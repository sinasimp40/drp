"""Telegram backup of license.db.

Self-contained module: persistent JSON settings, stdlib-only Telegram
sender (Bot API), and a background scheduler thread that uploads the
licenses database on a configured schedule.

Supports a *list* of proxies tried in order with auto-eviction of dead
ones (network/SOCKS/connect/timeout/proxy-407/proxy-502 failures).
Telegram-side errors (401/413/429/etc.) never evict the proxy.
"""

import json
import os
import socket
import threading
import time
import uuid
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup_settings.json")
HISTORY_LIMIT = 10
HTTP_TIMEOUT = 60          # full read timeout once a connection is established
CONNECT_TIMEOUT = 8        # short timeout used during the initial handshake
MAX_PROXY_ATTEMPTS = 8     # cap proxies tried per backup so the scheduler can't hang
MAX_TOTAL_SECONDS = 120    # overall wall-clock cap per backup attempt
MAX_PROXY_LIST = 200       # hard cap on persisted list size

_DEFAULTS = {
    "bot_token": "",
    "chat_id": "",
    "caption_prefix": "",
    "proxy_url": "",                # legacy, migrated into proxy_list on load
    "proxy_list": [],               # ordered list of proxy URLs
    "try_direct_first": False,      # if True, try a direct connection before walking the list
    "schedule": {
        "type": "off",          # off | interval | daily | weekly
        "interval_hours": 24,
        "daily_time": "03:00",
        "weekly_day": 0,        # 0=Monday ... 6=Sunday
        "weekly_time": "03:00",
    },
    "last_run_at": 0.0,
    "last_used_proxy": "",          # masked URL of the proxy that worked last time
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


def _migrate(settings):
    """Move legacy single proxy_url into proxy_list[0] if not present."""
    legacy = (settings.get("proxy_url") or "").strip()
    proxy_list = settings.get("proxy_list")
    if not isinstance(proxy_list, list):
        proxy_list = []
    if legacy and legacy not in proxy_list:
        proxy_list.insert(0, legacy)
    settings["proxy_list"] = proxy_list
    settings["proxy_url"] = ""
    return settings


def load_settings():
    with _lock:
        if not os.path.isfile(SETTINGS_FILE):
            return _migrate(json.loads(json.dumps(_DEFAULTS)))
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return _migrate(json.loads(json.dumps(_DEFAULTS)))
        return _migrate(_deep_merge(_DEFAULTS, data))


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

    proxy_list = [p for p in (s.get("proxy_list") or []) if isinstance(p, str) and p.strip()]
    s["proxy_list"] = proxy_list
    s["proxy_list_text"] = "\n".join(proxy_list)
    s["proxy_list_masked"] = [_mask_proxy(p) for p in proxy_list]
    s["proxy_count"] = len(proxy_list)
    s["proxy_set"] = bool(proxy_list)
    s["try_direct_first"] = bool(s.get("try_direct_first"))
    s["last_used_proxy"] = s.get("last_used_proxy") or ""

    # Legacy compatibility for any template still referencing these:
    s["proxy_url_masked"] = s["proxy_list_masked"][0] if s["proxy_list_masked"] else ""

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


def _probe_proxy_reachable(proxy_url):
    """Cheap TCP connect to the proxy's host:port with CONNECT_TIMEOUT.

    Returns (ok, reason). Used before the heavy upload so that dead
    proxies are rejected within ~CONNECT_TIMEOUT seconds regardless of
    scheme — without this, urllib's HTTP/HTTPS proxy path would block
    for the full HTTP_TIMEOUT (60s) per dead proxy.
    """
    try:
        from urllib.parse import urlparse
        p = urlparse(proxy_url)
    except Exception as e:
        return False, f"invalid proxy URL: {e}"
    host = p.hostname
    if not host:
        return False, "missing host in proxy URL"
    scheme = (p.scheme or "").lower()
    if scheme in ("socks5", "socks5h"):
        port = p.port or 1080
    elif scheme in ("socks4", "socks4a"):
        port = p.port or 1080
    elif scheme == "https":
        port = p.port or 443
    else:
        port = p.port or 8080
    try:
        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT):
            return True, ""
    except socket.timeout:
        return False, f"connect timeout after {CONNECT_TIMEOUT}s"
    except OSError as e:
        return False, f"connect failed: {e}"


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
                # Use the short connect timeout for the SOCKS handshake +
                # destination connect, then raise it for the upload itself.
                sock.settimeout(CONNECT_TIMEOUT)
                sock.connect((self.host, self.port))
                sock.settimeout(self.timeout)
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


# ---------- Failure classification ----------------------------------------

