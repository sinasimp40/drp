SERVER_VERSION = "1.0.0"

import os
import sys
import uuid
import time
import hmac
import hashlib
import json
import sqlite3
import secrets
import threading
import shutil
import re
import subprocess
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, send_file
from flask_socketio import SocketIO, emit

import telegram_backup

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "licenses.db")
SHARED_SECRET = os.environ.get("LICENSE_SHARED_SECRET", "DENFI_LICENSE_SECRET_KEY_2024")
ADMIN_PASSWORD = os.environ.get("LICENSE_ADMIN_PASSWORD", "admin")
HEARTBEAT_TIMEOUT = 60
REQUEST_TIMESTAMP_TOLERANCE = 300
_used_nonces = set()
_nonce_cleanup_time = 0

BUILDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "builds")
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_icons")
SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_build_progress = {}
_build_lock = threading.Lock()
_recent_ota_log = []
_recent_ota_lock = threading.Lock()

def _record_ota(entry):
    with _recent_ota_lock:
        _recent_ota_log.append(entry)
        if len(_recent_ota_log) > 50:
            del _recent_ota_log[:len(_recent_ota_log)-50]
_download_tokens = {}
_download_progress = {}

socketio = SocketIO(app, async_mode='threading', allow_upgrades=False, transports=['polling'])


@socketio.on('connect')
def handle_connect():
    if not session.get("admin"):
        return False


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE NOT NULL,
            created_at REAL NOT NULL,
            activated_at REAL,
            expires_at REAL,
            duration_seconds INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            last_heartbeat REAL,
            last_ip TEXT,
            note TEXT DEFAULT '',
            registered_ip TEXT
        );
    """)
    try:
        conn.execute("SELECT activated_at FROM licenses LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE licenses ADD COLUMN activated_at REAL")
        conn.execute("UPDATE licenses SET activated_at = created_at WHERE status = 'active'")
        conn.execute("UPDATE licenses SET status = 'pending' WHERE status = 'active' AND last_heartbeat IS NULL AND activated_at IS NULL")
        conn.commit()
    try:
        conn.execute("SELECT registered_ip FROM licenses LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE licenses ADD COLUMN registered_ip TEXT")
        conn.execute("UPDATE licenses SET registered_ip = last_ip WHERE status = 'active' AND last_ip IS NOT NULL")
        conn.commit()
    try:
        existing = conn.execute("SELECT expires_at FROM licenses WHERE expires_at IS NOT NULL LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("SELECT launcher_version FROM licenses LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE licenses ADD COLUMN launcher_version TEXT DEFAULT ''")
        conn.commit()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS build_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_id INTEGER,
            app_name TEXT NOT NULL DEFAULT 'DENFI ROBLOX',
            hardcoded_path TEXT NOT NULL DEFAULT '',
            license_server_url TEXT DEFAULT '',
            license_secret TEXT DEFAULT 'DENFI_LICENSE_SECRET_KEY_2024',
            icon_filename TEXT DEFAULT '',
            embedded_key TEXT DEFAULT '',
            created_at REAL NOT NULL,
            updated_at REAL,
            FOREIGN KEY (license_id) REFERENCES licenses(id)
        );
        CREATE TABLE IF NOT EXISTS builds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            total_configs INTEGER DEFAULT 0,
            completed_configs INTEGER DEFAULT 0,
            started_at REAL,
            completed_at REAL,
            error_message TEXT DEFAULT '',
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS build_artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            build_id INTEGER NOT NULL,
            build_config_id INTEGER NOT NULL,
            license_id INTEGER,
            exe_filename TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            error_message TEXT DEFAULT '',
            config_hash TEXT DEFAULT '',
            started_at REAL,
            completed_at REAL,
            FOREIGN KEY (build_id) REFERENCES builds(id),
            FOREIGN KEY (build_config_id) REFERENCES build_configs(id)
        );
    """)
    try:
        conn.execute("SELECT config_hash FROM build_artifacts LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE build_artifacts ADD COLUMN config_hash TEXT DEFAULT ''")
        conn.commit()
    try:
        conn.execute("SELECT app_name_snapshot FROM build_artifacts LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE build_artifacts ADD COLUMN app_name_snapshot TEXT DEFAULT ''")
        conn.commit()
        conn.execute("""UPDATE build_artifacts
                        SET app_name_snapshot = COALESCE(
                            (SELECT app_name FROM build_configs WHERE build_configs.id = build_artifacts.build_config_id),
                            ''
                        )
                        WHERE app_name_snapshot = '' OR app_name_snapshot IS NULL""")
        conn.commit()
    conn.commit()
    try:
        conn.execute("SELECT embedded_key FROM build_configs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE build_configs ADD COLUMN embedded_key TEXT DEFAULT ''")
        conn.commit()
    conn.close()


