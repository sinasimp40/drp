"""Telegram backup of license.db.

Self-contained module: persistent JSON settings, stdlib-only Telegram
sender (Bot API), and a background scheduler thread that uploads the
licenses database on a configured schedule.
"""

import json
import os
import threading
import time
import uuid
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup_settings.json")
HISTORY_LIMIT = 10
HTTP_TIMEOUT = 60

_DEFAULTS = {
    "bot_token": "",
    "chat_id": "",
    "caption_prefix": "",
    "proxy_url": "",
    "schedule": {
        "type": "off",          # off | interval | daily | weekly
        "interval_hours": 24,
        "daily_time": "03:00",
        "weekly_day": 0,        # 0=Monday ... 6=Sunday
        "weekly_time": "03:00",
    },
    "last_run_at": 0.0,
    "history": [],
}

_lock = threading.RLock()


# ---------- Persistence ----------------------------------------------------

def _deep_merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings():
    with _lock:
        if not os.path.isfile(SETTINGS_FILE):
            return json.loads(json.dumps(_DEFAULTS))
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return json.loads(json.dumps(_DEFAULTS))
        return _deep_merge(_DEFAULTS, data)


def save_settings(settings):
    with _lock:
        tmp = SETTINGS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        os.replace(tmp, SETTINGS_FILE)


def public_view(settings):
    """Return a copy safe for templating: bot token is masked."""
    s = json.loads(json.dumps(settings))
    tok = s.get("bot_token") or ""
    if tok:
        if len(tok) > 8:
            s["bot_token_masked"] = tok[:4] + "•" * 6 + tok[-4:]
        else:
            s["bot_token_masked"] = "•" * len(tok)
        s["bot_token_set"] = True
    else:
        s["bot_token_masked"] = ""
        s["bot_token_set"] = False
    s["chat_id_set"] = bool(s.get("chat_id"))
    proxy = (s.get("proxy_url") or "").strip()
    s["proxy_set"] = bool(proxy)
    if proxy:
        s["proxy_url_masked"] = _mask_proxy(proxy)
    else:
        s["proxy_url_masked"] = ""
    s.pop("bot_token", None)
    s.pop("proxy_url", None)
    return s


def _mask_proxy(url):
    """Hide user:password if present in the proxy URL."""
    try:
        from urllib.parse import urlparse, urlunparse
        p = urlparse(url)
        if p.username or p.password:
            host = p.hostname or ""
            if p.port:
                host = f"{host}:{p.port}"
            netloc = f"***:***@{host}"
            return urlunparse((p.scheme, netloc, p.path, p.params, p.query, p.fragment))
        return url
    except Exception:
        return "(proxy configured)"


def append_history(settings, entry):
    history = list(settings.get("history") or [])
    history.insert(0, entry)
    settings["history"] = history[:HISTORY_LIMIT]


# ---------- Telegram sender ------------------------------------------------

def _api_url(token, method):
    return f"https://api.telegram.org/bot{token}/{method}"


def _build_opener(proxy_url):
    """Return a urllib opener configured for the given proxy.

    Supports schemes: http, https, socks5, socks5h, socks4, socks4a.
    SOCKS support requires the optional PySocks package.
    """
    proxy_url = (proxy_url or "").strip()
    if not proxy_url:
        return urllib.request.build_opener()

    scheme = proxy_url.split("://", 1)[0].lower() if "://" in proxy_url else ""

    if scheme.startswith("socks"):
        try:
            import socks  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "SOCKS proxy requires the 'PySocks' package: " + str(e)
            )
        import http.client
        import ssl as _ssl
        from urllib.parse import urlparse

        p = urlparse(proxy_url)
        stype = socks.SOCKS5 if scheme.startswith("socks5") else socks.SOCKS4
        rdns = scheme in ("socks5h", "socks4a")
        proxy_host = p.hostname
        proxy_port = p.port or 1080
        proxy_user = p.username
        proxy_pass = p.password

        class _SocksHTTPSConnection(http.client.HTTPSConnection):
            def connect(self):
                sock = socks.socksocket()
                sock.set_proxy(stype, proxy_host, proxy_port, rdns=rdns,
                               username=proxy_user, password=proxy_pass)
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                self.sock = self._context.wrap_socket(
                    sock, server_hostname=self.host)

        class _SocksHTTPSHandler(urllib.request.HTTPSHandler):
            def https_open(self, req):
                return self.do_open(_SocksHTTPSConnection, req,
                                    context=_ssl.create_default_context())

        return urllib.request.build_opener(_SocksHTTPSHandler())

    # HTTP / HTTPS proxy
    proxy_handler = urllib.request.ProxyHandler({
        "http": proxy_url,
        "https": proxy_url,
    })
    return urllib.request.build_opener(proxy_handler)


def send_message(token, chat_id, text, proxy_url=""):
    if not token or not chat_id:
        return False, "Bot token and chat ID are required"
    url = _api_url(token, "sendMessage")
    body = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        opener = _build_opener(proxy_url)
        with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            if payload.get("ok"):
                return True, "Message delivered"
            return False, f"Telegram error: {payload.get('description', 'unknown')}"
    except urllib.error.HTTPError as e:
        return False, _http_error_msg(e)
    except urllib.error.URLError as e:
        return False, f"Network error: {e.reason}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def _http_error_msg(err):
    try:
        body = err.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        desc = data.get("description") or body
    except Exception:
        desc = str(err)
    return f"HTTP {err.code}: {desc}"


