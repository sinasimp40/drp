"""End-to-end test for the admin "Force re-download" feature.

Verifies (against the running license_server on PORT 5000):
  1. /api/roblox_bundle/info returns a `force_redownload_at` field.
  2. POST /roblox_bundles/force_redownload (admin route) bumps it.
  3. The new (higher) value flows through subsequent /info responses.
  4. The launcher's "should I re-download?" decision flips correctly,
     and stays stable once the launcher persists the new timestamp
     (no infinite re-download loop).
  5. Response signature is valid both before and after.

Run from project root after the server is up:
    python bundle_automation/test_force_redownload.py
"""
import hashlib
import hmac
import http.cookiejar
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

SERVER = os.environ.get("LICENSE_SERVER_URL", "http://127.0.0.1:5000").rstrip("/")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "license_server", "licenses.db")
TRIAL_SECRET = os.environ.get("TRIAL_REGISTER_SECRET", "DENFI_TRIAL_REGISTER_SECRET_2026")
ADMIN_PASSWORD = os.environ.get("LICENSE_ADMIN_PASSWORD", "admin")


def _sign_request(body, secret):
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
    msg = f"{ts}:{nonce}:{payload}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return ts, nonce, sig


def _verify_response(data, signature, secret):
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def fetch_bundle_info():
    body = {"version": "test", "app_name": "test"}
    ts, nonce, sig = _sign_request(body, TRIAL_SECRET)
    req = urllib.request.Request(
        f"{SERVER}/api/roblox_bundle/info",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Timestamp": ts, "X-Nonce": nonce, "X-Signature": sig,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        body_resp = he.read().decode("utf-8", errors="replace")
        result = json.loads(body_resp)
    data = result["data"]
    sig_resp = result.get("signature", "")
    assert _verify_response(data, sig_resp, TRIAL_SECRET), \
        "response signature did not verify"
    return data


def admin_session():
    """Return an opener with a logged-in admin session cookie."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    # The server's auth route is the site root POST; there is no
    # /admin/login by design (decoy nginx 404 for guesses).
    body = urllib.parse.urlencode({"password": ADMIN_PASSWORD}).encode("utf-8")
    req = urllib.request.Request(
        f"{SERVER}/",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with opener.open(req, timeout=10) as resp:
        # 302 to dashboard or 200 with form. We just need the cookie.
        if resp.status not in (200, 302):
            raise SystemExit(f"admin login failed: HTTP {resp.status}")
    return opener


def force_redownload(opener):
    req = urllib.request.Request(
        f"{SERVER}/roblox_bundles/force_redownload",
        data=b"",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with opener.open(req, timeout=10) as resp:
        if resp.status not in (200, 302):
            raise SystemExit(f"force_redownload failed: HTTP {resp.status}")


def ensure_bundle_row():
    """Insert a placeholder bundle row if none exist so the API has
    something to return. Cleaned up at the end."""
    conn = sqlite3.connect(DB_PATH)
    try:
        n = conn.execute("SELECT COUNT(*) FROM roblox_bundles").fetchone()[0]
        if n > 0:
            return None  # caller doesn't need to clean up
        conn.execute(
            "INSERT INTO roblox_bundles (version, filename, file_size, sha256, uploaded_at, note)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (999999, "_test_placeholder.zip", 1024, "0" * 64, time.time(), "force-redownload test"),
        )
        conn.commit()
        return 999999
    finally:
        conn.close()


def cleanup_bundle_row(version):
    if version is None:
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM roblox_bundles WHERE version = ?", (version,))
        conn.commit()
    finally:
        conn.close()


def main():
    inserted_version = ensure_bundle_row()
    try:
        info_before = fetch_bundle_info()
        assert info_before.get("valid"), f"info call returned invalid: {info_before}"
        assert "force_redownload_at" in info_before, \
            f"force_redownload_at missing from response: {info_before}"
        before_ts = float(info_before["force_redownload_at"])
        print(f"[1/5] Initial force_redownload_at = {before_ts}")

        opener = admin_session()
        print("[2/5] Admin session established.")

        force_redownload(opener)
        print("[3/5] POST /roblox_bundles/force_redownload accepted.")

        # Server uses time.time() with sub-second precision; make sure the
        # next request runs at least a tick later so the comparison is safe.
        time.sleep(0.01)
        info_after = fetch_bundle_info()
        after_ts = float(info_after["force_redownload_at"])
        print(f"[4/5] force_redownload_at after force = {after_ts}")
        assert after_ts > before_ts, \
            f"timestamp did not advance: before={before_ts} after={after_ts}"

        # Launcher decision logic mirror
        cached_force_at = before_ts
        force_required = after_ts > 0 and after_ts > cached_force_at
        assert force_required, "launcher would NOT trigger re-download (logic bug)"

        # After the launcher persists after_ts, next launch must NOT re-download.
        cached_force_at = after_ts
        info_again = fetch_bundle_info()
        ts3 = float(info_again["force_redownload_at"])
        force_required = ts3 > 0 and ts3 > cached_force_at
        assert not force_required, \
            "launcher would re-download every launch — infinite loop bug!"
        print("[5/5] Launcher decision flips True after force, "
              "False after persist. No loop. PASS.")

        # Force again — should bump again.
        time.sleep(0.01)
        force_redownload(opener)
        time.sleep(0.01)
        info_third = fetch_bundle_info()
        ts4 = float(info_third["force_redownload_at"])
        assert ts4 > ts3, f"second force didn't bump: {ts3} -> {ts4}"
        print(f"      Second force advanced timestamp again: {ts3} -> {ts4}. PASS.")

        print("\nAll force-redownload tests passed.")
        return 0
    finally:
        cleanup_bundle_row(inserted_version)


if __name__ == "__main__":
    sys.exit(main())
