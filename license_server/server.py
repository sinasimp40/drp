import os
import sys
import uuid
import time
import hmac
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.urandom(32).hex()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "licenses.db")
SHARED_SECRET = "DENFI_LICENSE_SECRET_KEY_2024"
ADMIN_PASSWORD = os.environ.get("LICENSE_ADMIN_PASSWORD", "admin")
HEARTBEAT_TIMEOUT = 300


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
            expires_at REAL NOT NULL,
            duration_seconds INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            last_heartbeat REAL,
            last_ip TEXT,
            note TEXT DEFAULT ''
        );
    """)
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


@app.route("/api/validate", methods=["POST"])
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
        resp = {"valid": False, "error": "Invalid license key"}
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
        resp = {"valid": False, "error": "License expired"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    client_ip = request.remote_addr
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
        "expires_at": row["expires_at"],
        "key": key,
    }
    return jsonify({"data": resp, "signature": sign_response(resp)})


@app.route("/api/heartbeat", methods=["POST"])
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
        resp = {"valid": False, "error": "Invalid license key"}
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
        resp = {"valid": False, "error": "License expired"}
        return jsonify({"data": resp, "signature": sign_response(resp)})

    client_ip = request.remote_addr
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
        auth = request.cookies.get("admin_auth")
        if auth != hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest():
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            resp = redirect(url_for("dashboard"))
            resp.set_cookie(
                "admin_auth",
                hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
                max_age=86400
            )
            return resp
        flash("Invalid password", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    resp = redirect(url_for("login_page"))
    resp.delete_cookie("admin_auth")
    return resp


@app.route("/")
@require_admin
def dashboard():
    conn = get_db()
    now = time.time()

    conn.execute(
        "UPDATE licenses SET status = 'expired' WHERE status = 'active' AND expires_at <= ?",
        (now,)
    )
    conn.commit()

    rows = conn.execute(
        "SELECT * FROM licenses WHERE status = 'active' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    licenses = []
    for row in rows:
        remaining = row["expires_at"] - now
        licenses.append({
            "id": row["id"],
            "key": row["license_key"],
            "created": format_time(row["created_at"]),
            "remaining": format_duration(remaining),
            "remaining_seconds": int(remaining),
            "online": is_online(row["last_heartbeat"]),
            "last_heartbeat": format_time(row["last_heartbeat"]),
            "last_ip": row["last_ip"] or "N/A",
            "note": row["note"] or "",
            "status": row["status"],
        })

    return render_template("dashboard.html", licenses=licenses)


@app.route("/history")
@require_admin
def history():
    conn = get_db()
    now = time.time()

    conn.execute(
        "UPDATE licenses SET status = 'expired' WHERE status = 'active' AND expires_at <= ?",
        (now,)
    )
    conn.commit()

    rows = conn.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
    conn.close()

    licenses = []
    for row in rows:
        remaining = max(0, row["expires_at"] - now)
        licenses.append({
            "id": row["id"],
            "key": row["license_key"],
            "created": format_time(row["created_at"]),
            "expires": format_time(row["expires_at"]),
            "remaining": format_duration(remaining) if row["status"] == "active" else "-",
            "online": is_online(row["last_heartbeat"]) if row["status"] == "active" else False,
            "last_ip": row["last_ip"] or "N/A",
            "note": row["note"] or "",
            "status": row["status"],
            "duration_text": format_duration(row["duration_seconds"]),
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
            "INSERT INTO licenses (license_key, created_at, expires_at, duration_seconds, status, note) VALUES (?, ?, ?, ?, 'active', ?)",
            (key, now, now + duration_seconds, duration_seconds, note)
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


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("LICENSE_PORT", os.environ.get("PORT", 3842)))
    print(f"License server starting on port {port}")
    print(f"Admin password: {ADMIN_PASSWORD}")
    print(f"Dashboard: http://0.0.0.0:{port}/")
    app.run(host="0.0.0.0", port=port, debug=False)
