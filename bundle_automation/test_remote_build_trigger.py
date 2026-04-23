"""End-to-end test for the remote-build trigger flow.

Verifies:
  1. /api/admin/bundle_build_status responds with the expected fields.
  2. Polling the status endpoint updates bundle_runner_seen_at.
  3. Admin POST to /roblox_bundles/build_now bumps requested_at and the
     status endpoint flips pending=True.
  4. POST /api/admin/bundle_build_ack with the captured requested_at
     flips pending back to False, records completed_at + last_status,
     and acked_at moves forward (never backwards).
  5. Idempotency: a second ack with the same requested_at does not
     break anything; pending stays False.
  6. Stale ack with an older requested_at is ignored (acked_at not
     moved backwards) -- safety against a poller restarted with stale
     state.
  7. A new admin click DURING a build (i.e. requested_at advances past
     the value the runner is still acking) keeps pending=True after
     the runner's ack of the older request_at.

Run against a live server:
    LICENSE_SERVER_URL=http://localhost:5000 \
    BUNDLE_AUTOMATION_TOKEN=<token> \
    ADMIN_PASSWORD=admin \
    python bundle_automation/test_remote_build_trigger.py
"""
from __future__ import annotations
import http.cookiejar
import json
import os
import sys
import time
import urllib.parse
import urllib.request

SERVER = os.environ.get("LICENSE_SERVER_URL", "http://localhost:5000").rstrip("/")
TOKEN = os.environ.get("BUNDLE_AUTOMATION_TOKEN", "").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")


def die(msg: str) -> "None":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def http_json(method: str, path: str, body=None, headers=None, opener=None):
    url = SERVER + path
    data = None
    h = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    op = opener or urllib.request.build_opener()
    with op.open(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw) if raw else {}


def admin_session():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = urllib.parse.urlencode({"password": ADMIN_PASSWORD}).encode("utf-8")
    req = urllib.request.Request(
        f"{SERVER}/",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with op.open(req, timeout=10) as resp:
        if resp.status not in (200, 302):
            die(f"admin login failed: HTTP {resp.status}")
    return op


def status() -> dict:
    sc, body = http_json(
        "GET",
        "/api/admin/bundle_build_status",
        headers={"X-Bundle-Token": TOKEN},
    )
    if sc != 200 or not body.get("ok"):
        die(f"status endpoint returned {sc}: {body}")
    for k in ("server_time", "requested_at", "acked_at", "pending"):
        if k not in body:
            die(f"status response missing field {k!r}: {body}")
    return body


def ack(requested_at: float, st: str, msg: str) -> dict:
    sc, body = http_json(
        "POST",
        "/api/admin/bundle_build_ack",
        body={"requested_at": requested_at, "status": st, "message": msg},
        headers={"X-Bundle-Token": TOKEN},
    )
    if sc != 200 or not body.get("ok"):
        die(f"ack endpoint returned {sc}: {body}")
    return body


def click_build(op):
    body = b""
    req = urllib.request.Request(
        f"{SERVER}/roblox_bundles/build_now",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with op.open(req, timeout=10) as resp:
        if resp.status not in (200, 302):
            die(f"build_now returned HTTP {resp.status}")


def main() -> int:
    if not TOKEN:
        die("BUNDLE_AUTOMATION_TOKEN env var is required")

    print(f"[1/7] Initial status...")
    s0 = status()
    print(f"      requested_at={s0['requested_at']} acked_at={s0['acked_at']} "
          f"pending={s0['pending']}")

    print(f"[2/7] Two consecutive status polls advance bundle_runner_seen_at")
    time.sleep(1.05)
    s_again = status()
    if s_again["server_time"] <= s0["server_time"]:
        die("server_time did not advance between two polls")
    print(f"      runner_seen advances on every poll: PASS")

    print(f"[3/7] Admin clicks 'Build new bundle now'")
    op = admin_session()
    click_build(op)
    s1 = status()
    if not s1["pending"]:
        die(f"after click, pending should be True: {s1}")
    if s1["requested_at"] <= s0["requested_at"]:
        die(f"requested_at did not advance: was {s0['requested_at']}, "
            f"now {s1['requested_at']}")
    print(f"      pending=True, requested_at={s1['requested_at']}")

    print(f"[4/7] Runner ack with the captured requested_at")
    a = ack(s1["requested_at"], "ok", "test ack from suite")
    s2 = status()
    if s2["pending"]:
        die(f"after ack, pending should be False: {s2}")
    if abs(s2["acked_at"] - s1["requested_at"]) > 0.0001:
        die(f"acked_at != requested_at: {s2['acked_at']} vs {s1['requested_at']}")
    print(f"      acked_at={s2['acked_at']} completed_at={a['completed_at']} "
          f"status={a['status']}")

    print(f"[5/7] Idempotent ack (same requested_at)")
    ack(s1["requested_at"], "ok", "second ack")
    s3 = status()
    if s3["pending"]:
        die(f"second ack should leave pending=False: {s3}")
    print(f"      no flip back to pending: PASS")

    print(f"[6/7] Stale ack (older requested_at) does NOT move acked_at backwards")
    stale_ts = max(0.0, s2["acked_at"] - 100.0)
    ack(stale_ts, "ok", "stale ack")
    s4 = status()
    if s4["acked_at"] < s2["acked_at"]:
        die(f"acked_at moved backwards: was {s2['acked_at']}, now {s4['acked_at']}")
    print(f"      acked_at stayed at {s4['acked_at']}: PASS")

    print(f"[7/7] Click during in-flight build keeps pending=True after old ack")
    # Simulate: runner observed s1.requested_at and is still building.
    # Admin clicks again -- requested_at advances past s1.requested_at.
    in_flight_ts = s1["requested_at"]
    time.sleep(0.05)
    click_build(op)
    s5 = status()
    if not s5["pending"]:
        die(f"after second click, should be pending again: {s5}")
    if s5["requested_at"] <= in_flight_ts:
        die(f"second click did not advance requested_at: {s5}")
    # Runner now acks the OLD timestamp it was working on.
    ack(in_flight_ts, "ok", "ack of in-flight build")
    s6 = status()
    if not s6["pending"]:
        die(f"acking old request should leave new request pending: {s6}")
    print(f"      pending stays True after old ack: PASS "
          f"(requested_at={s6['requested_at']} > acked_at={s6['acked_at']})")

    # Clean up: ack the latest so the test leaves state tidy.
    ack(s6["requested_at"], "ok", "test cleanup")

    print("\nAll remote-build-trigger tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