# Outcomes returned by _attempt_*:
#   "success"        — proxy + Telegram both happy
#   "telegram_error" — request reached Telegram which returned a real API error
#                      (401/413/429/etc.) — DO NOT evict the proxy
#   "evict_proxy"    — network / SOCKS / connect / timeout / proxy-407 / 502 etc.
#   "bad_input"      — token / chat id missing
#
# Each returns: (outcome, message)


def _classify_http_error(err):
    """An HTTPError can be from Telegram OR from an upstream proxy.

    Treat as Telegram error only if the body parses as Telegram's
    {ok:false, description:...} envelope. Otherwise assume proxy.
    """
    code = getattr(err, "code", 0) or 0
    try:
        body = err.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    desc = ""
    looks_like_telegram = False
    try:
        data = json.loads(body) if body else None
        if isinstance(data, dict) and "ok" in data:
            looks_like_telegram = True
            desc = data.get("description") or body
    except Exception:
        pass
    if not desc:
        desc = body[:200] if body else str(err)

    if looks_like_telegram:
        return "telegram_error", f"HTTP {code}: {desc}"

    # Proxy-side codes we definitely treat as dead proxy.
    if code in (407, 502, 503, 504):
        return "evict_proxy", f"proxy HTTP {code}"
    # Anything else without a Telegram envelope is suspicious — assume proxy.
    return "evict_proxy", f"HTTP {code} (non-Telegram response)"


def _classify_url_error(err):
    reason = getattr(err, "reason", err)
    text = str(reason).lower()
    # All of these strongly suggest the proxy / network path is dead.
    return "evict_proxy", f"network: {reason}"


def _classify_exception(e):
    name = type(e).__name__
    text = str(e).lower()
    # PySocks raises socks.ProxyError / GeneralProxyError / ConnectionError
    if "socks" in name.lower() or "proxy" in text or "socks" in text:
        return "evict_proxy", f"SOCKS handshake failed: {e}"
    if isinstance(e, (socket.timeout, TimeoutError)):
        return "evict_proxy", "timeout"
    if isinstance(e, ConnectionError):
        return "evict_proxy", f"connection: {e}"
    return "evict_proxy", f"{name}: {e}"


# ---------- Single-attempt senders (no list logic) ------------------------

def _attempt_send_message(token, chat_id, text, proxy_url):
    if not token or not chat_id:
        return "bad_input", "Bot token and chat ID are required"
    if proxy_url:
        ok, why = _probe_proxy_reachable(proxy_url)
        if not ok:
            return "evict_proxy", why
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
                return "success", "Message delivered"
            return "telegram_error", f"Telegram error: {payload.get('description', 'unknown')}"
    except urllib.error.HTTPError as e:
        return _classify_http_error(e)
    except urllib.error.URLError as e:
        return _classify_url_error(e)
    except Exception as e:
        return _classify_exception(e)


def _attempt_send_document(token, chat_id, file_path, caption, proxy_url):
    if not token or not chat_id:
        return "bad_input", "Bot token and chat ID are required"
    if not os.path.isfile(file_path):
        return "bad_input", f"File not found: {file_path}"
    if proxy_url:
        ok, why = _probe_proxy_reachable(proxy_url)
        if not ok:
            return "evict_proxy", why
    try:
        with open(file_path, "rb") as f:
            content = f.read()
    except Exception as e:
        return "bad_input", f"Failed to read file: {e}"

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
                return "success", f"Uploaded {filename} ({size_kb:.1f} KB)"
            return "telegram_error", f"Telegram error: {payload.get('description', 'unknown')}"
    except urllib.error.HTTPError as e:
        return _classify_http_error(e)
    except urllib.error.URLError as e:
        return _classify_url_error(e)
    except Exception as e:
        return _classify_exception(e)


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


# ---------- List-walking driver -------------------------------------------

