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

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "licenses.db")
SHARED_SECRET = os.environ.get("LICENSE_SHARED_SECRET", "DENFI_LICENSE_SECRET_KEY_2024")
ADMIN_PASSWORD = os.environ.get("LICENSE_ADMIN_PASSWORD", "admin")
HEARTBEAT_TIMEOUT = 300
REQUEST_TIMESTAMP_TOLERANCE = 300
_used_nonces = set()
_nonce_cleanup_time = 0

BUILDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "builds")
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_icons")
SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_build_progress = {}
_build_lock = threading.Lock()
_download_tokens = {}
_download_progress = {}

socketio = SocketIO(app, async_mode='threading')


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
            started_at REAL,
            completed_at REAL,
            FOREIGN KEY (build_id) REFERENCES builds(id),
            FOREIGN KEY (build_config_id) REFERENCES build_configs(id)
        );
    """)
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
        client_ip = request.remote_addr
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
        remaining = row["expires_at"] - now

        if remaining <= 0:
            conn.execute("UPDATE licenses SET status = 'expired' WHERE id = ?", (row["id"],))
            conn.commit()
            conn.close()
            resp = {"valid": False, "error": "License has expired"}
            return jsonify({"data": resp, "signature": sign_response(resp)})

        client_ip = request.remote_addr
        if row["registered_ip"] and client_ip != row["registered_ip"]:
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
    remaining = row["expires_at"] - now

    if remaining <= 0:
        conn.execute("UPDATE licenses SET status = 'expired' WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        resp = {"valid": False, "error": "License has expired"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    client_ip = request.remote_addr
    if row["registered_ip"] and client_ip != row["registered_ip"]:
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
    for row in rows:
        if row["status"] == "active":
            remaining = row["expires_at"] - now
            remaining_text = format_duration(remaining)
            remaining_seconds = int(remaining)
        elif row["status"] == "suspended" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
            remaining_text = format_duration(remaining) + " (suspended)"
            remaining_seconds = int(remaining)
        else:
            remaining_text = format_duration(row["duration_seconds"])
            remaining_seconds = row["duration_seconds"]

        licenses.append({
            "id": row["id"],
            "key": row["license_key"],
            "created": format_time(row["created_at"]),
            "activated": format_time(row["activated_at"]),
            "remaining": remaining_text,
            "remaining_seconds": remaining_seconds,
            "online": is_online(row["last_heartbeat"]),
            "last_heartbeat": format_time(row["last_heartbeat"]),
            "last_ip": row["last_ip"] or "N/A",
            "registered_ip": row["registered_ip"] or "N/A",
            "note": row["note"] or "",
            "status": row["status"],
            "version": row["launcher_version"] or "",
        })

    return render_template("dashboard.html", licenses=licenses)


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

        flash(f"License created: {key}", "success")
        return redirect(url_for("dashboard"))

    return render_template("create.html")


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
    for row in rows:
        if row["status"] == "active":
            remaining = row["expires_at"] - now
            remaining_text = format_duration(remaining)
            remaining_seconds = int(remaining)
        elif row["status"] == "suspended" and row["expires_at"]:
            remaining = max(0, row["expires_at"] - now)
            remaining_text = format_duration(remaining) + " (suspended)"
            remaining_seconds = int(remaining)
        else:
            remaining_text = format_duration(row["duration_seconds"])
            remaining_seconds = row["duration_seconds"]

        licenses.append({
            "id": row["id"],
            "key": row["license_key"],
            "created": format_time(row["created_at"]),
            "activated": format_time(row["activated_at"]),
            "remaining": remaining_text,
            "remaining_seconds": remaining_seconds,
            "online": is_online(row["last_heartbeat"]),
            "last_heartbeat": format_time(row["last_heartbeat"]),
            "last_ip": row["last_ip"] or "N/A",
            "registered_ip": row["registered_ip"] or "N/A",
            "note": row["note"] or "",
            "status": row["status"],
            "version": row["launcher_version"] or "",
        })

    return jsonify({"licenses": licenses})


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
    return source


def _run_single_build(build_id, config, version):
    config_id = config["id"]
    exe_name = _sanitize_exe_name(config.get("app_name", "DenfiRoblox"))
    output_dir = os.path.join(BUILDS_DIR, version, str(config_id))
    os.makedirs(output_dir, exist_ok=True)
    work_dir = os.path.join(BUILDS_DIR, "_work", f"{build_id}_{config_id}")
    os.makedirs(work_dir, exist_ok=True)

    try:
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
                shutil.copy2(src_icon, dst_icon)
                icon_path = dst_icon

        splash_src = os.path.join(SOURCE_DIR, "splash_logo.png")
        if os.path.isfile(splash_src):
            shutil.copy2(splash_src, os.path.join(work_dir, "splash_logo.png"))

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
        splash_work = os.path.join(work_dir, "splash_logo.png")
        if os.path.isfile(splash_work):
            cmd.extend(["--add-data", f"{splash_work}{os.pathsep}."])
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
        conn = get_db()
        conn.execute(
            "UPDATE build_artifacts SET status='completed', progress=100, exe_filename=?, file_size=?, completed_at=? WHERE build_id=? AND build_config_id=?",
            (os.path.basename(exe_path), file_size, time.time(), build_id, config_id)
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
    conn = get_db()
    conn.execute("UPDATE builds SET status='building', started_at=? WHERE id=?", (time.time(), build_id))
    conn.commit()
    conn.close()

    completed = 0
    failed = 0
    for config in configs:
        success = _run_single_build(build_id, config, version)
        if success:
            completed += 1
        else:
            failed += 1
        conn = get_db()
        conn.execute("UPDATE builds SET completed_configs=? WHERE id=?", (completed + failed, build_id))
        conn.commit()
        conn.close()
        with _build_lock:
            if build_id in _build_progress:
                _build_progress[build_id]["completed"] = completed + failed

    final_status = "completed" if failed == 0 else ("failed" if completed == 0 else "completed")
    error_msg = f"{failed} config(s) failed" if failed > 0 else ""
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
    past_builds = conn.execute("SELECT * FROM builds ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()

    build_list = []
    for b in past_builds:
        build_list.append({
            "id": b["id"], "version": b["version"], "status": b["status"],
            "total": b["total_configs"], "completed": b["completed_configs"],
            "started": format_time(b["started_at"]), "finished": format_time(b["completed_at"]),
            "error": b["error_message"] or "",
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
            elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.webp'):
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
            elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.webp'):
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
    }
    return render_template("build_config_form.html", config=config_dict, licenses=licenses)


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
    conn.execute("DELETE FROM build_configs WHERE id = ?", (config_id,))
    conn.commit()
    conn.close()
    flash("Build config deleted", "success")
    return redirect(url_for("builds_page"))


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
    configs = conn.execute("""
        SELECT bc.*, l.license_key
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

    config_list = []
    for c in configs:
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

    flash(f"Build v{version} started for {len(config_list)} config(s)", "success")
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

    config = conn.execute("SELECT id FROM build_configs WHERE license_id = ?", (license_row["id"],)).fetchone()
    if not config:
        conn.close()
        resp = {"update_available": False}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    artifact = conn.execute("""
        SELECT ba.exe_filename, ba.file_size, b.version
        FROM build_artifacts ba
        JOIN builds b ON ba.build_id = b.id
        WHERE ba.build_config_id = ? AND ba.status = 'completed' AND b.status = 'completed'
        ORDER BY b.created_at DESC LIMIT 1
    """, (config["id"],)).fetchone()
    conn.close()

    if not artifact:
        resp = {"update_available": False}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    latest_version = artifact["version"]
    if _version_compare(latest_version, current_version) <= 0:
        resp = {"update_available": False, "latest_version": latest_version}
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

    resp = {
        "update_available": True, "latest_version": latest_version,
        "file_size": artifact["file_size"],
        "download_token": token,
        "sha256": file_hash,
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
@require_admin
def api_download_artifact(build_id, config_id):
    conn = get_db()
    artifact = conn.execute("""
        SELECT ba.exe_filename, b.version FROM build_artifacts ba
        JOIN builds b ON ba.build_id = b.id
        WHERE ba.build_id = ? AND ba.build_config_id = ? AND ba.status = 'completed'
    """, (build_id, config_id)).fetchone()
    conn.close()

    if not artifact:
        flash("Artifact not found", "error")
        return redirect(url_for("builds_page"))

    file_path = os.path.join(BUILDS_DIR, artifact["version"], str(config_id), artifact["exe_filename"])
    if not os.path.isfile(file_path):
        flash("Build file missing from disk", "error")
        return redirect(url_for("builds_page"))

    return send_file(file_path, as_attachment=True, download_name=artifact["exe_filename"])


@app.route("/api/report_download_progress", methods=["POST"])
@require_signed_request
def api_report_download_progress():
    data = request.get_json(silent=True) or {}
    key = (data.get("license_key") or "").strip()
    progress = data.get("progress", 0)
    version = (data.get("version") or "").strip()
    status = (data.get("status") or "downloading").strip()

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
    configs = conn.execute("""
        SELECT bc.id, bc.app_name, bc.license_id, l.license_key, l.launcher_version
        FROM build_configs bc LEFT JOIN licenses l ON bc.license_id = l.id
    """).fetchall()

    latest_version = conn.execute("""
        SELECT version FROM builds WHERE status='completed' ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    conn.close()

    latest_ver = latest_version["version"] if latest_version else None
    result = []
    now = time.time()
    for c in configs:
        key = c["license_key"] or ""
        dl_info = _download_progress.get(key, {})
        dl_age = now - dl_info.get("updated_at", 0) if dl_info else 999999

        if c["launcher_version"] and latest_ver and c["launcher_version"] == latest_ver:
            ota_state = "updated"
        elif dl_info and dl_info.get("status") == "downloading" and dl_age < 300:
            ota_state = "downloading"
        elif latest_ver and (not c["launcher_version"] or c["launcher_version"] != latest_ver):
            ota_state = "outdated"
        else:
            ota_state = "unknown"

        result.append({
            "config_id": c["id"],
            "app_name": c["app_name"],
            "license_key": key[:8] + "..." if key else "",
            "current_version": c["launcher_version"] or "—",
            "latest_version": latest_ver or "—",
            "ota_state": ota_state,
            "download_progress": dl_info.get("progress", 0) if ota_state == "downloading" else None,
        })

    return jsonify({"users": result, "latest_version": latest_ver})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("LICENSE_PORT", os.environ.get("PORT", 3842)))
    if ADMIN_PASSWORD == "admin":
        print("WARNING: Using default admin password. Set LICENSE_ADMIN_PASSWORD env var for production!")
    print(f"License server starting on port {port}")
    print(f"Dashboard: http://0.0.0.0:{port}/")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