def sign_response(data):
    payload = json.dumps(data, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        SHARED_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_request_signature():
    global _used_nonces, _nonce_cleanup_time

    timestamp = request.headers.get("X-Timestamp", "")
    nonce = request.headers.get("X-Nonce", "")
    signature = request.headers.get("X-Signature", "")

    if not timestamp or not nonce or not signature:
        return False, "Missing authentication headers"

    try:
        ts = int(timestamp)
    except ValueError:
        return False, "Invalid timestamp"

    now = int(time.time())
    if abs(now - ts) > REQUEST_TIMESTAMP_TOLERANCE:
        return False, "Request expired"

    if nonce in _used_nonces:
        return False, "Replay detected"

    body = request.get_json(silent=True) or {}
    body_json = json.dumps(body, sort_keys=True, separators=(',', ':'))
    sign_payload = f"{timestamp}:{nonce}:{body_json}"
    expected = hmac.new(
        SHARED_SECRET.encode('utf-8'),
        sign_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return False, "Invalid signature"

    _used_nonces.add(nonce)
    if now - _nonce_cleanup_time > 600:
        _used_nonces = set()
        _nonce_cleanup_time = now

    return True, "OK"


def require_signed_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        valid, msg = verify_request_signature()
        if not valid:
            try:
                client_ip = _get_client_ip()
            except Exception:
                client_ip = request.remote_addr
            ts_hdr = request.headers.get("X-Timestamp", "")
            skew = ""
            try:
                skew = f" skew={int(time.time()) - int(ts_hdr)}s"
            except Exception:
                pass
            print(f"[auth] 403 {request.path} from {client_ip}: {msg}{skew}", flush=True)
            resp = {"valid": False, "error": msg}
            return jsonify({"data": resp, "signature": sign_response(resp)}), 403
        return f(*args, **kwargs)
    return decorated


def generate_key():
    raw = uuid.uuid4().hex[:20].upper()
    return f"{raw[:5]}-{raw[5:10]}-{raw[10:15]}-{raw[15:20]}"


def format_duration(seconds):
    if seconds <= 0:
        return "Expired"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "<1m"


def format_time(timestamp):
    if not timestamp:
        return "Never"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def is_online(last_heartbeat):
    if not last_heartbeat:
        return False
    return (time.time() - last_heartbeat) < HEARTBEAT_TIMEOUT


def _get_client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    real = request.headers.get("X-Real-IP", "").strip()
    if real:
        return real
    return request.remote_addr


def _is_same_subnet(ip1, ip2):
    try:
        parts1 = ip1.split(".")[:3]
        parts2 = ip2.split(".")[:3]
        return parts1 == parts2 and len(parts1) == 3
    except Exception:
        return False


def activate_license(conn, row, client_ip):
    now = time.time()
    expires_at = now + row["duration_seconds"]
    conn.execute(
        "UPDATE licenses SET status = 'active', activated_at = ?, expires_at = ?, registered_ip = ?, last_heartbeat = ?, last_ip = ? WHERE id = ?",
        (now, expires_at, client_ip, now, client_ip, row["id"])
    )
    conn.commit()
    return expires_at


def expire_active_licenses(conn):
    now = time.time()
    conn.execute(
        "UPDATE licenses SET status = 'expired' WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?",
        (now,)
    )
    conn.commit()



@app.route("/api/validate", methods=["POST"])
@require_signed_request
def api_validate():
    data = request.get_json(silent=True)
    if not data or "key" not in data:
        resp = {"valid": False, "error": "Missing key"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    key = data["key"].strip()
    conn = get_db()
    row = conn.execute("SELECT * FROM licenses WHERE license_key = ?", (key,)).fetchone()

    if not row:
        conn.close()
        resp = {"valid": False, "error": "License not found"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "revoked":
        conn.close()
        resp = {"valid": False, "error": "License has been revoked"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "deleted":
        conn.close()
        resp = {"valid": False, "error": "License has been deleted"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "suspended":
        conn.close()
        resp = {"valid": False, "error": "License suspended. Contact the developer."}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "expired":
        conn.close()
        resp = {"valid": False, "error": "License has expired"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "pending":
        client_ip = _get_client_ip()
        expires_at = activate_license(conn, row, client_ip)
        remaining = expires_at - time.time()
        conn.close()
        resp = {
            "valid": True,
            "status": "activated",
            "remaining_seconds": int(remaining),
            "remaining_text": format_duration(remaining),
            "expires_at": expires_at,
            "key": key,
        }
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "active":
        now = time.time()
        if row["expires_at"] is None:
            conn.execute("UPDATE licenses SET status = 'expired' WHERE id = ?", (row["id"],))
            conn.commit()
            conn.close()
            resp = {"valid": False, "error": "License has expired"}
            return jsonify({"data": resp, "signature": sign_response(resp)})
        remaining = row["expires_at"] - now

        if remaining <= 0:
            conn.execute("UPDATE licenses SET status = 'expired' WHERE id = ?", (row["id"],))
            conn.commit()
            conn.close()
            resp = {"valid": False, "error": "License has expired"}
            return jsonify({"data": resp, "signature": sign_response(resp)})

        client_ip = _get_client_ip()
        if row["registered_ip"] and not _is_same_subnet(client_ip, row["registered_ip"]):
            conn.execute("UPDATE licenses SET status = 'suspended' WHERE id = ?", (row["id"],))
            conn.commit()
            conn.close()
            resp = {"valid": False, "error": "License suspended. Contact the developer."}
            return jsonify({"data": resp, "signature": sign_response(resp)})

        launcher_version = data.get("version", "") or ""
        if launcher_version:
            conn.execute(
                "UPDATE licenses SET last_heartbeat = ?, last_ip = ?, launcher_version = ? WHERE id = ?",
                (now, client_ip, launcher_version, row["id"])
            )
        else:
            conn.execute(
                "UPDATE licenses SET last_heartbeat = ?, last_ip = ? WHERE id = ?",
                (now, client_ip, row["id"])
            )
        conn.commit()
        conn.close()
        resp = {
            "valid": True,
            "status": "active",
            "remaining_seconds": int(remaining),
            "remaining_text": format_duration(remaining),
            "key": key,
        }
        return jsonify({"data": resp, "signature": sign_response(resp)})

    conn.close()
    resp = {"valid": False, "error": f"License {row['status']}"}
    return jsonify({"data": resp, "signature": sign_response(resp)})


@app.route("/api/heartbeat", methods=["POST"])
@require_signed_request
def api_heartbeat():
    data = request.get_json(silent=True)
    if not data or "key" not in data:
        resp = {"valid": False, "error": "Missing key"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    key = data["key"].strip()
    conn = get_db()
    row = conn.execute("SELECT * FROM licenses WHERE license_key = ?", (key,)).fetchone()

    if not row:
        conn.close()
        resp = {"valid": False, "error": "License not found"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "pending":
        conn.close()
        resp = {"valid": False, "error": "License not yet activated"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "revoked":
        conn.close()
        resp = {"valid": False, "error": "License has been revoked"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "deleted":
        conn.close()
        resp = {"valid": False, "error": "License has been deleted"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "suspended":
        conn.close()
        resp = {"valid": False, "error": "License suspended. Contact the developer."}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] == "expired":
        conn.close()
        resp = {"valid": False, "error": "License has expired"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    if row["status"] != "active":
        conn.close()
        resp = {"valid": False, "error": f"License {row['status']}"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    now = time.time()
    if row["expires_at"] is None:
        conn.execute("UPDATE licenses SET status = 'expired' WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        resp = {"valid": False, "error": "License has expired"}
        return jsonify({"data": resp, "signature": sign_response(resp)})
    remaining = row["expires_at"] - now

    if remaining <= 0:
        conn.execute("UPDATE licenses SET status = 'expired' WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        resp = {"valid": False, "error": "License has expired"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    client_ip = _get_client_ip()
    if row["registered_ip"] and not _is_same_subnet(client_ip, row["registered_ip"]):
        conn.execute("UPDATE licenses SET status = 'suspended' WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        resp = {"valid": False, "error": "License suspended. Contact the developer."}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    launcher_version = data.get("version", "") or ""
    if launcher_version:
        conn.execute(
            "UPDATE licenses SET last_heartbeat = ?, last_ip = ?, launcher_version = ? WHERE id = ?",
            (now, client_ip, launcher_version, row["id"])
        )
    else:
        conn.execute(
            "UPDATE licenses SET last_heartbeat = ?, last_ip = ? WHERE id = ?",
            (now, client_ip, row["id"])
        )
    conn.commit()
    conn.close()

    resp = {
        "valid": True,
        "remaining_seconds": int(remaining),
        "remaining_text": format_duration(remaining),
    }
    return jsonify({"data": resp, "signature": sign_response(resp)})


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        password = request.form.get("password", "")
        if hmac.compare_digest(password, ADMIN_PASSWORD):
            session.permanent = True
            session["admin_logged_in"] = True
            session["login_time"] = time.time()
            return redirect(url_for("dashboard"))
        flash("Invalid password", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/")
@require_admin
def dashboard():
    conn = get_db()
    now = time.time()
    expire_active_licenses(conn)

    rows = conn.execute(
        "SELECT * FROM licenses WHERE status IN ('active', 'pending', 'suspended') ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    licenses = []
    kpi_total = len(rows)
    kpi_online = 0
    kpi_suspended = 0
    kpi_expiring = 0
    for row in rows:
        if row["status"] == "active" and row["expires_at"] is not None:
            remaining = row["expires_at"] - now
            remaining_text = format_duration(remaining)
            remaining_seconds = int(remaining)
        elif row["status"] == "suspended" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
            remaining_text = format_duration(remaining) + " (suspended)"
            remaining_seconds = int(remaining)
        elif row["status"] == "active":
            remaining_text = "-"
            remaining_seconds = 0
        else:
            remaining_text = format_duration(row["duration_seconds"])
            remaining_seconds = row["duration_seconds"]

        online = is_online(row["last_heartbeat"])
        if row["status"] == "active" and online:
            kpi_online += 1
        if row["status"] == "suspended":
            kpi_suspended += 1
        if row["status"] == "active" and 0 < remaining_seconds <= 86400:
            kpi_expiring += 1

        licenses.append({
            "id": row["id"],
            "key": row["license_key"],
            "created": format_time(row["created_at"]),
            "activated": format_time(row["activated_at"]),
            "remaining": remaining_text,
            "remaining_seconds": remaining_seconds,
            "online": online,
            "last_heartbeat": format_time(row["last_heartbeat"]),
            "last_ip": row["last_ip"] or "N/A",
            "registered_ip": row["registered_ip"] or "N/A",
            "note": row["note"] or "",
            "status": row["status"],
            "version": row["launcher_version"] or "",
            "expires_at_ts": row["expires_at"],
            "duration_seconds": row["duration_seconds"],
        })

    kpis = {
        "total": kpi_total,
        "online": kpi_online,
        "suspended": kpi_suspended,
        "expiring": kpi_expiring,
    }
    return render_template("dashboard.html", licenses=licenses, kpis=kpis)


@app.route("/history")
@require_admin
def history():
    conn = get_db()
    now = time.time()
    expire_active_licenses(conn)

    rows = conn.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
    conn.close()

    licenses = []
    for row in rows:
        if row["status"] == "active" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
            remaining_text = format_duration(remaining)
            remaining_seconds = int(remaining)
        elif row["status"] == "suspended" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
            remaining_text = format_duration(remaining) + " (suspended)"
            remaining_seconds = int(remaining)
        elif row["status"] == "pending":
            remaining_text = format_duration(row["duration_seconds"]) + " (pending)"
            remaining_seconds = row["duration_seconds"]
        else:
            remaining_text = "-"
            remaining_seconds = 0

        licenses.append({
            "id": row["id"],
            "key": row["license_key"],
            "created": format_time(row["created_at"]),
            "activated": format_time(row["activated_at"]),
            "expires": format_time(row["expires_at"]) if row["expires_at"] else "Not activated",
            "remaining": remaining_text,
            "remaining_seconds": remaining_seconds,
            "online": is_online(row["last_heartbeat"]) if row["status"] == "active" else False,
            "last_ip": row["last_ip"] or "N/A",
            "registered_ip": row["registered_ip"] or "N/A",
            "note": row["note"] or "",
            "status": row["status"],
            "duration_text": format_duration(row["duration_seconds"]),
            "duration_seconds": int(row["duration_seconds"] or 0),
            "expires_at_ts": row["expires_at"],
            "version": row["launcher_version"] or "",
        })

    return render_template("history.html", licenses=licenses)


@app.route("/create", methods=["GET", "POST"])
@require_admin
def create_license():
    if request.method == "POST":
        duration_value = int(request.form.get("duration_value", 1))
        duration_unit = request.form.get("duration_unit", "hours")
        note = request.form.get("note", "").strip()

        multipliers = {"minutes": 60, "hours": 3600, "days": 86400}
        duration_seconds = duration_value * multipliers.get(duration_unit, 3600)

        now = time.time()
        key = generate_key()

        conn = get_db()
        conn.execute(
            "INSERT INTO licenses (license_key, created_at, duration_seconds, status, note) VALUES (?, ?, ?, 'pending', ?)",
            (key, now, duration_seconds, note)
        )
        conn.commit()
        conn.close()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": True,
                "key": key,
                "duration_value": duration_value,
                "duration_unit": duration_unit,
                "note": note,
                "created_at": now,
            })

        flash(f"License created: {key}", "success")
        return redirect(url_for("dashboard"))

    return render_template("create.html")


MAX_EDIT_SECONDS = 10 * 365 * 86400  # 10 years cap


@app.route("/license/<int:license_id>/edit", methods=["POST"])
@require_admin
def edit_license(license_id):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def _fail(msg, http=400):
        if is_ajax:
            return jsonify({"success": False, "error": msg}), http
        flash(msg, "error")
        return redirect(request.referrer or url_for("dashboard"))

    mode = (request.form.get("mode") or "").strip()  # "extend" | "set" | "note_only"
    unit = (request.form.get("unit") or "days").strip()
    amount_raw = (request.form.get("amount") or "").strip()
    note = (request.form.get("note") or "").strip()

    if mode not in ("extend", "set", "note_only"):
        return _fail("Invalid edit mode")

    multipliers = {"minutes": 60, "hours": 3600, "days": 86400}
    if unit not in multipliers:
        return _fail("Invalid time unit (use minutes, hours, or days)")

    delta_seconds = 0
    if mode in ("extend", "set"):
        if amount_raw == "":
            return _fail("Amount is required")
        try:
            amount = float(amount_raw)
        except ValueError:
            return _fail("Amount must be a number")
        delta_seconds = int(round(amount * multipliers[unit]))
        if mode == "set" and delta_seconds <= 0:
            return _fail("New remaining time must be greater than 0")
        if abs(delta_seconds) > MAX_EDIT_SECONDS:
            return _fail("Time change exceeds 10 year safety cap")

    conn = get_db()
    row = conn.execute("SELECT * FROM licenses WHERE id = ?", (license_id,)).fetchone()
    if not row:
        conn.close()
        return _fail("License not found", 404)

    status = row["status"]
    if status in ("revoked", "deleted"):
        conn.close()
        return _fail(f"Cannot edit a {status} license")

    now = time.time()
    new_status = status
    new_expires_at = row["expires_at"]
    new_duration_seconds = row["duration_seconds"]
    summary_parts = []

    if mode != "note_only":
        if status == "pending":
            # Never activated yet — adjust the stored duration that will start ticking on first activation.
            base = row["duration_seconds"] or 0
            new_duration_seconds = delta_seconds if mode == "set" else base + delta_seconds
            if new_duration_seconds < 60:
                new_duration_seconds = 60  # never store an immediately-expired pending key
            summary_parts.append(f"duration → {format_duration(new_duration_seconds)}")
        elif status == "suspended":
            # Suspended licenses keep their expiry frozen on the row; unsuspend computes
            # remaining from (expires_at - now). Edit expires_at to keep that consistent.
            current_expires = row["expires_at"] or now
            if mode == "set":
                new_expires_at = now + delta_seconds
            else:  # extend
                new_expires_at = current_expires + delta_seconds
            if new_expires_at <= now:
                summary_parts.append("no time left (will mark expired on unsuspend)")
            else:
                summary_parts.append(f"remaining → {format_duration(new_expires_at - now)} (suspended)")
        elif status == "active":
            current_expires = row["expires_at"] or now
            if mode == "set":
                new_expires_at = now + delta_seconds
            else:  # extend
                new_expires_at = current_expires + delta_seconds
            if new_expires_at <= now:
                new_status = "expired"
                summary_parts.append("now expired")
            else:
                summary_parts.append(f"remaining → {format_duration(new_expires_at - now)}")
        elif status == "expired":
            # "set" revives from now; "extend" adds delta to the existing expires_at
            # (positive or negative). If the result lands in the future, license revives.
            if mode == "set":
                new_expires_at = now + delta_seconds
            else:  # extend
                base_expires = row["expires_at"] if row["expires_at"] is not None else now
                new_expires_at = base_expires + delta_seconds
            if new_expires_at > now:
                new_status = "active"
                summary_parts.append(f"reactivated, remaining → {format_duration(new_expires_at - now)}")
                # Preserve activated_at if previously set; otherwise stamp now.
                if row["activated_at"] is None:
                    conn.execute("UPDATE licenses SET activated_at = ? WHERE id = ?", (now, license_id))
            else:
                summary_parts.append("still expired")

    # Apply
    conn.execute(
        "UPDATE licenses SET note = ?, duration_seconds = ?, expires_at = ?, status = ? WHERE id = ?",
        (note, int(new_duration_seconds), new_expires_at, new_status, license_id)
    )
    conn.commit()
    conn.close()

    if mode == "note_only":
        summary_parts.append("note updated")
    elif note != (row["note"] or ""):
        summary_parts.append("note updated")

    msg = "License updated: " + "; ".join(summary_parts) if summary_parts else "License updated"

    if is_ajax:
        # Compute fresh remaining for response
        remaining_seconds = 0
        if new_status == "active" and new_expires_at:
            remaining_seconds = max(0, int(new_expires_at - time.time()))
        elif new_status == "suspended" and new_expires_at:
            remaining_seconds = max(0, int(new_expires_at - time.time()))
        elif new_status == "pending":
            remaining_seconds = int(new_duration_seconds)
        return jsonify({
            "success": True,
            "message": msg,
            "license": {
                "id": license_id,
                "status": new_status,
                "expires_at": new_expires_at,
                "duration_seconds": int(new_duration_seconds),
                "remaining_seconds": remaining_seconds,
                "remaining_text": format_duration(remaining_seconds) if remaining_seconds > 0 else (
                    "Expired" if new_status == "expired" else format_duration(new_duration_seconds)
                ),
                "note": note,
            },
        })

    flash(msg, "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/revoke/<int:license_id>", methods=["POST"])
@require_admin
def revoke_license(license_id):
    conn = get_db()
    conn.execute("UPDATE licenses SET status = 'revoked' WHERE id = ?", (license_id,))
    conn.commit()
    conn.close()
    flash("License revoked", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/delete/<int:license_id>", methods=["POST"])
@require_admin
def delete_license(license_id):
    conn = get_db()
    conn.execute("UPDATE licenses SET status = 'deleted' WHERE id = ?", (license_id,))
    conn.commit()
    conn.close()
    flash("License deleted", "success")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/unsuspend_all", methods=["POST"])
@require_admin
def unsuspend_all_licenses():
    conn = get_db()
    rows = conn.execute("SELECT * FROM licenses WHERE status = 'suspended'").fetchall()
    now = time.time()
    recovered = 0
    expired = 0
    for row in rows:
        remaining = 0
        if row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
        if remaining > 0:
            conn.execute(
                "UPDATE licenses SET status = 'pending', registered_ip = NULL, activated_at = NULL, expires_at = NULL, last_heartbeat = NULL, duration_seconds = ? WHERE id = ?",
                (int(remaining), row["id"])
            )
            recovered += 1
        else:
            conn.execute(
                "UPDATE licenses SET status = 'expired', registered_ip = NULL, last_heartbeat = NULL WHERE id = ?",
                (row["id"],)
            )
            expired += 1
    conn.commit()
    conn.close()
    if recovered or expired:
        flash(f"Recovered {recovered} license(s); {expired} had no time left and were marked expired. Customers will re-register their real IP on next launch.", "success")
    else:
        flash("No suspended licenses to recover.", "warning")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/unsuspend/<int:license_id>", methods=["POST"])
@require_admin
def unsuspend_license(license_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM licenses WHERE id = ? AND status = 'suspended'", (license_id,)).fetchone()
    if not row:
        conn.close()
        flash("License not found or not suspended", "error")
        return redirect(request.referrer or url_for("dashboard"))

    now = time.time()
    remaining = 0
    if row["expires_at"]:
        remaining = max(0, row["expires_at"] - now)

    if remaining > 0:
        conn.execute(
            "UPDATE licenses SET status = 'pending', registered_ip = NULL, activated_at = NULL, expires_at = NULL, last_heartbeat = NULL, duration_seconds = ? WHERE id = ?",
            (int(remaining), license_id)
        )
        remaining_text = format_duration(remaining)
        flash(f"License unsuspended — {remaining_text} remaining. User can re-activate.", "success")
    else:
        conn.execute(
            "UPDATE licenses SET status = 'expired', registered_ip = NULL, last_heartbeat = NULL WHERE id = ?",
            (license_id,)
        )
        flash("License unsuspended but had no time remaining — marked as expired.", "warning")

    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


def require_admin_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("admin_logged_in"):
            return f(*args, **kwargs)
        admin_key = request.headers.get("X-Admin-Key", "")
        if admin_key and hmac.compare_digest(admin_key, ADMIN_PASSWORD):
            return f(*args, **kwargs)
        resp = {"success": False, "error": "Admin authentication required"}
        return jsonify({"data": resp, "signature": sign_response(resp)}), 403
    return decorated


@app.route("/api/create", methods=["POST"])
@require_admin_api
def api_create():
    data = request.get_json(silent=True)
    if not data:
        resp = {"success": False, "error": "Missing request body"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    duration_value = int(data.get("duration_value", 1))
    duration_unit = data.get("duration_unit", "hours")
    note = data.get("note", "").strip()

    multipliers = {"minutes": 60, "hours": 3600, "days": 86400}
    duration_seconds = duration_value * multipliers.get(duration_unit, 3600)

    now = time.time()
    key = generate_key()

    conn = get_db()
    conn.execute(
        "INSERT INTO licenses (license_key, created_at, duration_seconds, status, note) VALUES (?, ?, ?, 'pending', ?)",
        (key, now, duration_seconds, note)
    )
    conn.commit()
    conn.close()

    resp = {"success": True, "key": key, "duration_seconds": duration_seconds, "status": "pending"}
    return jsonify({"data": resp, "signature": sign_response(resp)})


@app.route("/api/revoke", methods=["POST"])
@require_admin_api
def api_revoke():
    data = request.get_json(silent=True)
    if not data or "key" not in data:
        resp = {"success": False, "error": "Missing key"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    key = data["key"].strip()
    conn = get_db()
    row = conn.execute("SELECT id, status FROM licenses WHERE license_key = ?", (key,)).fetchone()
    if not row:
        conn.close()
        resp = {"success": False, "error": "License not found"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    conn.execute("UPDATE licenses SET status = 'revoked' WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()

    resp = {"success": True, "key": key, "status": "revoked"}
    return jsonify({"data": resp, "signature": sign_response(resp)})


@app.route("/api/licenses", methods=["POST"])
@require_admin_api
def api_list_licenses():
    conn = get_db()
    now = time.time()
    expire_active_licenses(conn)

    rows = conn.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
    conn.close()

    licenses = []
    for row in rows:
        if row["status"] == "active" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
        elif row["status"] == "suspended" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
        elif row["status"] == "pending":
            remaining = row["duration_seconds"]
        else:
            remaining = 0
        licenses.append({
            "key": row["license_key"],
            "status": row["status"],
            "created_at": row["created_at"],
            "activated_at": row["activated_at"],
            "expires_at": row["expires_at"],
            "remaining_seconds": int(remaining),
            "remaining_text": format_duration(remaining) if row["status"] in ("active", "pending", "suspended") else "-",
            "online": is_online(row["last_heartbeat"]) if row["status"] == "active" else False,
            "last_ip": row["last_ip"] or "",
            "registered_ip": row["registered_ip"] or "",
            "note": row["note"] or "",
        })

    resp = {"success": True, "licenses": licenses, "count": len(licenses)}
    return jsonify({"data": resp, "signature": sign_response(resp)})


@app.route("/api/dashboard_data")
@require_admin
def api_dashboard_data():
    conn = get_db()
    now = time.time()
    expire_active_licenses(conn)

    rows = conn.execute(
        "SELECT * FROM licenses WHERE status IN ('active', 'pending', 'suspended') ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    licenses = []
    kpi_total = len(rows)
    kpi_online = 0
    kpi_suspended = 0
    kpi_expiring = 0
    for row in rows:
        if row["status"] == "active" and row["expires_at"] is not None:
            remaining = row["expires_at"] - now
            remaining_text = format_duration(remaining)
            remaining_seconds = int(remaining)
        elif row["status"] == "suspended" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
            remaining_text = format_duration(remaining) + " (suspended)"
            remaining_seconds = int(remaining)
        elif row["status"] == "active":
            remaining_text = "-"
            remaining_seconds = 0
        else:
            remaining_text = format_duration(row["duration_seconds"])
            remaining_seconds = row["duration_seconds"]

        online = is_online(row["last_heartbeat"])
        if row["status"] == "active" and online:
            kpi_online += 1
        if row["status"] == "suspended":
            kpi_suspended += 1
        if row["status"] == "active" and 0 < remaining_seconds <= 86400:
            kpi_expiring += 1

        licenses.append({
            "id": row["id"],
            "key": row["license_key"],
            "created": format_time(row["created_at"]),
            "activated": format_time(row["activated_at"]),
            "remaining": remaining_text,
            "remaining_seconds": remaining_seconds,
            "online": online,
            "last_heartbeat": format_time(row["last_heartbeat"]),
            "last_ip": row["last_ip"] or "N/A",
            "registered_ip": row["registered_ip"] or "N/A",
            "note": row["note"] or "",
            "status": row["status"],
            "version": row["launcher_version"] or "",
            "expires_at_ts": row["expires_at"],
            "duration_seconds": row["duration_seconds"],
        })

    return jsonify({
        "licenses": licenses,
        "kpis": {
            "total": kpi_total,
            "online": kpi_online,
            "suspended": kpi_suspended,
            "expiring": kpi_expiring,
        },
    })


@app.route("/api/history_data")
@require_admin
def api_history_data():
    conn = get_db()
    now = time.time()
    expire_active_licenses(conn)

    rows = conn.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
    conn.close()

    licenses = []
    for row in rows:
        if row["status"] == "active" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
            remaining_text = format_duration(remaining)
            remaining_seconds = int(remaining)
        elif row["status"] == "suspended" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
            remaining_text = format_duration(remaining) + " (suspended)"
            remaining_seconds = int(remaining)
        elif row["status"] == "pending":
            remaining_text = format_duration(row["duration_seconds"]) + " (pending)"
            remaining_seconds = row["duration_seconds"]
        else:
            remaining_text = "-"
            remaining_seconds = 0

        licenses.append({
            "id": row["id"],
            "key": row["license_key"],
            "created": format_time(row["created_at"]),
            "activated": format_time(row["activated_at"]),
            "expires": format_time(row["expires_at"]) if row["expires_at"] else "Not activated",
            "remaining": remaining_text,
            "remaining_seconds": remaining_seconds,
            "online": is_online(row["last_heartbeat"]) if row["status"] == "active" else False,
            "last_ip": row["last_ip"] or "N/A",
            "registered_ip": row["registered_ip"] or "N/A",
            "note": row["note"] or "",
            "status": row["status"],
            "duration_text": format_duration(row["duration_seconds"]),
            "duration_seconds": int(row["duration_seconds"] or 0),
            "expires_at_ts": row["expires_at"],
            "version": row["launcher_version"] or "",
        })

    return jsonify({"licenses": licenses})


def _encode_secret_xor(plaintext, xor_key=0x57):
    encoded = [ord(c) ^ xor_key for c in plaintext]
    return "[" + ",".join(f"0x{b:02x}" for b in encoded) + "]"


def _sanitize_exe_name(name):
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = sanitized.strip().strip('.')
    sanitized = sanitized.replace(' ', '')
    return sanitized or "RobloxLauncher"


def _convert_to_ico(image_data, output_path):
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(image_data))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icon_images = []
    for size in sizes:
        resized = img.copy()
        resized.thumbnail(size, Image.LANCZOS)
        canvas = Image.new('RGBA', size, (0, 0, 0, 0))
        offset = ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2)
        canvas.paste(resized, offset)
        icon_images.append(canvas)
    icon_images[0].save(output_path, format='ICO', sizes=[(s, s) for s, _ in sizes], append_images=icon_images[1:])


def _safe_str(val):
    return (val or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", "").replace("\r", "")


def _compute_config_hash(config):
    icon_filename = config.get("icon_filename", "") or ""
    icon_bytes_hash = ""
    if icon_filename:
        icon_path = os.path.join(ICONS_DIR, icon_filename)
        if os.path.isfile(icon_path):
            try:
                h = hashlib.sha256()
                with open(icon_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                icon_bytes_hash = h.hexdigest()
            except Exception:
                icon_bytes_hash = ""
    fields = {
        "app_name": config.get("app_name", ""),
        "hardcoded_path": config.get("hardcoded_path", ""),
        "license_server_url": config.get("license_server_url", ""),
        "license_secret": config.get("license_secret", ""),
        "icon_filename": icon_filename,
        "icon_bytes_hash": icon_bytes_hash,
        "embedded_key": config.get("embedded_key", ""),
    }
    raw = json.dumps(fields, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_launcher_app_version():
    launcher_src = os.path.join(SOURCE_DIR, "launcher.py")
    if not os.path.isfile(launcher_src):
        launcher_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.py")
    if not os.path.isfile(launcher_src):
        return None
    try:
        with open(launcher_src, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
        if not m:
            return None
        ver = m.group(1).strip()
        if not re.match(r'^\d+\.\d+\.\d+$', ver):
            return None
        return ver
    except Exception:
        return None


def _patch_launcher_source(source, config, version):
    safe_ver = _safe_str(version)
    source = re.sub(r'APP_VERSION = ".*?"', f'APP_VERSION = "{safe_ver}"', source)
    if config.get("app_name"):
        safe_name = _safe_str(config["app_name"])
        source = re.sub(r'APP_NAME = ".*?"', f'APP_NAME = "{safe_name}"', source)
    path = (config.get("hardcoded_path") or "").replace("\\", "/")
    safe_path = _safe_str(path)
    source = re.sub(r'HARDCODED_PATH = ".*?"', f'HARDCODED_PATH = "{safe_path}"', source)
    if config.get("license_server_url"):
        safe_url = _safe_str(config["license_server_url"])
        source = re.sub(r'LICENSE_SERVER_URL = ".*?"', f'LICENSE_SERVER_URL = "{safe_url}"', source)
    if config.get("license_secret"):
        xor_encoded = _encode_secret_xor(config["license_secret"])
        source = re.sub(r'_LICENSE_SECRET_XOR = \[.*?\]', f'_LICENSE_SECRET_XOR = {xor_encoded}', source)
    if config.get("embedded_key"):
        safe_key = _safe_str(config["embedded_key"])
        source = re.sub(r'EMBEDDED_LICENSE_KEY = ".*?"', f'EMBEDDED_LICENSE_KEY = "{safe_key}"', source)
    cfg_hash = _compute_config_hash(config)
    if re.search(r'CONFIG_HASH = ".*?"', source):
        source = re.sub(r'CONFIG_HASH = ".*?"', f'CONFIG_HASH = "{cfg_hash}"', source)
    else:
        source = re.sub(
            r'(EMBEDDED_LICENSE_KEY = ".*?")',
            f'\\1\nCONFIG_HASH = "{cfg_hash}"',
            source
        )
    cid = int(config.get("id") or 0)
    if re.search(r'CONFIG_ID\s*=\s*\d+', source):
        source = re.sub(r'CONFIG_ID\s*=\s*\d+', f'CONFIG_ID = {cid}', source)
    else:
        source = re.sub(
            r'(CONFIG_HASH = ".*?")',
            f'\\1\nCONFIG_ID = {cid}',
            source
        )
    return source


def _run_single_build(build_id, config, version):
    config_id = config["id"]
    exe_name = _sanitize_exe_name(config.get("app_name", "DenfiRoblox"))
    output_dir = os.path.join(BUILDS_DIR, version, str(config_id))
    os.makedirs(output_dir, exist_ok=True)
    try:
        for _stale in os.listdir(output_dir):
            _stale_path = os.path.join(output_dir, _stale)
            if os.path.isfile(_stale_path):
                try:
                    os.remove(_stale_path)
                    print(f"[BUILD] Removed stale file: {_stale_path}")
                except Exception as _re:
                    print(f"[BUILD] Could not remove {_stale_path}: {_re}")
    except Exception as _le:
        print(f"[BUILD] Could not list {output_dir}: {_le}")
    work_dir = os.path.join(BUILDS_DIR, "_work", f"{build_id}_{config_id}")
    os.makedirs(work_dir, exist_ok=True)

    try:
        print(f"[BUILD] Config #{config_id}: app_name='{config.get('app_name', '')}', icon='{config.get('icon_filename', '')}', path='{config.get('hardcoded_path', '')}', exe_name='{exe_name}'")

        with _build_lock:
            if build_id in _build_progress:
                _build_progress[build_id]["artifacts"][config_id] = {
                    "status": "building", "progress": 0, "name": config.get("app_name", "")
                }

        conn = get_db()
        conn.execute(
            "UPDATE build_artifacts SET status='building', started_at=? WHERE build_id=? AND build_config_id=?",
            (time.time(), build_id, config_id)
        )
        conn.commit()
        conn.close()

        launcher_src = os.path.join(SOURCE_DIR, "launcher.py")
        if not os.path.isfile(launcher_src):
            launcher_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.py")
        if not os.path.isfile(launcher_src):
            raise FileNotFoundError("launcher.py not found. Place it next to license_server/ folder or inside it.")
        with open(launcher_src, "r", encoding="utf-8") as f:
            source = f.read()

        source = _patch_launcher_source(source, config, version)
        patched_path = os.path.join(work_dir, "launcher.py")
        with open(patched_path, "w", encoding="utf-8") as f:
            f.write(source)

        icon_path = None
        if config.get("icon_filename"):
            src_icon = os.path.join(ICONS_DIR, config["icon_filename"])
            if os.path.isfile(src_icon):
                dst_icon = os.path.join(work_dir, "icon.ico")
                shutil.copyfile(src_icon, dst_icon)
                icon_path = dst_icon
                try:
                    ih = hashlib.sha256()
                    with open(src_icon, "rb") as _f:
                        for _chunk in iter(lambda: _f.read(65536), b""):
                            ih.update(_chunk)
                    print(f"[BUILD] Config #{config_id}: icon bytes sha256={ih.hexdigest()[:16]}... ({os.path.getsize(src_icon)} bytes)")
                except Exception:
                    pass

        for splash_ext in [".gif", ".png"]:
            splash_src = None
            for splash_dir in [SOURCE_DIR, os.path.dirname(os.path.abspath(__file__))]:
                candidate = os.path.join(splash_dir, f"splash_logo{splash_ext}")
                if os.path.isfile(candidate):
                    splash_src = candidate
                    break
            if splash_src:
                shutil.copy2(splash_src, os.path.join(work_dir, os.path.basename(splash_src)))

        font_file = None
        for font_dir in [SOURCE_DIR, os.path.dirname(os.path.abspath(__file__))]:
            candidate = os.path.join(font_dir, "Roblox2017.ttf")
            if os.path.isfile(candidate):
                font_file = candidate
                break
        if font_file:
            shutil.copy2(font_file, os.path.join(work_dir, "Roblox2017.ttf"))

        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile", "--windowed", "--clean",
            "--name", exe_name,
            "--distpath", output_dir,
            "--workpath", os.path.join(work_dir, "build"),
            "--specpath", work_dir,
        ]
        if icon_path:
            cmd.extend(["--icon", icon_path])
            cmd.extend(["--add-data", f"{icon_path}{os.pathsep}."])
        for splash_ext in [".gif", ".png"]:
            splash_work = os.path.join(work_dir, f"splash_logo{splash_ext}")
            if os.path.isfile(splash_work):
                cmd.extend(["--add-data", f"{splash_work}{os.pathsep}."])
        font_work = os.path.join(work_dir, "Roblox2017.ttf")
        if os.path.isfile(font_work):
            cmd.extend(["--add-data", f"{font_work}{os.pathsep}."])
        cmd.append(patched_path)

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=work_dir
        )
        progress_steps = 0
        last_emitted = 0
        for line in process.stdout:
            progress_steps += 1
            estimated = min(95, int(progress_steps * 1.5))
            with _build_lock:
                if build_id in _build_progress:
                    _build_progress[build_id]["artifacts"][config_id]["progress"] = estimated
            if estimated != last_emitted:
                last_emitted = estimated
                try:
                    socketio.emit('build_progress', {
                        'build_id': build_id, 'config_id': config_id,
                        'progress': estimated, 'status': 'building',
                        'name': config.get("app_name", ""),
                    }, namespace='/')
                except Exception:
                    pass
                if estimated % 5 == 0:
                    conn = get_db()
                    conn.execute(
                        "UPDATE build_artifacts SET progress=? WHERE build_id=? AND build_config_id=?",
                        (estimated, build_id, config_id)
                    )
                    conn.commit()
                    conn.close()

        process.wait()
        if process.returncode != 0:
            raise Exception(f"PyInstaller failed with code {process.returncode}")

        exe_path = os.path.join(output_dir, f"{exe_name}.exe")
        if not os.path.isfile(exe_path):
            exe_path_alt = os.path.join(output_dir, exe_name)
            if os.path.isfile(exe_path_alt):
                exe_path = exe_path_alt
            else:
                raise Exception("Build output not found")

        file_size = os.path.getsize(exe_path)

        expected_name = config.get("app_name", "")
        if expected_name:
            try:
                with open(exe_path, "rb") as ef:
                    exe_bytes = ef.read()
                name_bytes = expected_name.encode("utf-8")
                if name_bytes in exe_bytes:
                    print(f"[BUILD] Config #{config_id}: VERIFIED — exe contains APP_NAME '{expected_name}'")
                else:
                    print(f"[BUILD] Config #{config_id}: WARNING — exe does NOT contain expected APP_NAME '{expected_name}'")
            except Exception as ve:
                print(f"[BUILD] Config #{config_id}: Could not verify exe: {ve}")

        cfg_hash = _compute_config_hash(config)
        conn = get_db()
        conn.execute(
            "UPDATE build_artifacts SET status='completed', progress=100, exe_filename=?, file_size=?, config_hash=?, app_name_snapshot=?, completed_at=? WHERE build_id=? AND build_config_id=?",
            (os.path.basename(exe_path), file_size, cfg_hash, config.get("app_name", ""), time.time(), build_id, config_id)
        )
        conn.commit()
        conn.close()

        with _build_lock:
            if build_id in _build_progress:
                _build_progress[build_id]["artifacts"][config_id] = {
                    "status": "completed", "progress": 100,
                    "name": config.get("app_name", ""),
                    "filename": os.path.basename(exe_path), "size": file_size
                }
        try:
            socketio.emit('build_progress', {
                'build_id': build_id, 'config_id': config_id,
                'progress': 100, 'status': 'completed',
                'name': config.get("app_name", ""),
                'filename': os.path.basename(exe_path), 'size': file_size,
            }, namespace='/')
        except Exception:
            pass
        return True

    except Exception as e:
        conn = get_db()
        conn.execute(
            "UPDATE build_artifacts SET status='failed', error_message=?, completed_at=? WHERE build_id=? AND build_config_id=?",
            (str(e)[:500], time.time(), build_id, config_id)
        )
        conn.commit()
        conn.close()
        with _build_lock:
            if build_id in _build_progress:
                _build_progress[build_id]["artifacts"][config_id] = {
                    "status": "failed", "progress": 0,
                    "name": config.get("app_name", ""), "error": str(e)[:200]
                }
        try:
            socketio.emit('build_progress', {
                'build_id': build_id, 'config_id': config_id,
                'progress': 0, 'status': 'failed',
                'name': config.get("app_name", ""),
                'error': str(e)[:200],
            }, namespace='/')
        except Exception:
            pass
        return False
    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def _run_build_all(build_id, version, configs):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    conn = get_db()
    conn.execute("UPDATE builds SET status='building', started_at=? WHERE id=?", (time.time(), build_id))
    conn.commit()
    conn.close()

    completed = [0]
    failed = [0]
    count_lock = threading.Lock()

    def build_one(config):
        success = _run_single_build(build_id, config, version)
        with count_lock:
            if success:
                completed[0] += 1
            else:
                failed[0] += 1
            total_done = completed[0] + failed[0]
        conn2 = get_db()
        conn2.execute("UPDATE builds SET completed_configs=? WHERE id=?", (total_done, build_id))
        conn2.commit()
        conn2.close()
        with _build_lock:
            if build_id in _build_progress:
                _build_progress[build_id]["completed"] = total_done
        return success

    max_workers = min(3, len(configs))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(build_one, cfg): cfg for cfg in configs}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                with count_lock:
                    failed[0] += 1

    final_status = "completed" if failed[0] == 0 else ("failed" if completed[0] == 0 else "completed")
    error_msg = f"{failed[0]} config(s) failed" if failed[0] > 0 else ""
    conn = get_db()
    conn.execute(
        "UPDATE builds SET status=?, completed_at=?, error_message=? WHERE id=?",
        (final_status, time.time(), error_msg, build_id)
    )
    conn.commit()
    conn.close()
    with _build_lock:
        if build_id in _build_progress:
            _build_progress[build_id]["status"] = final_status
            _build_progress[build_id]["error"] = error_msg


@app.route("/splash_preview")
def splash_preview():
    splash_file = None
    for ext in [".gif", ".png"]:
        for d in [SOURCE_DIR, os.path.dirname(os.path.abspath(__file__))]:
            candidate = os.path.join(d, f"splash_logo{ext}")
            if os.path.isfile(candidate):
                splash_file = f"splash_logo{ext}"
                break
        if splash_file:
            break
    app_name = request.args.get("app_name", "ROBLOX")
    return render_template("splash_preview.html", splash_file=splash_file, app_name=app_name)


@app.route("/splash_logo_file")
def splash_logo_file():
    for ext in [".gif", ".png"]:
        for d in [SOURCE_DIR, os.path.dirname(os.path.abspath(__file__))]:
            candidate = os.path.join(d, f"splash_logo{ext}")
            if os.path.isfile(candidate):
                mime = "image/gif" if ext == ".gif" else "image/png"
                return send_file(candidate, mimetype=mime)
    return "No splash logo found", 404


@app.route("/ota_log")
@require_admin
def ota_log_page():
    with _recent_ota_lock:
        entries = list(reversed(_recent_ota_log))
    rows_html = ""
    for e in entries:
        ts_str = time.strftime("%H:%M:%S", time.localtime(e.get("ts", 0)))
        result = e.get("result", "?")
        color = {"update": "#10b981", "no_update": "#f59e0b", "no_match": "#ef4444"}.get(result, "#6b7280")
        rows_html += f"""<tr>
            <td>{ts_str}</td>
            <td><span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{result.upper()}</span></td>
            <td>{e.get("key","")}</td>
            <td>{e.get("app_name","") or "<i>(empty)</i>"}</td>
            <td>{e.get("client_config_id", e.get("config_id","")) or "<i>0</i>"}</td>
            <td><code>{e.get("client_hash", e.get("config_hash",""))}</code></td>
            <td><code>{e.get("server_hash","")}</code></td>
            <td>{e.get("matched_config_id","")} {('('+e.get("matched_app_name","")+')') if e.get("matched_app_name") else ""}</td>
            <td>{e.get("current_version","")} → {e.get("latest_version","")}</td>
            <td>cfg_changed={e.get("cfg_changed","")} ver_newer={e.get("ver_newer","")}</td>
        </tr>"""
    if not rows_html:
        rows_html = '<tr><td colspan="10" style="text-align:center;padding:40px;color:#888;">No OTA requests recorded yet. Run an old launcher to capture traffic.</td></tr>'
    return f"""<!doctype html><html><head><title>OTA Log</title>
<meta http-equiv="refresh" content="3">
<style>body{{font-family:Segoe UI,sans-serif;background:#1a1a1a;color:#e0e0e0;padding:20px;}}
table{{width:100%;border-collapse:collapse;font-size:13px;}}
th,td{{padding:8px;border-bottom:1px solid #333;text-align:left;vertical-align:top;}}
th{{background:#252525;}}code{{background:#2a2a2a;padding:2px 4px;border-radius:3px;font-size:11px;}}
a{{color:#60a5fa;}}</style></head><body>
<h1>Recent OTA Update Checks</h1>
<p><a href="/builds">← back to builds</a> &nbsp; auto-refreshes every 3s &nbsp; (last {len(entries)} requests)</p>
<table><thead><tr>
<th>Time</th><th>Result</th><th>Key</th><th>App Name (sent)</th><th>cfg_id sent</th>
<th>Client hash</th><th>Server hash</th><th>Matched config</th><th>Version</th><th>Notes</th>
</tr></thead><tbody>{rows_html}</tbody></table></body></html>"""


@app.route("/builds")
@require_admin
def builds_page():
    conn = get_db()
    configs = conn.execute("""
        SELECT bc.*, l.license_key, l.note as license_note
        FROM build_configs bc
        LEFT JOIN licenses l ON bc.license_id = l.id
        ORDER BY bc.created_at DESC
    """).fetchall()
    past_builds = conn.execute("SELECT * FROM builds ORDER BY created_at DESC LIMIT 500").fetchall()
    conn.close()

    all_artifacts = {}
    if past_builds:
        build_ids = [b["id"] for b in past_builds]
        placeholders = ",".join("?" * len(build_ids))
        conn2 = get_db()
        arts = conn2.execute(f"""
            SELECT ba.build_id, ba.build_config_id, ba.exe_filename, ba.file_size, ba.status,
                   bc.app_name
            FROM build_artifacts ba
            LEFT JOIN build_configs bc ON ba.build_config_id = bc.id
            WHERE ba.build_id IN ({placeholders})
        """, build_ids).fetchall()
        conn2.close()
        for a in arts:
            bid = a["build_id"]
            if bid not in all_artifacts:
                all_artifacts[bid] = []
            all_artifacts[bid].append({
                "config_id": a["build_config_id"],
                "app_name": a["app_name"] or "Unknown",
                "exe_filename": a["exe_filename"] or "",
                "file_size": a["file_size"] or 0,
                "status": a["status"],
            })

    build_list = []
    for b in past_builds:
        build_list.append({
            "id": b["id"], "version": b["version"], "status": b["status"],
            "total": b["total_configs"], "completed": b["completed_configs"],
            "started": format_time(b["started_at"]), "finished": format_time(b["completed_at"]),
            "error": b["error_message"] or "",
            "artifacts": all_artifacts.get(b["id"], []),
        })

    config_list = []
    for c in configs:
        config_list.append({
            "id": c["id"], "app_name": c["app_name"],
            "hardcoded_path": c["hardcoded_path"],
            "license_key": c["license_key"] or "None",
            "license_note": c["license_note"] or "",
            "has_icon": bool(c["icon_filename"]),
            "license_server_url": c["license_server_url"] or "",
        })

    return render_template("builds.html", configs=config_list, builds=build_list)


@app.route("/build_config/create", methods=["GET", "POST"])
@require_admin
def create_build_config():
    conn = get_db()
    if request.method == "POST":
        license_id = request.form.get("license_id", "")
        license_id = int(license_id) if license_id else None
        app_name = request.form.get("app_name", "DENFI ROBLOX").strip()
        hardcoded_path = request.form.get("hardcoded_path", "").strip()
        license_server_url = request.form.get("license_server_url", "").strip()
        license_secret = request.form.get("license_secret", "DENFI_LICENSE_SECRET_KEY_2024").strip()
        embedded_key = request.form.get("embedded_key", "").strip()

        icon_filename = ""
        icon_file = request.files.get("icon")
        if icon_file and icon_file.filename:
            os.makedirs(ICONS_DIR, exist_ok=True)
            config_id_temp = str(uuid.uuid4().hex[:8])
            ext = os.path.splitext(icon_file.filename)[1].lower()
            if ext in ('.ico',):
                icon_filename = f"{config_id_temp}.ico"
                icon_file.save(os.path.join(ICONS_DIR, icon_filename))
            elif ext in ('.png', '.jpg', '.jpeg', '.jfif', '.bmp', '.webp'):
                icon_filename = f"{config_id_temp}.ico"
                _convert_to_ico(icon_file.read(), os.path.join(ICONS_DIR, icon_filename))

        conn.execute(
            "INSERT INTO build_configs (license_id, app_name, hardcoded_path, license_server_url, license_secret, icon_filename, embedded_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (license_id, app_name, hardcoded_path, license_server_url, license_secret, icon_filename, embedded_key, time.time())
        )
        conn.commit()
        conn.close()
        flash(f"Build config created for '{app_name}'", "success")
        return redirect(url_for("builds_page"))

    licenses = conn.execute(
        "SELECT id, license_key, note, status FROM licenses WHERE status IN ('active', 'pending', 'suspended') ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return render_template("build_config_form.html", config=None, licenses=licenses)


@app.route("/build_config/<int:config_id>/edit", methods=["GET", "POST"])
@require_admin
def edit_build_config(config_id):
    conn = get_db()
    config = conn.execute("SELECT * FROM build_configs WHERE id = ?", (config_id,)).fetchone()
    if not config:
        conn.close()
        flash("Build config not found", "error")
        return redirect(url_for("builds_page"))

    if request.method == "POST":
        license_id = request.form.get("license_id", "")
        license_id = int(license_id) if license_id else None
        app_name = request.form.get("app_name", "DENFI ROBLOX").strip()
        hardcoded_path = request.form.get("hardcoded_path", "").strip()
        license_server_url = request.form.get("license_server_url", "").strip()
        license_secret = request.form.get("license_secret", "DENFI_LICENSE_SECRET_KEY_2024").strip()
        embedded_key = request.form.get("embedded_key", "").strip()

        icon_filename = config["icon_filename"]
        icon_file = request.files.get("icon")
        if icon_file and icon_file.filename:
            os.makedirs(ICONS_DIR, exist_ok=True)
            ext = os.path.splitext(icon_file.filename)[1].lower()
            new_icon = f"{config_id}.ico"
            if ext in ('.ico',):
                icon_file.save(os.path.join(ICONS_DIR, new_icon))
                icon_filename = new_icon
            elif ext in ('.png', '.jpg', '.jpeg', '.jfif', '.bmp', '.webp'):
                _convert_to_ico(icon_file.read(), os.path.join(ICONS_DIR, new_icon))
                icon_filename = new_icon

        conn.execute(
            "UPDATE build_configs SET license_id=?, app_name=?, hardcoded_path=?, license_server_url=?, license_secret=?, icon_filename=?, embedded_key=?, updated_at=? WHERE id=?",
            (license_id, app_name, hardcoded_path, license_server_url, license_secret, icon_filename, embedded_key, time.time(), config_id)
        )
        conn.commit()
        conn.close()
        flash(f"Build config updated for '{app_name}'", "success")
        return redirect(url_for("builds_page"))

    licenses = conn.execute(
        "SELECT id, license_key, note, status FROM licenses WHERE status IN ('active', 'pending', 'suspended') ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    config_dict = {
        "id": config["id"], "license_id": config["license_id"],
        "app_name": config["app_name"], "hardcoded_path": config["hardcoded_path"],
        "license_server_url": config["license_server_url"],
        "license_secret": config["license_secret"], "icon_filename": config["icon_filename"],
        "embedded_key": config["embedded_key"] or "",
    }
    return render_template("build_config_form.html", config=config_dict, licenses=licenses)


def _purge_artifacts_for_config(conn, config_id):
    """Remove build artifacts (DB rows + .exe files on disk) for a config,
    and clean up parent `builds` rows that have no artifacts left.
    Returns (files_removed, builds_removed)."""
    rows = conn.execute(
        "SELECT ba.build_id, ba.exe_filename, b.version "
        "FROM build_artifacts ba JOIN builds b ON ba.build_id = b.id "
        "WHERE ba.build_config_id = ?",
        (config_id,)
    ).fetchall()
    affected_builds = set()
    files_removed = 0
    for r in rows:
        affected_builds.add(r["build_id"])
        if r["exe_filename"] and r["version"]:
            fp = os.path.join(BUILDS_DIR, r["version"], str(config_id), r["exe_filename"])
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                    files_removed += 1
                except Exception:
                    pass
            # try removing the now-empty per-config directory
            cfg_dir = os.path.join(BUILDS_DIR, r["version"], str(config_id))
            if os.path.isdir(cfg_dir):
                try:
                    if not os.listdir(cfg_dir):
                        os.rmdir(cfg_dir)
                except Exception:
                    pass
    conn.execute("DELETE FROM build_artifacts WHERE build_config_id = ?", (config_id,))
    builds_removed = 0
    for bid in affected_builds:
        remaining = conn.execute(
            "SELECT COUNT(*) AS n FROM build_artifacts WHERE build_id = ?", (bid,)
        ).fetchone()["n"]
        if remaining == 0:
            conn.execute("DELETE FROM builds WHERE id = ?", (bid,))
            builds_removed += 1
    return files_removed, builds_removed


@app.route("/build_config/<int:config_id>/delete", methods=["POST"])
@require_admin
def delete_build_config(config_id):
    conn = get_db()
    config = conn.execute("SELECT icon_filename FROM build_configs WHERE id = ?", (config_id,)).fetchone()
    if config and config["icon_filename"]:
        icon_path = os.path.join(ICONS_DIR, config["icon_filename"])
        if os.path.isfile(icon_path):
            try:
                os.remove(icon_path)
            except Exception:
                pass
    files_removed, builds_removed = _purge_artifacts_for_config(conn, config_id)
    conn.execute("DELETE FROM build_configs WHERE id = ?", (config_id,))
    conn.commit()
    conn.close()
    bits = ["Build config deleted"]
    if files_removed or builds_removed:
        extras = []
        if files_removed:
            extras.append(f"{files_removed} artifact file(s)")
        if builds_removed:
            extras.append(f"{builds_removed} empty build(s)")
        bits.append("(also removed " + ", ".join(extras) + ")")
    flash(" ".join(bits), "success")
    return redirect(url_for("builds_page"))


@app.route("/build_configs/bulk_edit", methods=["POST"])
@require_admin
def bulk_edit_build_configs():
    config_ids = request.form.getlist("config_ids")
    config_ids = [int(x) for x in config_ids if str(x).strip().isdigit()]
    if not config_ids:
        flash("No configs selected", "error")
        return redirect(url_for("builds_page"))

    update_url = request.form.get("update_server_url") == "on"
    update_secret = request.form.get("update_secret") == "on"
    then_rebuild = request.form.get("then_rebuild") == "on"
    if not (update_url or update_secret or then_rebuild):
        flash("Pick at least one option (update a field and/or rebuild)", "error")
        return redirect(url_for("builds_page"))

    new_url = request.form.get("license_server_url", "").strip()
    new_secret = request.form.get("license_secret", "").strip()

    conn = get_db()
    placeholders = ",".join("?" * len(config_ids))

    fields_updated = 0
    if update_url or update_secret:
        sets = []
        params = []
        if update_url:
            sets.append("license_server_url = ?")
            params.append(new_url)
        if update_secret:
            sets.append("license_secret = ?")
            params.append(new_secret)
        sets.append("updated_at = ?")
        params.append(time.time())
        sql = f"UPDATE build_configs SET {', '.join(sets)} WHERE id IN ({placeholders})"
        conn.execute(sql, (*params, *config_ids))
        conn.commit()
        fields_updated = len(config_ids)

    if not then_rebuild:
        conn.close()
        flash(f"Updated {fields_updated} build config(s)", "success")
        return redirect(url_for("builds_page"))

    rebuild_version = _get_launcher_app_version()
    if not rebuild_version:
        conn.close()
        flash(f"Updated {fields_updated} config(s) but rebuild was skipped — could not read APP_VERSION from launcher.py", "error")
        return redirect(url_for("builds_page"))

    active_build = conn.execute("SELECT id FROM builds WHERE status IN ('pending', 'building') LIMIT 1").fetchone()
    if active_build:
        conn.close()
        flash(f"Updated {len(config_ids)} config(s) but rebuild was skipped — another build is in progress", "error")
        return redirect(url_for("builds_page"))

    expire_active_licenses(conn)
    configs = conn.execute(f"""
        SELECT bc.*, l.license_key, l.status as license_status
        FROM build_configs bc
        LEFT JOIN licenses l ON bc.license_id = l.id
        WHERE bc.id IN ({placeholders})
    """, config_ids).fetchall()

    config_list = []
    skipped = 0
    for c in configs:
        if c["license_status"] not in ('active', None):
            skipped += 1
            continue
        config_list.append({
            "id": c["id"], "app_name": c["app_name"],
            "hardcoded_path": c["hardcoded_path"],
            "license_server_url": c["license_server_url"],
            "license_secret": c["license_secret"],
            "icon_filename": c["icon_filename"],
            "embedded_key": c["embedded_key"] or (c["license_key"] or ""),
            "license_id": c["license_id"],
        })

    if not config_list:
        conn.close()
        flash(f"Updated {len(config_ids)} config(s) but rebuild was skipped — no eligible configs (all licenses inactive)", "error")
        return redirect(url_for("builds_page"))

    now = time.time()
    cursor = conn.execute(
        "INSERT INTO builds (version, status, total_configs, created_at) VALUES (?, 'pending', ?, ?)",
        (rebuild_version, len(config_list), now)
    )
    build_id = cursor.lastrowid
    for cfg in config_list:
        conn.execute(
            "INSERT INTO build_artifacts (build_id, build_config_id, license_id, status) VALUES (?, ?, ?, 'pending')",
            (build_id, cfg["id"], cfg["license_id"])
        )
    conn.commit()
    conn.close()

    with _build_lock:
        _build_progress[build_id] = {
            "status": "pending", "version": rebuild_version,
            "total": len(config_list), "completed": 0,
            "artifacts": {}, "error": "",
        }

    threading.Thread(target=_run_build_all, args=(build_id, rebuild_version, config_list), daemon=True).start()

    if fields_updated:
        msg = f"Updated {fields_updated} config(s) and started rebuild v{rebuild_version} for {len(config_list)} of them"
    else:
        msg = f"Started rebuild v{rebuild_version} for {len(config_list)} config(s)"
    if skipped:
        msg += f" (skipped {skipped} with inactive licenses)"
    flash(msg, "success")
    return redirect(url_for("builds_page"))


@app.route("/builds/bulk_delete", methods=["POST"])
@require_admin
def bulk_delete_builds():
    build_ids = request.form.getlist("build_ids")
    build_ids = [int(x) for x in build_ids if str(x).strip().isdigit()]
    if not build_ids:
        flash("No builds selected", "error")
        return redirect(url_for("builds_page"))

    conn = get_db()
    placeholders = ",".join("?" * len(build_ids))
    rows = conn.execute(
        f"SELECT id, version, status FROM builds WHERE id IN ({placeholders})",
        build_ids
    ).fetchall()

    deletable = [r for r in rows if r["status"] not in ("pending", "building")]
    skipped = len(rows) - len(deletable)
    if not deletable:
        conn.close()
        flash("No builds were eligible to delete (all running)", "error")
        return redirect(url_for("builds_page"))

    deletable_ids = [r["id"] for r in deletable]
    versions_in_batch = {r["version"] for r in deletable}
    del_ph = ",".join("?" * len(deletable_ids))
    conn.execute(f"DELETE FROM build_artifacts WHERE build_id IN ({del_ph})", deletable_ids)
    conn.execute(f"DELETE FROM builds WHERE id IN ({del_ph})", deletable_ids)
    conn.commit()

    for version in versions_in_batch:
        other = conn.execute("SELECT id FROM builds WHERE version = ? LIMIT 1", (version,)).fetchone()
        if not other:
            version_dir = os.path.join(BUILDS_DIR, version)
            if os.path.isdir(version_dir):
                try:
                    shutil.rmtree(version_dir, ignore_errors=True)
                except Exception:
                    pass
    conn.close()

    msg = f"Deleted {len(deletable)} build(s)"
    if skipped:
        msg += f" (skipped {skipped} still running)"
    flash(msg, "success")
    return redirect(url_for("builds_page"))


@app.route("/build/<int:build_id>/delete", methods=["POST"])
@require_admin
def delete_build(build_id):
    conn = get_db()
    build = conn.execute("SELECT id, version, status FROM builds WHERE id = ?", (build_id,)).fetchone()
    if not build:
        conn.close()
        flash("Build not found", "error")
        return redirect(url_for("builds_page"))

    if build["status"] in ("pending", "building"):
        conn.close()
        flash("Cannot delete a build that is still running", "error")
        return redirect(url_for("builds_page"))

    version = build["version"]
    conn.execute("DELETE FROM build_artifacts WHERE build_id = ?", (build_id,))
    conn.execute("DELETE FROM builds WHERE id = ?", (build_id,))
    conn.commit()
    conn.close()

    other = None
    try:
        conn2 = get_db()
        other = conn2.execute("SELECT id FROM builds WHERE version = ? LIMIT 1", (version,)).fetchone()
        conn2.close()
    except Exception:
        pass

    if not other:
        version_dir = os.path.join(BUILDS_DIR, version)
        if os.path.isdir(version_dir):
            try:
                shutil.rmtree(version_dir, ignore_errors=True)
            except Exception:
                pass

    flash(f"Build v{version} deleted", "success")
    return redirect(url_for("builds_page"))


@app.route("/build_config/<int:config_id>/rebuild", methods=["POST"])
@require_admin
def rebuild_single_config(config_id):
    conn = get_db()

    active_build = conn.execute("SELECT id FROM builds WHERE status IN ('pending', 'building') LIMIT 1").fetchone()
    if active_build:
        conn.close()
        flash("A build is already in progress. Wait for it to finish.", "error")
        return redirect(url_for("builds_page"))

    config = conn.execute("SELECT * FROM build_configs WHERE id = ?", (config_id,)).fetchone()
    if not config:
        conn.close()
        flash("Build config not found", "error")
        return redirect(url_for("builds_page"))

    license_row = None
    if config["license_id"]:
        license_row = conn.execute("SELECT license_key, status FROM licenses WHERE id = ?", (config["license_id"],)).fetchone()
        if license_row and license_row["status"] != 'active':
            conn.close()
            flash(f"Cannot rebuild — license is '{license_row['status']}', not active", "error")
            return redirect(url_for("builds_page"))

    version = _get_launcher_app_version()
    if not version:
        conn.close()
        flash("Could not read APP_VERSION from launcher.py — make sure it's uploaded.", "error")
        return redirect(url_for("builds_page"))
    embedded_key = config["embedded_key"] or (license_row["license_key"] if license_row else "") or ""

    now = time.time()
    cursor = conn.execute(
        "INSERT INTO builds (version, status, total_configs, created_at) VALUES (?, 'pending', 1, ?)",
        (version, now)
    )
    build_id = cursor.lastrowid

    conn.execute(
        "INSERT INTO build_artifacts (build_id, build_config_id, license_id, status) VALUES (?, ?, ?, 'pending')",
        (build_id, config_id, config["license_id"])
    )
    conn.commit()
    conn.close()

    config_dict = {
        "id": config["id"], "app_name": config["app_name"],
        "hardcoded_path": config["hardcoded_path"],
        "license_server_url": config["license_server_url"],
        "license_secret": config["license_secret"],
        "icon_filename": config["icon_filename"],
        "embedded_key": embedded_key,
    }

    with _build_lock:
        _build_progress[build_id] = {
            "status": "pending", "version": version,
            "total": 1, "completed": 0,
            "artifacts": {}, "error": "",
        }

    def run_single_rebuild():
        conn2 = get_db()
        conn2.execute("UPDATE builds SET status='building', started_at=? WHERE id=?", (time.time(), build_id))
        conn2.commit()
        conn2.close()

        success = _run_single_build(build_id, config_dict, version)

        final_status = "completed" if success else "failed"
        error_msg = "" if success else "Build failed"
        conn3 = get_db()
        conn3.execute(
            "UPDATE builds SET status=?, completed_configs=?, completed_at=?, error_message=? WHERE id=?",
            (final_status, 1 if success else 0, time.time(), error_msg, build_id)
        )
        conn3.commit()
        conn3.close()
        with _build_lock:
            if build_id in _build_progress:
                _build_progress[build_id]["status"] = final_status
                _build_progress[build_id]["completed"] = 1 if success else 0
                _build_progress[build_id]["error"] = error_msg

    thread = threading.Thread(target=run_single_rebuild, daemon=True)
    thread.start()

    flash(f"Rebuild started for '{config['app_name']}' using v{version}", "success")
    return redirect(url_for("builds_page"))


@app.route("/api/upload_launcher", methods=["POST"])
@require_admin
def api_upload_launcher():
    launcher_file = request.files.get("launcher_file")
    if not launcher_file or not launcher_file.filename:
        flash("No file selected", "error")
        return redirect(url_for("builds_page"))

    content = launcher_file.read().decode("utf-8", errors="replace")
    if "APP_VERSION" not in content or "QApplication" not in content:
        flash("Invalid launcher.py — missing expected launcher code", "error")
        return redirect(url_for("builds_page"))

    dest_path = os.path.join(SOURCE_DIR, "launcher.py")
    alt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.py")

    saved_to = None
    try:
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(content)
        saved_to = dest_path
    except Exception:
        try:
            with open(alt_path, "w", encoding="utf-8") as f:
                f.write(content)
            saved_to = alt_path
        except Exception as e:
            flash(f"Failed to save launcher.py: {e}", "error")
            return redirect(url_for("builds_page"))

    ver_match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
    detected_ver = ver_match.group(1) if ver_match else "unknown"

    flash(f"Launcher uploaded successfully! Detected version: {detected_ver}. Saved to: {os.path.basename(os.path.dirname(saved_to))}/{os.path.basename(saved_to)}", "success")
    return redirect(url_for("builds_page"))


@app.route("/api/upload_server", methods=["POST"])
@require_admin
def api_upload_server():
    server_file = request.files.get("server_file")
    if not server_file or not server_file.filename:
        flash("No file selected", "error")
        return redirect(url_for("builds_page"))

    content = server_file.read().decode("utf-8", errors="replace")
    if "Flask" not in content or "def init_db" not in content:
        flash("Invalid server.py — missing expected server code", "error")
        return redirect(url_for("builds_page"))

    try:
        compile(content, "server.py", "exec")
    except SyntaxError as e:
        flash(f"Syntax error in uploaded server.py (line {e.lineno}): {e.msg}", "error")
        return redirect(url_for("builds_page"))

    server_path = os.path.abspath(__file__)

    backup_path = server_path + ".bak"
    try:
        shutil.copy2(server_path, backup_path)
    except Exception:
        pass

    try:
        with open(server_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        if os.path.isfile(backup_path):
            shutil.copy2(backup_path, server_path)
        flash(f"Failed to save server.py: {e}", "error")
        return redirect(url_for("builds_page"))

    flash("Server uploaded successfully! The server will restart in 3 seconds...", "success")

    def delayed_restart():
        import time as _t
        _t.sleep(3)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    restart_thread = threading.Thread(target=delayed_restart, daemon=True)
    restart_thread.start()

    return redirect(url_for("builds_page"))


@app.route("/api/server_info")
@require_admin
def api_server_info():
    server_path = os.path.abspath(__file__)
    if not os.path.isfile(server_path):
        return jsonify({"found": False})

    try:
        with open(server_path, "r", encoding="utf-8") as f:
            content = f.read()
        ver_match = re.search(r'^SERVER_VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if not ver_match:
            ver_match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        size = os.path.getsize(server_path)
        mtime = os.path.getmtime(server_path)
        return jsonify({
            "found": True,
            "version": ver_match.group(1) if ver_match else "unknown",
            "size": size,
            "modified": mtime,
            "path": server_path,
        })
    except Exception as e:
        return jsonify({"found": False, "error": str(e)})


@app.route("/api/launcher_info")
@require_admin
def api_launcher_info():
    launcher_src = os.path.join(SOURCE_DIR, "launcher.py")
    if not os.path.isfile(launcher_src):
        launcher_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.py")
    if not os.path.isfile(launcher_src):
        return jsonify({"found": False})

    try:
        with open(launcher_src, "r", encoding="utf-8") as f:
            content = f.read()
        ver_match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
        name_match = re.search(r'APP_NAME\s*=\s*"([^"]+)"', content)
        size = os.path.getsize(launcher_src)
        mtime = os.path.getmtime(launcher_src)
        return jsonify({
            "found": True,
            "version": ver_match.group(1) if ver_match else "unknown",
            "app_name": name_match.group(1) if name_match else "unknown",
            "size": size,
            "modified": mtime,
            "path": launcher_src,
        })
    except Exception as e:
        return jsonify({"found": False, "error": str(e)})


@app.route("/api/trigger_build", methods=["POST"])
@require_admin
def api_trigger_build():
    version = request.form.get("version", "").strip()
    if not version:
        flash("Version is required", "error")
        return redirect(url_for("builds_page"))

    if not re.match(r'^\d+\.\d+\.\d+$', version):
        flash("Version must be in format X.Y.Z (e.g. 1.1.0)", "error")
        return redirect(url_for("builds_page"))

    conn = get_db()
    active_build = conn.execute("SELECT id FROM builds WHERE status IN ('pending', 'building') LIMIT 1").fetchone()
    if active_build:
        conn.close()
        flash("A build is already in progress. Wait for it to finish.", "error")
        return redirect(url_for("builds_page"))
    expire_active_licenses(conn)

    configs = conn.execute("""
        SELECT bc.*, l.license_key, l.status as license_status
        FROM build_configs bc
        LEFT JOIN licenses l ON bc.license_id = l.id
    """).fetchall()

    if not configs:
        conn.close()
        flash("No build configs found. Create at least one first.", "error")
        return redirect(url_for("builds_page"))

    now = time.time()
    cursor = conn.execute(
        "INSERT INTO builds (version, status, total_configs, created_at) VALUES (?, 'pending', ?, ?)",
        (version, len(configs), now)
    )
    build_id = cursor.lastrowid

    already_built = set()
    existing = conn.execute("""
        SELECT ba.build_config_id FROM build_artifacts ba
        JOIN builds b ON ba.build_id = b.id
        WHERE b.version = ? AND ba.status = 'completed'
    """, (version,)).fetchall()
    for row in existing:
        already_built.add(row["build_config_id"])

    config_list = []
    skipped = 0
    skipped_expired = 0
    for c in configs:
        if c["license_status"] not in ('active', None):
            skipped_expired += 1
            continue
        if c["id"] in already_built:
            skipped += 1
            continue
        embedded_key = c["embedded_key"] or c["license_key"] or ""
        conn.execute(
            "INSERT INTO build_artifacts (build_id, build_config_id, license_id, status) VALUES (?, ?, ?, 'pending')",
            (build_id, c["id"], c["license_id"])
        )
        config_list.append({
            "id": c["id"], "app_name": c["app_name"],
            "hardcoded_path": c["hardcoded_path"],
            "license_server_url": c["license_server_url"],
            "license_secret": c["license_secret"],
            "icon_filename": c["icon_filename"],
            "embedded_key": embedded_key,
        })

    if not config_list:
        conn.execute("DELETE FROM builds WHERE id=?", (build_id,))
        conn.commit()
        conn.close()
        parts = []
        if skipped > 0:
            parts.append(f"{skipped} already built")
        if skipped_expired > 0:
            parts.append(f"{skipped_expired} skipped (not active)")
        flash(f"Nothing to build for v{version}. {', '.join(parts)}.", "warning")
        return redirect(url_for("builds_page"))

    conn.execute("UPDATE builds SET total_configs=? WHERE id=?", (len(config_list), build_id))
    conn.commit()
    conn.close()

    with _build_lock:
        _build_progress[build_id] = {
            "status": "pending", "version": version,
            "total": len(config_list), "completed": 0,
            "artifacts": {}, "error": "",
        }

    thread = threading.Thread(target=_run_build_all, args=(build_id, version, config_list), daemon=True)
    thread.start()

    skip_parts = []
    if skipped > 0:
        skip_parts.append(f"{skipped} already built")
    if skipped_expired > 0:
        skip_parts.append(f"{skipped_expired} skipped (not active)")
    skip_msg = f" ({', '.join(skip_parts)})" if skip_parts else ""
    flash(f"Build v{version} started for {len(config_list)} config(s){skip_msg}", "success")
    return redirect(url_for("builds_page"))


@app.route("/api/build_status/<int:build_id>")
@require_admin
def api_build_status(build_id):
    with _build_lock:
        progress = _build_progress.get(build_id)

    if progress:
        return jsonify(progress)

    conn = get_db()
    build = conn.execute("SELECT * FROM builds WHERE id = ?", (build_id,)).fetchone()
    if not build:
        conn.close()
        return jsonify({"error": "Build not found"}), 404

    artifacts = conn.execute(
        "SELECT ba.*, bc.app_name FROM build_artifacts ba JOIN build_configs bc ON ba.build_config_id = bc.id WHERE ba.build_id = ?",
        (build_id,)
    ).fetchall()
    conn.close()

    art_dict = {}
    for a in artifacts:
        art_dict[a["build_config_id"]] = {
            "status": a["status"], "progress": a["progress"],
            "name": a["app_name"], "filename": a["exe_filename"] or "",
            "size": a["file_size"] or 0, "error": a["error_message"] or "",
        }

    return jsonify({
        "status": build["status"], "version": build["version"],
        "total": build["total_configs"], "completed": build["completed_configs"],
        "artifacts": art_dict, "error": build["error_message"] or "",
    })


@app.route("/api/build_status_all")
@require_admin
def api_build_status_all():
    conn = get_db()
    active = conn.execute("SELECT id FROM builds WHERE status IN ('pending', 'building') ORDER BY created_at DESC LIMIT 1").fetchone()
    conn.close()
    if not active:
        return jsonify({"active_build": None})
    with _build_lock:
        progress = _build_progress.get(active["id"])
    if progress:
        return jsonify({"active_build": active["id"], "progress": progress})
    return jsonify({"active_build": active["id"]})


@app.route("/api/update_check", methods=["POST"])
@require_signed_request
def api_update_check():
    data = request.get_json(silent=True)
    if not data or "key" not in data or "version" not in data:
        resp = {"update_available": False, "error": "Missing key or version"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    key = data["key"].strip()
    current_version = data["version"].strip()

    conn = get_db()
    license_row = conn.execute("SELECT id FROM licenses WHERE license_key = ? AND status IN ('active', 'pending')", (key,)).fetchone()
    if not license_row:
        conn.close()
        resp = {"update_available": False, "error": "License not found or inactive"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    client_app_name = (data.get("app_name") or "").strip()
    try:
        client_config_id = int(data.get("config_id") or 0)
    except (TypeError, ValueError):
        client_config_id = 0

    client_config_hash_in = (data.get("config_hash") or "").strip()

    config = None
    if client_config_id:
        config = conn.execute("SELECT id, app_name FROM build_configs WHERE id = ?", (client_config_id,)).fetchone()
    if not config and client_config_hash_in:
        row = conn.execute(
            "SELECT bc.id AS id, bc.app_name AS app_name "
            "FROM build_artifacts ba JOIN build_configs bc ON ba.build_config_id = bc.id "
            "WHERE ba.config_hash = ? ORDER BY ba.id DESC LIMIT 1",
            (client_config_hash_in,)
        ).fetchone()
        if row:
            config = row
    if not config:
        config = conn.execute("SELECT id, app_name FROM build_configs WHERE license_id = ?", (license_row["id"],)).fetchone()
    if not config:
        config = conn.execute("SELECT id, app_name FROM build_configs WHERE embedded_key = ?", (key,)).fetchone()
    if not config and client_app_name:
        config = conn.execute("SELECT id, app_name FROM build_configs WHERE app_name = ? COLLATE NOCASE ORDER BY created_at DESC LIMIT 1", (client_app_name,)).fetchone()
    if not config and client_app_name:
        row = conn.execute(
            "SELECT bc.id AS id, bc.app_name AS app_name "
            "FROM build_artifacts ba JOIN build_configs bc ON ba.build_config_id = bc.id "
            "WHERE ba.app_name_snapshot = ? COLLATE NOCASE ORDER BY ba.id DESC LIMIT 1",
            (client_app_name,)
        ).fetchone()
        if row:
            config = row
    if not config:
        conn.close()
        msg = f"NO_MATCH key={key[:8]}... app='{client_app_name}' cid={client_config_id} hash={client_config_hash_in[:16]}"
        print(f"[OTA] {msg}")
        _record_ota({"ts": time.time(), "result": "no_match", "key": key[:8]+"...", "app_name": client_app_name, "config_id": client_config_id, "config_hash": client_config_hash_in[:16], "current_version": current_version, "msg": msg})
        resp = {"update_available": False}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    artifact = conn.execute("""
        SELECT ba.exe_filename, ba.file_size, ba.config_hash, b.version
        FROM build_artifacts ba
        JOIN builds b ON ba.build_id = b.id
        WHERE ba.build_config_id = ? AND ba.status = 'completed' AND b.status = 'completed'
        ORDER BY b.created_at DESC LIMIT 1
    """, (config["id"],)).fetchone()
    conn.close()

    if not artifact:
        print(f"[OTA] NO_ARTIFACT cfg#{config['id']} '{config['app_name']}'")
        resp = {"update_available": False}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    latest_version = artifact["version"]
    client_config_hash = (data.get("config_hash") or "").strip()
    server_config_hash = artifact["config_hash"] or ""

    version_newer = _version_compare(latest_version, current_version) > 0
    config_changed = False
    if server_config_hash:
        if not client_config_hash:
            config_changed = True
        elif server_config_hash != client_config_hash:
            config_changed = True

    decision = "UPDATE" if (version_newer or config_changed) else "NO_UPDATE"
    msg = f"cfg#{config['id']} '{config['app_name']}' client_v={current_version} latest_v={latest_version} client_hash={client_config_hash[:16]} server_hash={server_config_hash[:16]} ver_newer={version_newer} cfg_changed={config_changed} -> {decision}"
    print(f"[OTA] {msg}")
    _record_ota({"ts": time.time(), "result": decision.lower(), "key": key[:8]+"...", "app_name": client_app_name, "matched_config_id": config["id"], "matched_app_name": config["app_name"], "client_config_id": client_config_id, "current_version": current_version, "latest_version": latest_version, "client_hash": client_config_hash[:16], "server_hash": server_config_hash[:16], "ver_newer": version_newer, "cfg_changed": config_changed, "msg": msg})

    if not version_newer and not config_changed:
        resp = {"update_available": False, "latest_version": latest_version, "config_hash": server_config_hash}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    file_path = os.path.join(BUILDS_DIR, latest_version, str(config["id"]), artifact["exe_filename"])
    file_hash = ""
    if os.path.isfile(file_path):
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        file_hash = h.hexdigest()

    token = secrets.token_urlsafe(32)
    with _build_lock:
        _download_tokens[token] = {
            "config_id": config["id"], "version": latest_version,
            "expires": time.time() + 600, "license_key": key,
        }

    echo_app_name = client_app_name or (config["app_name"] if config else "")
    resp = {
        "update_available": True, "latest_version": latest_version,
        "file_size": artifact["file_size"],
        "download_token": token,
        "sha256": file_hash,
        "app_name": echo_app_name,
        "new_app_name": (config["app_name"] if config else ""),
        "config_hash": server_config_hash,
    }
    return jsonify({"data": resp, "signature": sign_response(resp)})


def _version_compare(v1, v2):
    try:
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]
        for a, b in zip(parts1, parts2):
            if a > b:
                return 1
            if a < b:
                return -1
        return len(parts1) - len(parts2)
    except Exception:
        return 0


@app.route("/api/download_update/<token>")
def api_download_update(token):
    with _build_lock:
        now = time.time()
        expired = [t for t, v in _download_tokens.items() if v["expires"] < now]
        for t in expired:
            del _download_tokens[t]
        token_data = _download_tokens.pop(token, None)

    if not token_data:
        return jsonify({"error": "Invalid or expired download token"}), 403

    config_id = token_data["config_id"]
    version = token_data["version"]

    conn = get_db()
    artifact = conn.execute("""
        SELECT ba.exe_filename FROM build_artifacts ba
        JOIN builds b ON ba.build_id = b.id
        WHERE ba.build_config_id = ? AND b.version = ? AND ba.status = 'completed'
        ORDER BY b.created_at DESC LIMIT 1
    """, (config_id, version)).fetchone()
    conn.close()

    if not artifact:
        return jsonify({"error": "Build artifact not found"}), 404

    file_path = os.path.join(BUILDS_DIR, version, str(config_id), artifact["exe_filename"])
    if not os.path.isfile(file_path):
        return jsonify({"error": "Build file missing from disk"}), 404

    return send_file(file_path, as_attachment=True, download_name=artifact["exe_filename"])


@app.route("/api/download_artifact/<int:build_id>/<int:config_id>")
def api_download_artifact(build_id, config_id):
    conn = get_db()
    artifact = conn.execute("""
        SELECT ba.exe_filename, b.version FROM build_artifacts ba
        JOIN builds b ON ba.build_id = b.id
        WHERE ba.build_id = ? AND ba.build_config_id = ? AND ba.status = 'completed'
    """, (build_id, config_id)).fetchone()
    conn.close()

    if not artifact:
        return "Artifact not found", 404

    file_path = os.path.join(BUILDS_DIR, artifact["version"], str(config_id), artifact["exe_filename"])
    if not os.path.isfile(file_path):
        return "Build file missing from disk", 404

    return send_file(file_path, as_attachment=True, download_name=artifact["exe_filename"])


@app.route("/api/report_download_progress", methods=["POST"])
@require_signed_request
def api_report_download_progress():
    data = request.get_json(silent=True) or {}
    key = (data.get("license_key") or "").strip()
    progress = data.get("progress", 0)
    version = (data.get("version") or "").strip()
    status = (data.get("status") or "downloading").strip()
    client_app_name = (data.get("app_name") or "").strip()

    if not key:
        return jsonify({"error": "Missing license_key"}), 400

    conn = get_db()
    lic = conn.execute("SELECT id FROM licenses WHERE license_key = ?", (key,)).fetchone()
    conn.close()
    if not lic:
        return jsonify({"error": "Unknown key"}), 404

    with _build_lock:
        _download_progress[key] = {
            "progress": min(100, max(0, int(progress))),
            "version": version,
            "status": status,
            "updated_at": time.time(),
            "app_name": client_app_name,
        }

    try:
        socketio.emit('download_progress', {
            'license_key': key,
            'progress': min(100, max(0, int(progress))),
            'version': version,
            'status': status,
        }, namespace='/')
    except Exception:
        pass

    return jsonify({"ok": True})


@app.route("/api/ota_status")
@require_admin
def api_ota_status():
    conn = get_db()

    latest_version = conn.execute("""
        SELECT version FROM builds WHERE status='completed' ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    latest_ver = latest_version["version"] if latest_version else None

    configs = conn.execute("SELECT id, app_name, license_id, embedded_key FROM build_configs ORDER BY created_at DESC").fetchall()
    app_name_map = {}
    for c in configs:
        app_name_map[c["id"]] = c["app_name"]

    licenses = conn.execute("""
        SELECT id, license_key, launcher_version, status, note
        FROM licenses WHERE status IN ('active', 'pending', 'suspended')
    """).fetchall()

    seen_keys = set()
    result = []
    now = time.time()

    for lic in licenses:
        key = lic["license_key"] or ""
        if key in seen_keys:
            continue
        seen_keys.add(key)

        launcher_ver = lic["launcher_version"] or ""

        config_match = None
        for c in configs:
            if c["license_id"] and c["license_id"] == lic["id"]:
                config_match = c
                break
        if not config_match:
            for c in configs:
                if c["embedded_key"] and c["embedded_key"] == key:
                    config_match = c
                    break
        if not config_match:
            dl_app_name = _download_progress.get(key, {}).get("app_name", "")
            match_name = dl_app_name or (lic["note"] or "")
            if match_name:
                match_lower = match_name.strip().lower()
                for c in configs:
                    if c["app_name"] and c["app_name"].strip().lower() == match_lower:
                        config_match = c
                        break
        if not config_match and len(configs) == 1:
            config_match = configs[0]

        app_name = app_name_map.get(config_match["id"], "Unknown") if config_match else (lic["note"] or key[:12])

        dl_info = _download_progress.get(key, {})
        dl_age = now - dl_info.get("updated_at", 0) if dl_info else 999999

        if launcher_ver and latest_ver and launcher_ver == latest_ver:
            ota_state = "updated"
        elif dl_info and dl_info.get("status") == "downloading" and dl_age < 300:
            ota_state = "downloading"
        elif latest_ver and (not launcher_ver or launcher_ver != latest_ver):
            ota_state = "outdated"
        else:
            ota_state = "unknown"

        result.append({
            "config_id": config_match["id"] if config_match else None,
            "app_name": app_name,
            "license_key": key[:8] + "..." if key else "",
            "current_version": launcher_ver or "—",
            "latest_version": latest_ver or "—",
            "ota_state": ota_state,
            "download_progress": dl_info.get("progress", 0) if ota_state == "downloading" else None,
        })

    conn.close()
    return jsonify({"users": result, "latest_version": latest_ver})


@app.route("/backups")
@require_admin
def backups_page():
    settings = telegram_backup.public_view(telegram_backup.load_settings())
    return render_template("backups.html", settings=settings)


def _wants_json():
    if request.headers.get("X-Requested-With", "").lower() == "xmlhttprequest":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


@app.route("/backups/save", methods=["POST"])
@require_admin
def backups_save():
    settings = telegram_backup.load_settings()
    chat_id = (request.form.get("chat_id") or "").strip()
    caption_prefix = (request.form.get("caption_prefix") or "").strip()
    bot_token_input = (request.form.get("bot_token") or "").strip()
    if bot_token_input:
        settings["bot_token"] = bot_token_input
    settings["chat_id"] = chat_id
    settings["caption_prefix"] = caption_prefix[:200]

    sched_type = (request.form.get("schedule_type") or "off").strip()
    if sched_type not in ("off", "interval", "daily", "weekly"):
        sched_type = "off"
    try:
        interval_hours = max(1, min(720, int(request.form.get("interval_hours") or 24)))
    except ValueError:
        interval_hours = 24
    daily_time = (request.form.get("daily_time") or "03:00").strip()
    weekly_time = (request.form.get("weekly_time") or "03:00").strip()
    try:
        weekly_day = max(0, min(6, int(request.form.get("weekly_day") or 0)))
    except ValueError:
        weekly_day = 0
    def _valid_hhmm(s):
        m = re.match(r"^(\d{1,2}):(\d{2})$", s or "")
        if not m:
            return False
        h, mi = int(m.group(1)), int(m.group(2))
        return 0 <= h <= 23 and 0 <= mi <= 59
    if not _valid_hhmm(daily_time):
        daily_time = "03:00"
    if not _valid_hhmm(weekly_time):
        weekly_time = "03:00"

    prev_type = (settings.get("schedule") or {}).get("type", "off")
    settings["schedule"] = {
        "type": sched_type,
        "interval_hours": interval_hours,
        "daily_time": daily_time,
        "weekly_day": weekly_day,
        "weekly_time": weekly_time,
    }
    # Arm the interval clock when switching INTO interval mode so the next
    # run fires interval_hours from now (not immediately, not never).
    if sched_type == "interval" and prev_type != "interval":
        settings["last_run_at"] = time.time()
    telegram_backup.save_settings(settings)

    if _wants_json():
        return jsonify({"success": True, "settings": telegram_backup.public_view(settings)})
    flash("Backup settings saved", "success")
    return redirect(url_for("backups_page"))


@app.route("/backups/test", methods=["POST"])
@require_admin
def backups_test():
    settings = telegram_backup.load_settings()
    token = settings.get("bot_token", "")
    chat_id = settings.get("chat_id", "")
    text = (request.form.get("text") or "DPRS backup test message").strip()
    success, message = telegram_backup.send_message(token, chat_id, text)
    if _wants_json():
        return jsonify({"success": success, "message": message})
    flash(message, "success" if success else "error")
    return redirect(url_for("backups_page"))


@app.route("/backups/run-now", methods=["POST"])
@require_admin
def backups_run_now():
    success, message = telegram_backup.run_backup(DB_PATH, run_type="manual")
    if _wants_json():
        settings = telegram_backup.public_view(telegram_backup.load_settings())
        return jsonify({"success": success, "message": message, "settings": settings})
    flash(message, "success" if success else "error")
    return redirect(url_for("backups_page"))


@app.route("/api/backups/status")
@require_admin
def backups_status():
    return jsonify(telegram_backup.public_view(telegram_backup.load_settings()))


init_db()
telegram_backup.start_scheduler(DB_PATH)


if __name__ == "__main__":
    port = int(os.environ.get("LICENSE_PORT", os.environ.get("PORT", 3842)))
    if ADMIN_PASSWORD == "admin":
        print("WARNING: Using default admin password. Set LICENSE_ADMIN_PASSWORD env var for production!")
    print(f"License server starting on port {port}")
    print(f"Dashboard: http://0.0.0.0:{port}/")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