def _walk_proxies(settings, attempt_fn):
    """Try direct (optional) then each proxy in the list until one works.

    `attempt_fn(proxy_url)` must return (outcome, message).

    Mutates settings["proxy_list"] and settings["last_used_proxy"] in place
    based on the outcomes. Returns a dict:
        {
            "success": bool,
            "message": str,                # human-readable summary
            "used_proxy": str,             # masked URL, "" for direct
            "evictions": [ {proxy, reason}, ... ],
        }
    The caller is responsible for save_settings() under the same lock.
    """
    proxy_list = list(settings.get("proxy_list") or [])
    try_direct = bool(settings.get("try_direct_first"))

    candidates = []
    if try_direct:
        candidates.append(("", True))   # (url, is_direct)
    for p in proxy_list:
        candidates.append((p, False))

    if not candidates:
        return {
            "success": False,
            "message": "No proxies configured and direct connection is disabled.",
            "used_proxy": "",
            "evictions": [],
        }

    evictions = []           # [{proxy, reason}]
    last_msg = ""
    last_outcome = ""
    started = time.time()
    proxy_attempts = 0
    new_list = list(proxy_list)

    for url, is_direct in candidates:
        if not is_direct:
            if proxy_attempts >= MAX_PROXY_ATTEMPTS:
                last_msg = f"stopped after {proxy_attempts} proxy attempts (cap reached)"
                break
            if (time.time() - started) >= MAX_TOTAL_SECONDS:
                last_msg = f"stopped after {int(time.time() - started)}s wall-clock cap"
                break
            proxy_attempts += 1

        outcome, msg = attempt_fn(url)
        last_outcome, last_msg = outcome, msg

        if outcome == "success":
            used = "direct" if is_direct else _mask_proxy(url)
            settings["proxy_list"] = new_list
            settings["last_used_proxy"] = used
            return {
                "success": True,
                "message": f"{msg} via {used}" if not is_direct else f"{msg} via direct",
                "used_proxy": used,
                "evictions": evictions,
            }

        if outcome == "telegram_error" or outcome == "bad_input":
            # Proxy worked, Telegram (or our config) is the problem — stop.
            settings["proxy_list"] = new_list
            return {
                "success": False,
                "message": msg,
                "used_proxy": "direct" if is_direct else _mask_proxy(url),
                "evictions": evictions,
            }

        # outcome == "evict_proxy"
        if not is_direct:
            evictions.append({"proxy": _mask_proxy(url), "reason": msg})
            try:
                new_list.remove(url)
            except ValueError:
                pass

    # Exhausted all candidates without success.
    settings["proxy_list"] = new_list
    parts = [f"all {len(candidates)} attempt(s) failed"]
    if evictions:
        parts.append(f"{len(evictions)} proxy(ies) removed")
    if last_msg:
        parts.append(f"last error: {last_msg}")
    return {
        "success": False,
        "message": "; ".join(parts),
        "used_proxy": "",
        "evictions": evictions,
    }


# ---------- Public entrypoints --------------------------------------------

def send_message(token, chat_id, text, proxy_url=""):
    """Backwards-compatible single-attempt sender (no list walking).

    Used by callers that want to test one specific proxy without touching
    the saved list. Returns (success_bool, message).
    """
    outcome, msg = _attempt_send_message(token, chat_id, text, proxy_url)
    return (outcome == "success"), msg


def send_document(token, chat_id, file_path, caption="", proxy_url=""):
    outcome, msg = _attempt_send_document(token, chat_id, file_path, caption, proxy_url)
    return (outcome == "success"), msg


def test_connection(text="DPRS backup test message"):
    """Walk the saved proxy list with a tiny sendMessage call.

    Returns (success_bool, message_string). Mutates the saved proxy list:
    dead proxies are removed, the working one is recorded.
    """
    with _lock:
        settings = load_settings()
        token = settings.get("bot_token", "")
        chat_id = settings.get("chat_id", "")

        if not token or not chat_id:
            return False, "Bot token and chat ID must be configured"

        result = _walk_proxies(
            settings,
            lambda proxy: _attempt_send_message(token, chat_id, text, proxy),
        )
        save_settings(settings)
        return result["success"], result["message"]


def run_backup(db_path, run_type="manual"):
    """Send the database file once, walking the proxy list with auto-eviction.

    Records the attempt (and any evictions) in history. Returns
    (success_bool, message_string).
    """
    with _lock:
        settings = load_settings()
        token = settings.get("bot_token", "")
        chat_id = settings.get("chat_id", "")
        prefix = (settings.get("caption_prefix") or "").strip()

        if not token or not chat_id:
            msg = "Bot token and chat ID must be configured"
            append_history(settings, _entry(run_type, False, msg, "", []))
            save_settings(settings)
            return False, msg

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caption = f"{prefix + ' — ' if prefix else ''}{run_type} backup at {ts}"

        result = _walk_proxies(
            settings,
            lambda proxy: _attempt_send_document(token, chat_id, db_path, caption, proxy),
        )

        append_history(
            settings,
            _entry(run_type, result["success"], result["message"],
                   result["used_proxy"], result["evictions"]),
        )
        if result["success"]:
            settings["last_run_at"] = time.time()
        save_settings(settings)
        return result["success"], result["message"]


def _entry(run_type, success, message, used_proxy="", evictions=None):
    return {
        "ts": time.time(),
        "ts_text": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": run_type,
        "status": "ok" if success else "error",
        "message": message,
        "used_proxy": used_proxy or "",
        "evictions": list(evictions or []),
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