def _build_multipart(fields, files):
    boundary = "----dprsBoundary" + uuid.uuid4().hex
    crlf = b"\r\n"
    parts = []
    for name, value in fields.items():
        parts.append(("--" + boundary).encode("utf-8"))
        parts.append(
            f'Content-Disposition: form-data; name="{name}"'.encode("utf-8")
        )
        parts.append(b"")
        parts.append(str(value).encode("utf-8"))
    for name, (filename, content, ctype) in files.items():
        parts.append(("--" + boundary).encode("utf-8"))
        parts.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode("utf-8")
        )
        parts.append(f"Content-Type: {ctype}".encode("utf-8"))
        parts.append(b"")
        parts.append(content)
    parts.append(("--" + boundary + "--").encode("utf-8"))
    parts.append(b"")
    body = crlf.join(parts)
    return boundary, body


def send_document(token, chat_id, file_path, caption="", proxy_url=""):
    if not token or not chat_id:
        return False, "Bot token and chat ID are required"
    if not os.path.isfile(file_path):
        return False, f"File not found: {file_path}"
    try:
        with open(file_path, "rb") as f:
            content = f.read()
    except Exception as e:
        return False, f"Failed to read file: {e}"

    filename = os.path.basename(file_path)
    fields = {"chat_id": chat_id}
    if caption:
        fields["caption"] = caption[:1024]
    files = {"document": (filename, content, "application/octet-stream")}
    boundary, body = _build_multipart(fields, files)

    url = _api_url(token, "sendDocument")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Content-Length", str(len(body)))
    try:
        opener = _build_opener(proxy_url)
        with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            if payload.get("ok"):
                size_kb = len(content) / 1024.0
                return True, f"Uploaded {filename} ({size_kb:.1f} KB)"
            return False, f"Telegram error: {payload.get('description', 'unknown')}"
    except urllib.error.HTTPError as e:
        return False, _http_error_msg(e)
    except urllib.error.URLError as e:
        return False, f"Network error: {e.reason}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


# ---------- Run + history --------------------------------------------------

def run_backup(db_path, run_type="manual"):
    """Send the database file once. Records the attempt in history.

    Returns (success, message).
    """
    with _lock:
        settings = load_settings()
        token = settings.get("bot_token", "")
        chat_id = settings.get("chat_id", "")
        prefix = (settings.get("caption_prefix") or "").strip()
        proxy_url = (settings.get("proxy_url") or "").strip()

    if not token or not chat_id:
        msg = "Bot token and chat ID must be configured"
        with _lock:
            s = load_settings()
            append_history(s, _entry(run_type, False, msg))
            save_settings(s)
        return False, msg

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    caption = f"{prefix + ' — ' if prefix else ''}{run_type} backup at {ts}"

    success, message = send_document(token, chat_id, db_path, caption=caption, proxy_url=proxy_url)
    if not success:
        # Single retry on failure
        time.sleep(2)
        success, retry_msg = send_document(token, chat_id, db_path, caption=caption, proxy_url=proxy_url)
        if success:
            message = retry_msg + " (after retry)"
        else:
            message = f"{message} | retry: {retry_msg}"

    with _lock:
        s = load_settings()
        append_history(s, _entry(run_type, success, message))
        if success:
            s["last_run_at"] = time.time()
        save_settings(s)
    return success, message


def _entry(run_type, success, message):
    return {
        "ts": time.time(),
        "ts_text": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": run_type,
        "status": "ok" if success else "error",
        "message": message,
    }


# ---------- Schedule decision ---------------------------------------------

def _today_hhmm_epoch(hhmm, now_dt):
    try:
        hh, mm = [int(x) for x in hhmm.split(":")]
    except Exception:
        return None
    target = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return target.timestamp()


def _is_due(settings, now):
    sched = settings.get("schedule") or {}
    stype = sched.get("type", "off")
    if stype == "off":
        return False
    last = float(settings.get("last_run_at") or 0)
    now_dt = datetime.fromtimestamp(now)

    if stype == "interval":
        try:
            hours = max(1, int(sched.get("interval_hours") or 0))
        except Exception:
            return False
        if last <= 0:
            return False  # arm without immediate fire on first save
        return (now - last) >= hours * 3600

    if stype == "daily":
        target = _today_hhmm_epoch(sched.get("daily_time") or "03:00", now_dt)
        if target is None or now < target:
            return False
        return last < target

    if stype == "weekly":
        try:
            wday = int(sched.get("weekly_day") or 0)
        except Exception:
            return False
        if now_dt.weekday() != wday:
            return False
        target = _today_hhmm_epoch(sched.get("weekly_time") or "03:00", now_dt)
        if target is None or now < target:
            return False
        return last < target

    return False


# ---------- Scheduler thread ----------------------------------------------

_started = False
_started_lock = threading.Lock()


def start_scheduler(db_path):
    """Start the background scheduler exactly once per process."""
    global _started
    with _started_lock:
        if _started:
            return
        _started = True

    def loop():
        # Arm interval scheduler so we don't fire immediately on a fresh
        # config that has never run; daily/weekly are time-of-day based and
        # safe.
        try:
            with _lock:
                s = load_settings()
                if (s.get("schedule") or {}).get("type") == "interval" and not s.get("last_run_at"):
                    s["last_run_at"] = time.time()
                    save_settings(s)
        except Exception as e:
            print(f"[telegram-backup] init error: {e}")

        while True:
            try:
                settings = load_settings()
                if _is_due(settings, time.time()):
                    print("[telegram-backup] schedule due, sending backup...")
                    ok, msg = run_backup(db_path, run_type="scheduled")
                    print(f"[telegram-backup] result: {'OK' if ok else 'FAIL'} - {msg}")
            except Exception as e:
                print(f"[telegram-backup] scheduler tick error: {e}")
            time.sleep(60)

    t = threading.Thread(target=loop, name="telegram-backup-scheduler", daemon=True)
    t.start()
    print("[telegram-backup] scheduler started")
