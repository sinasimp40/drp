"""Unit tests for the rolling-24h IP-strike anti-sharing rule.

Covers the pure helper `_evaluate_ip_change` plus an end-to-end check
against a temporary SQLite DB to make sure the schema migration + JSON
serialization round-trip works the way the live endpoints expect.

Run:  python license_server/test_ip_strikes.py
"""
import json
import os
import sqlite3
import sys
import tempfile
import time

# Import server module without spinning up Flask.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server  # noqa: E402


# ── helpers ───────────────────────────────────────────────────────────

def make_row(registered_ip="1.1.1.10", last_ip=None, last_hb=None, strikes_json=""):
    """Build a sqlite3.Row-like dict for the helper. The helper accesses
    row["last_ip"], row["last_heartbeat"], row["ip_strikes_json"], and
    checks `row.keys()` for column presence."""
    class FakeRow(dict):
        def keys(self):
            return list(super().keys())
    return FakeRow(
        registered_ip=registered_ip,
        last_ip=last_ip,
        last_heartbeat=last_hb,
        ip_strikes_json=strikes_json,
    )


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"FAIL {msg}: expected {expected!r}, got {actual!r}")


# ── pure-helper tests ────────────────────────────────────────────────

def test_subnet_parser():
    assert_eq(server._subnet("1.2.3.4"), "1.2.3", "happy path")
    assert_eq(server._subnet(""), "", "empty")
    assert_eq(server._subnet(None), "", "None")
    assert_eq(server._subnet("::1"), "", "ipv6")
    assert_eq(server._subnet("1.2..4"), "", "blank octet")
    print("ok  _subnet parser")


def test_first_ever_heartbeat_no_strike():
    """No last_ip yet → no strike work, no transition."""
    now = time.time()
    row = make_row(last_ip=None, last_hb=None)
    res = server._evaluate_ip_change(row, "9.9.9.9", now)
    assert_eq(res, ("ok", None), "first-ever heartbeat")
    print("ok  first heartbeat is never a strike")


def test_same_subnet_no_strike():
    now = time.time()
    row = make_row(last_ip="5.5.5.10", last_hb=now - 30)
    res = server._evaluate_ip_change(row, "5.5.5.99", now)
    assert_eq(res, ("ok", None), "same /24")
    print("ok  same subnet does not strike")


def test_one_transition_records_strike():
    now = time.time()
    row = make_row(last_ip="5.5.5.10", last_hb=now - 30, strikes_json="")
    res = server._evaluate_ip_change(row, "8.8.8.10", now)
    assert_eq(res[0], "ok", "1st strike still ok")
    assert res[1] is not None, "expected strike JSON returned"
    parsed = json.loads(res[1])
    assert_eq(len(parsed), 1, "one strike recorded")
    assert_eq(parsed[0]["from_subnet"], "5.5.5", "from")
    assert_eq(parsed[0]["to_subnet"], "8.8.8", "to")
    print("ok  first transition records strike but stays active")


def test_second_transition_suspends_a_b_a():
    """A → B → A pattern should suspend on the second transition."""
    now = time.time()
    # Already 1 strike on file from the A→B transition 1h ago.
    existing = json.dumps([{"ts": now - 3600, "from_subnet": "5.5.5", "to_subnet": "8.8.8"}])
    row = make_row(last_ip="8.8.8.10", last_hb=now - 30, strikes_json=existing)
    # Now coming back to original /24.
    res = server._evaluate_ip_change(row, "5.5.5.20", now)
    assert_eq(res[0], "suspend_strikes", "should suspend on 2nd transition")
    assert_eq(res[1], "8.8.8.10", "prev_ip")
    assert_eq(res[2], "5.5.5.20", "new_ip")
    assert_eq(res[3], 2, "strike count")
    print("ok  A→B→A suspends on 2nd strike")


def test_second_transition_suspends_a_b_c():
    now = time.time()
    existing = json.dumps([{"ts": now - 3600, "from_subnet": "5.5.5", "to_subnet": "8.8.8"}])
    row = make_row(last_ip="8.8.8.10", last_hb=now - 30, strikes_json=existing)
    res = server._evaluate_ip_change(row, "9.9.9.10", now)
    assert_eq(res[0], "suspend_strikes", "A→B→C should suspend")
    assert_eq(res[3], 2, "strike count")
    print("ok  A→B→C suspends on 2nd strike")


