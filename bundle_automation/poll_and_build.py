"""DENFI bundle-build poller.

Runs every few minutes on the Windows RDP machine via Task Scheduler.
Asks the license server "did the admin press the Build now button since
the last build?" and, if yes, runs build_and_upload.py once, then POSTs
the result back so the admin UI shows status + a fresh "completed"
timestamp.

Why a separate script: the daily build_and_upload.py covers regular
upgrades, but the admin button on /roblox_bundles needs a fast feedback
loop -- waiting until 03:00 tomorrow is no good. Run this script every
2-5 minutes; it does nothing 99% of the time and only fires when there's
a pending request.

Required env vars (same as build_and_upload.py):
  LICENSE_SERVER_URL       e.g. https://your-license-server.example.com
  BUNDLE_AUTOMATION_TOKEN  long random string; must match the server

Optional:
  BUNDLE_BUILDER_PYTHON    path to python.exe to launch build_and_upload.py
                           with. Defaults to sys.executable.

Exit codes:
  0  no pending request (nothing to do), or build ran successfully
  1  could not reach the license server
  2  build_and_upload.py exited non-zero (still acks the server so the
     admin UI shows the failure instead of staying "Pending" forever)
"""
from __future__ import annotations
import json
import os
import socket
import ssl
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request

LICENSE_SERVER_URL = os.environ.get("LICENSE_SERVER_URL", "").rstrip("/")
BUNDLE_AUTOMATION_TOKEN = os.environ.get("BUNDLE_AUTOMATION_TOKEN", "").strip()
BUILDER_PY = os.environ.get("BUNDLE_BUILDER_PYTHON", sys.executable)
HERE = os.path.dirname(os.path.abspath(__file__))
BUILDER_SCRIPT = os.path.join(HERE, "build_and_upload.py")
LOG_DIR = os.path.join(HERE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, time.strftime("poll_%Y%m%d.log"))

# Build-and-upload exit codes (mirror of build_and_upload.py.die).
EXIT_LABEL = {
    0: "ok",
    1: "fetch-failed",
    2: "install-failed",
    3: "upload-failed",
    4: "config-error",
}


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    print(line, flush=True)


def http_json(method: str, path: str, body: dict | None = None, timeout: int = 30) -> tuple[int, dict]:
    """Tiny JSON-over-HTTP helper. Returns (status_code, parsed_body)."""
    url = LICENSE_SERVER_URL + path
    data = None
    headers = {
        "X-Bundle-Token": BUNDLE_AUTOMATION_TOKEN,
        "Accept": "application/json",
        "User-Agent": "denfi-bundle-poller/1",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
            try:
                return resp.status, (json.loads(raw.decode("utf-8")) if raw else {})
            except Exception:
                return resp.status, {"raw": raw[:500].decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        try:
            raw = e.read()
            return e.code, (json.loads(raw.decode("utf-8")) if raw else {})
        except Exception:
            return e.code, {"error": str(e)}
    except (urllib.error.URLError, socket.timeout, ssl.SSLError) as e:
        raise RuntimeError(f"network error contacting {url}: {e}")


def run_builder() -> tuple[int, str]:
    """Run build_and_upload.py once, capture last log lines for the ack."""
    log(f"Launching builder: {BUILDER_PY} {BUILDER_SCRIPT}")
    try:
        proc = subprocess.run(
            [BUILDER_PY, BUILDER_SCRIPT],
            capture_output=True,
            text=True,
            timeout=60 * 30,  # 30 min hard cap
        )
    except subprocess.TimeoutExpired:
        return 99, "builder timed out after 30 minutes"
    except Exception as e:
        return 99, f"failed to launch builder: {e}"

    # Last 8 lines of stdout (or stderr if stdout empty) -- enough context
    # for the admin UI message field without overflowing it.
    out = (proc.stdout or "").strip().splitlines()
    err = (proc.stderr or "").strip().splitlines()
    tail = (out[-8:] if out else err[-8:])
    msg = " | ".join(tail)[:500]
    log(f"Builder exited rc={proc.returncode}; tail: {msg}")
    return proc.returncode, msg


def main() -> int:
    if not LICENSE_SERVER_URL or not BUNDLE_AUTOMATION_TOKEN:
        log("ERROR: LICENSE_SERVER_URL and BUNDLE_AUTOMATION_TOKEN env vars are required")
        return 1

    log("=== bundle build poller starting ===")
    try:
        status_code, status = http_json("GET", "/api/admin/bundle_build_status")
    except RuntimeError as e:
        log(f"ERROR: {e}")
        return 1
    if status_code != 200 or not status.get("ok"):
        log(f"ERROR: status endpoint returned {status_code}: {status}")
        return 1

    if not status.get("pending"):
        log("No pending build request — exiting.")
        return 0

    requested_at = float(status.get("requested_at") or 0)
    log(f"Pending build request found (requested_at={requested_at}). Running builder…")

    rc, tail = run_builder()
    if rc == 0:
        ack_status, ack_message = "ok", (tail or "build completed")
    else:
        label = EXIT_LABEL.get(rc, f"failed-rc{rc}")
        ack_status, ack_message = label, (tail or f"builder exited rc={rc}")

    # Special case: build_and_upload exits 0 even when "no update needed".
    # The tail will say "Server already has bundle for ..." -- detect and
    # relabel so the admin sees a clearer status.
    if rc == 0 and "already has bundle" in (tail or "").lower():
        ack_status = "no-update-needed"

    try:
        ack_code, ack_resp = http_json(
            "POST",
            "/api/admin/bundle_build_ack",
            body={
                "requested_at": requested_at,
                "status": ack_status,
                "message": ack_message,
            },
        )
        if ack_code != 200 or not ack_resp.get("ok"):
            log(f"WARNING: ack endpoint returned {ack_code}: {ack_resp}")
        else:
            log(f"Ack accepted: {ack_resp}")
    except RuntimeError as e:
        log(f"WARNING: failed to ack server: {e}")

    return 0 if rc == 0 else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        log("UNCAUGHT EXCEPTION:")
        for line in traceback.format_exc().splitlines():
            log("  " + line)
        sys.exit(1)