def test_old_strikes_roll_off():
    """A strike older than 24h must NOT count toward the limit."""
    now = time.time()
    # Strike from 25 hours ago — past the rolling window.
    existing = json.dumps([
        {"ts": now - (25 * 3600), "from_subnet": "5.5.5", "to_subnet": "8.8.8"},
    ])
    row = make_row(last_ip="8.8.8.10", last_hb=now - 30, strikes_json=existing)
    res = server._evaluate_ip_change(row, "5.5.5.20", now)
    # Expected: old strike rolled off, this transition becomes strike #1, OK.
    assert_eq(res[0], "ok", "old strike should not block")
    assert res[1] is not None, "should record new strike json"
    parsed = json.loads(res[1])
    assert_eq(len(parsed), 1, "old one dropped, new one added")
    print("ok  strikes older than 24h roll off")


def test_repeated_same_new_subnet_no_extra_strikes():
    """Once moved to subnet B, further heartbeats from B must NOT
    accumulate more strikes — otherwise heartbeats every 10s would hit
    the cap in 20s for a CGNAT user who rotated once."""
    now = time.time()
    existing = json.dumps([{"ts": now - 60, "from_subnet": "5.5.5", "to_subnet": "8.8.8"}])
    row = make_row(last_ip="8.8.8.10", last_hb=now - 5, strikes_json=existing)
    res = server._evaluate_ip_change(row, "8.8.8.50", now)
    assert_eq(res, ("ok", None), "same /24 as last_ip → no new strike")
    print("ok  staying on rotated subnet does not accumulate strikes")


def test_corrupt_json_treated_as_empty():
    now = time.time()
    row = make_row(last_ip="5.5.5.10", last_hb=now - 30, strikes_json="not json {{")
    res = server._evaluate_ip_change(row, "8.8.8.10", now)
    assert_eq(res[0], "ok", "corrupt json should not crash")
    assert res[1] is not None, "should produce fresh strike list"
    parsed = json.loads(res[1])
    assert_eq(len(parsed), 1, "fresh list, one strike")
    print("ok  corrupt JSON tolerated")


def test_unparseable_client_ip_does_not_strike():
    now = time.time()
    row = make_row(last_ip="5.5.5.10", last_hb=now - 30)
    res = server._evaluate_ip_change(row, "garbage", now)
    assert_eq(res, ("ok", None), "unparseable IP → no strike")
    print("ok  unparseable client IP does not strike")


# ── end-to-end DB round-trip test ────────────────────────────────────

def test_db_schema_and_round_trip():
    """Spin up a temp DB using the real init_db() to confirm the
    ip_strikes_json column is created and JSON survives a round trip."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        path = tf.name
    try:
        original = server.DB_PATH
        server.DB_PATH = path
        server.init_db()

        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        # column should exist
        cols = [r[1] for r in conn.execute("PRAGMA table_info(licenses)").fetchall()]
        assert "ip_strikes_json" in cols, f"column missing, got: {cols}"

        # Insert a fake active license, simulate two strikes via helper,
        # persist, read back.
        now = time.time()
        conn.execute(
            """INSERT INTO licenses (license_key, created_at, activated_at, expires_at,
                                     duration_seconds, status, last_heartbeat, last_ip,
                                     registered_ip, ip_strikes_json)
               VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, '')""",
            ("TEST-KEY-1234", now, now, now + 3600, 3600, now - 30,
             "5.5.5.10", "5.5.5.10"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM licenses WHERE license_key='TEST-KEY-1234'").fetchone()

        # 1st transition A→B → ok with strike json
        d1 = server._evaluate_ip_change(row, "8.8.8.10", now)
        assert_eq(d1[0], "ok", "1st transition")
        conn.execute(
            "UPDATE licenses SET last_ip = ?, last_heartbeat = ?, ip_strikes_json = ? WHERE id = ?",
            ("8.8.8.10", now, d1[1], row["id"]),
        )
        conn.commit()

        # 2nd transition B→C → suspend
        row2 = conn.execute("SELECT * FROM licenses WHERE id=?", (row["id"],)).fetchone()
        d2 = server._evaluate_ip_change(row2, "9.9.9.10", now + 60)
        assert_eq(d2[0], "suspend_strikes", "2nd transition should suspend")

        print("ok  DB round-trip: schema + json persist + helper integration")
    finally:
        server.DB_PATH = original
        try:
            os.unlink(path)
        except OSError:
            pass


def main():
    test_subnet_parser()
    test_first_ever_heartbeat_no_strike()
    test_same_subnet_no_strike()
    test_one_transition_records_strike()
    test_second_transition_suspends_a_b_a()
    test_second_transition_suspends_a_b_c()
    test_old_strikes_roll_off()
    test_repeated_same_new_subnet_no_extra_strikes()
    test_corrupt_json_treated_as_empty()
    test_unparseable_client_ip_does_not_strike()
    test_db_schema_and_round_trip()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
