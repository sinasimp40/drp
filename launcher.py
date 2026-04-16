import sys
import os
import subprocess
import datetime
import shutil
import ctypes
import json
import hmac
import hashlib

from PyQt5.QtWidgets import (
    QApplication, QSplashScreen, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QWidget, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (
    QColor, QPainter, QPixmap, QIcon, QFont, QLinearGradient,
    QRadialGradient, QPen, QPainterPath, QBrush
)

APP_NAME = "DENFI ROBLOX"
APP_VERSION = "1.0.0"
HARDCODED_PATH = ""
LICENSE_SERVER_URL = ""
_LICENSE_SECRET_XOR = [0x13,0x12,0x19,0x11,0x1e,0x08,0x1b,0x1e,0x14,0x12,0x19,0x04,0x12,0x08,0x04,0x12,0x14,0x05,0x12,0x03,0x08,0x1c,0x12,0x0e,0x08,0x65,0x67,0x65,0x63]
_LICENSE_SECRET_KEY = 0x57
EMBEDDED_LICENSE_KEY = ""
LICENSE_CHECK_INTERVAL = 10000
LICENSE_OFFLINE_GRACE = 3
LICENSE_FATAL_GRACE = 3


def _decode_secret():
    return "".join(chr(b ^ _LICENSE_SECRET_KEY) for b in _LICENSE_SECRET_XOR)


def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()

BG = "#0a0a0a"
ORANGE = "#ff6a00"
ORANGE_LIGHT = "#ff8c33"
ORANGE_DARK = "#cc5500"
TEXT_WHITE = "#f0f0f0"
TEXT_DIM = "#555555"
RED = "#ff3333"


def get_base_path():
    if HARDCODED_PATH:
        return HARDCODED_PATH
    return APP_DIR


def get_paths():
    base = get_base_path()
    roblox_dir = os.path.join(base, "RobloxFiles")

    if os.path.isfile(os.path.join(base, "RobloxPlayerBeta.exe")):
        roblox_dir = base

    if os.path.basename(base).lower() == "robloxfiles":
        roblox_dir = base

    return {
        "base": base,
        "roblox": roblox_dir,
        "cache": os.path.join(base, "Cache"),
        "logs": os.path.join(base, "Logs"),
    }


def write_log(logs_dir, message):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, f"launch_{timestamp}.log")
    with open(log_file, "w") as f:
        f.write(message)


def get_folder_fingerprint(folder):
    if not os.path.isdir(folder):
        return None
    exe = os.path.join(folder, "RobloxPlayerBeta.exe")
    if os.path.isfile(exe):
        stat = os.stat(exe)
        return f"{stat.st_size}_{stat.st_mtime}"
    return None


def find_system_roblox():
    if sys.platform != "win32":
        return None, None, None
    local_app = os.environ.get("LOCALAPPDATA", "")
    versions_path = os.path.join(local_app, "Roblox", "Versions")
    if not os.path.isdir(versions_path):
        return None, None, None
    versions = []
    for item in os.listdir(versions_path):
        full = os.path.join(versions_path, item)
        if os.path.isdir(full) and os.path.isfile(os.path.join(full, "RobloxPlayerBeta.exe")):
            versions.append((full, item))
    if not versions:
        return None, None, None
    versions.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)
    latest_path, latest_version = versions[0]
    fingerprint = get_folder_fingerprint(latest_path)
    return latest_path, fingerprint, latest_version


def get_roblox_version(roblox_dir):
    if not roblox_dir or not os.path.isdir(roblox_dir):
        return None
    folder_name = os.path.basename(roblox_dir)
    if folder_name.startswith("version-"):
        return folder_name
    for item in os.listdir(roblox_dir):
        if item.startswith("version-"):
            return item
    return None


def sync_files(source_dir, roblox_dir):
    count = 0
    removed = 0
    failed = []

    old_files = set()
    if os.path.isdir(roblox_dir):
        for item in os.listdir(roblox_dir):
            if item != "PLACE_ROBLOX_HERE.txt":
                old_files.add(item)

    new_files = set()
    for item in os.listdir(source_dir):
        src = os.path.join(source_dir, item)
        dst = os.path.join(roblox_dir, item)
        new_files.add(item)
        success = False
        for attempt in range(3):
            try:
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    count += 1
                    success = True
                    break
                elif os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    count += 1
                    success = True
                    break
            except PermissionError:
                if attempt < 2:
                    import time as _t
                    _t.sleep(0.5)
                else:
                    failed.append(item)
            except Exception:
                if attempt < 2:
                    import time as _t
                    _t.sleep(0.3)
                else:
                    failed.append(item)
        if not success and item not in failed:
            failed.append(item)

    for old_item in old_files - new_files:
        old_path = os.path.join(roblox_dir, old_item)
        try:
            if os.path.isfile(old_path):
                os.remove(old_path)
                removed += 1
            elif os.path.isdir(old_path):
                shutil.rmtree(old_path)
                removed += 1
        except Exception:
            pass

    exe_path = os.path.join(roblox_dir, "RobloxPlayerBeta.exe")
    if not os.path.isfile(exe_path):
        if "RobloxPlayerBeta.exe" in failed:
            raise PermissionError("Could not copy RobloxPlayerBeta.exe - close Roblox first and try again")
        raise FileNotFoundError("RobloxPlayerBeta.exe missing after sync")

    return count, removed, failed


_mutex_handle = None

def grab_roblox_mutex():
    global _mutex_handle
    if sys.platform != "win32":
        return False
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        handle = kernel32.CreateMutexW(None, 1, "ROBLOX_singletonEvent")
        if handle:
            _mutex_handle = handle
            return True
    except Exception:
        pass
    return False


def clear_roblox_login():
    if sys.platform != "win32":
        return "skipped"
    real_local = os.environ.get("LOCALAPPDATA", "")
    if not real_local:
        return "no_localappdata"
    local_storage = os.path.join(real_local, "Roblox", "LocalStorage")
    if not os.path.isdir(local_storage):
        return "not_found"
    cleared = 0
    for item in os.listdir(local_storage):
        item_lower = item.lower()
        should_delete = False
        if item_lower.startswith("memprofstorage") and item_lower.endswith(".json"):
            should_delete = True
        elif item_lower == "robloxcookies.dat":
            should_delete = True
        if should_delete:
            try:
                os.remove(os.path.join(local_storage, item))
                cleared += 1
            except Exception:
                pass
    return f"cleared_{cleared}"


def ensure_windowed_mode():
    if sys.platform != "win32":
        return False
    real_local = os.environ.get("LOCALAPPDATA", "")
    if not real_local:
        return False
    local_storage = os.path.join(real_local, "Roblox", "LocalStorage")
    os.makedirs(local_storage, exist_ok=True)
    app_storage_file = os.path.join(local_storage, "appStorage.json")
    data = {}
    if os.path.isfile(app_storage_file):
        try:
            with open(app_storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["IsFullscreen"] = False
    data["InFullScreen"] = False
    try:
        with open(app_storage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_existing_memprof_files():
    if sys.platform != "win32":
        return set()
    real_local = os.environ.get("LOCALAPPDATA", "")
    if not real_local:
        return set()
    local_storage = os.path.join(real_local, "Roblox", "LocalStorage")
    if not os.path.isdir(local_storage):
        return set()
    files = set()
    for item in os.listdir(local_storage):
        if item.lower().startswith("memprofstorage") and item.lower().endswith(".json"):
            files.add(item)
    return files


def parse_memprof_pid(filename):
    pid_part = filename.lower().replace("memprofstorage", "").replace(".json", "")
    if pid_part.isdigit():
        return int(pid_part)
    return None


def pid_has_visible_window(pid):
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
        EnumWindows = user32.EnumWindows
        GetWindowThreadProcessId = user32.GetWindowThreadProcessId
        IsWindowVisible = user32.IsWindowVisible

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.POINTER(ctypes.c_bool))
        found = ctypes.c_bool(False)

        def callback(hwnd, lparam):
            if IsWindowVisible(hwnd):
                win_pid = ctypes.c_ulong(0)
                GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
                if win_pid.value == pid:
                    lparam[0] = True
                    return False
            return True

        EnumWindows(WNDENUMPROC(callback), ctypes.byref(found))
        return found.value
    except Exception:
        return False


def is_pid_alive(pid):
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True,
            creationflags=0x08000000
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def kill_pid_tree(pid):
    if sys.platform != "win32":
        return
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            creationflags=0x08000000
        )
    except Exception:
        pass


def clear_instance_login(my_files):
    if sys.platform != "win32":
        return "skipped"
    real_local = os.environ.get("LOCALAPPDATA", "")
    if not real_local:
        return "no_localappdata"
    local_storage = os.path.join(real_local, "Roblox", "LocalStorage")
    if not os.path.isdir(local_storage):
        return "not_found"
    cleared = 0
    for filename in my_files:
        filepath = os.path.join(local_storage, filename)
        if os.path.isfile(filepath):
            try:
                os.remove(filepath)
                cleared += 1
            except Exception:
                pass
    cookies_path = os.path.join(local_storage, "RobloxCookies.dat")
    if os.path.isfile(cookies_path):
        try:
            os.remove(cookies_path)
            cleared += 1
        except Exception:
            pass
    return f"cleared_{cleared}"


def get_lock_file():
    return os.path.join(APP_DIR, ".launcher_lock")


def acquire_launcher_lock():
    lock_path = get_lock_file()
    try:
        if os.path.isfile(lock_path):
            try:
                with open(lock_path, "r") as f:
                    lock_data = json.load(f)
                lock_time = lock_data.get("time", 0)
                lock_pid = lock_data.get("pid", 0)
                if import_time() - lock_time < 10:
                    if lock_pid and lock_pid != os.getpid():
                        if sys.platform == "win32":
                            try:
                                result = subprocess.run(
                                    ["tasklist", "/FI", f"PID eq {lock_pid}", "/NH"],
                                    capture_output=True, text=True,
                                    creationflags=0x08000000
                                )
                                if str(lock_pid) in result.stdout:
                                    return False
                            except Exception:
                                pass
            except Exception:
                pass
        with open(lock_path, "w") as f:
            json.dump({"time": import_time(), "pid": os.getpid()}, f)
        return True
    except Exception:
        return True


def release_launcher_lock():
    lock_path = get_lock_file()
    try:
        if os.path.isfile(lock_path):
            with open(lock_path, "r") as f:
                lock_data = json.load(f)
            if lock_data.get("pid") == os.getpid():
                os.remove(lock_path)
    except Exception:
        pass


class SplashScreen(QSplashScreen):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen)
        self.progress = 0
        self.status_msg = "Initializing..."
        self.error_msg = ""
        self.is_error = False
        self._base_pixmap = pixmap
        self.roblox_version = ""

    def set_progress(self, value, msg=""):
        self.progress = value
        if msg:
            self.status_msg = msg
        self.repaint()

    def show_error(self, msg):
        self.is_error = True
        self.error_msg = msg
        self.progress = 100
        self.status_msg = ""
        self.repaint()

    def drawContents(self, painter):
        w = self._base_pixmap.width()
        h = self._base_pixmap.height()

        bar_y = h - 70
        bar_x = 80
        bar_w = w - 160
        bar_h = 3

        status_y = bar_y - 30
        version_y = h - 35

        if self.is_error:
            painter.fillRect(0, status_y - 10, w, h - status_y + 10, QColor("#0d0000"))

            painter.setPen(QColor(RED))
            painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
            painter.drawText(0, status_y - 5, w, 22, Qt.AlignCenter, "ERROR")

            painter.setPen(QColor("#cccccc"))
            painter.setFont(QFont("Segoe UI", 9))
            lines = self.error_msg.split("\n")
            y_off = status_y + 20
            for line in lines[:3]:
                painter.drawText(30, y_off, w - 60, 18, Qt.AlignCenter, line)
                y_off += 18

            painter.fillRect(bar_x, bar_y + 25, bar_w, bar_h, QColor(RED))
        else:
            painter.fillRect(0, status_y - 5, w, 25, QColor("#0a0a0a"))

            painter.setPen(QColor("#888888"))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(0, status_y, w, 20, Qt.AlignCenter, self.status_msg)

            painter.fillRect(bar_x, bar_y, bar_w, bar_h, QColor("#1e1e1e"))

            if self.progress > 0:
                fill_w = int(bar_w * self.progress / 100)
                bar_grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
                bar_grad.setColorAt(0, QColor("#ff6a00"))
                bar_grad.setColorAt(1, QColor("#ff9d4d"))
                painter.fillRect(bar_x, bar_y, fill_w, bar_h, bar_grad)

                glow = QRadialGradient(bar_x + fill_w, bar_y + bar_h // 2, 12)
                glow.setColorAt(0, QColor(255, 106, 0, 80))
                glow.setColorAt(1, QColor(255, 106, 0, 0))
                painter.setBrush(QBrush(glow))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(bar_x + fill_w - 12, bar_y - 10, 24, 24)

            if self.roblox_version:
                painter.setPen(QColor("#444444"))
                painter.setFont(QFont("Segoe UI", 8))
                painter.drawText(0, version_y, w, 16, Qt.AlignCenter, self.roblox_version)


_cached_splash_pixmap = None

def create_splash_pixmap():
    global _cached_splash_pixmap
    if _cached_splash_pixmap is not None:
        return _cached_splash_pixmap
    w, h = 560, 380
    splash_pix = QPixmap(w, h)
    splash_pix.fill(QColor("#0a0a0a"))

    painter = QPainter(splash_pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    bg_grad = QLinearGradient(0, 0, w, h)
    bg_grad.setColorAt(0.0, QColor("#0c0c0c"))
    bg_grad.setColorAt(0.3, QColor("#111111"))
    bg_grad.setColorAt(0.7, QColor("#0e0e0e"))
    bg_grad.setColorAt(1.0, QColor("#0a0a0a"))
    painter.fillRect(0, 0, w, h, bg_grad)

    center_glow = QRadialGradient(w / 2, 140, 200)
    center_glow.setColorAt(0, QColor(255, 106, 0, 18))
    center_glow.setColorAt(0.5, QColor(255, 106, 0, 6))
    center_glow.setColorAt(1, QColor(0, 0, 0, 0))
    painter.fillRect(0, 0, w, h, center_glow)

    border_pen = QPen(QColor("#1c1c1c"))
    border_pen.setWidth(1)
    painter.setPen(border_pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(0, 0, w - 1, h - 1)

    inner_pen = QPen(QColor(255, 106, 0, 25))
    inner_pen.setWidth(1)
    painter.setPen(inner_pen)
    painter.drawRect(1, 1, w - 3, h - 3)

    logo_size = 80
    logo_path = None
    for candidate in [
        os.path.join(APP_DIR, "splash_logo.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "splash_logo.png"),
    ]:
        if os.path.isfile(candidate):
            logo_path = candidate
            break
    if getattr(sys, 'frozen', False):
        bundle_logo = os.path.join(sys._MEIPASS, "splash_logo.png")
        if os.path.isfile(bundle_logo):
            logo_path = bundle_logo

    if logo_path:
        logo_pix = QPixmap(logo_path)
        if not logo_pix.isNull():
            logo_pix = logo_pix.scaled(logo_size, logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_x = (w - logo_pix.width()) // 2
            logo_y = 35
            painter.drawPixmap(logo_x, logo_y, logo_pix)

    title_y = 140
    painter.setPen(QColor("#ff6a00"))
    title_font = QFont("Segoe UI", 32, QFont.Bold)
    title_font.setLetterSpacing(QFont.AbsoluteSpacing, 6)
    painter.setFont(title_font)
    painter.drawText(0, title_y, w, 45, Qt.AlignCenter, APP_NAME)

    sub_y = title_y + 52
    painter.setPen(QColor("#cc5500"))
    sub_font = QFont("Segoe UI", 13)
    sub_font.setLetterSpacing(QFont.AbsoluteSpacing, 12)
    painter.setFont(sub_font)
    painter.drawText(0, sub_y, w, 25, Qt.AlignCenter, "PORTABLE")

    line_y = sub_y + 35
    line_w = 100
    line_x = (w - line_w) // 2
    line_grad = QLinearGradient(line_x, 0, line_x + line_w, 0)
    line_grad.setColorAt(0, QColor(255, 106, 0, 0))
    line_grad.setColorAt(0.3, QColor(255, 106, 0, 60))
    line_grad.setColorAt(0.5, QColor(255, 106, 0, 90))
    line_grad.setColorAt(0.7, QColor(255, 106, 0, 60))
    line_grad.setColorAt(1, QColor(255, 106, 0, 0))
    painter.fillRect(line_x, line_y, line_w, 1, line_grad)

    painter.end()
    _cached_splash_pixmap = splash_pix
    return splash_pix


def get_license_file():
    return os.path.join(APP_DIR, ".license_key")


def _get_file_xor_key():
    seed = APP_NAME + "LIC" + str(len(_LICENSE_SECRET_XOR))
    return hashlib.md5(seed.encode("utf-8")).digest()


def _encrypt_key(plaintext):
    xor_key = _get_file_xor_key()
    data = plaintext.encode("utf-8")
    encrypted = bytes([data[i] ^ xor_key[i % len(xor_key)] for i in range(len(data))])
    return encrypted


def _decrypt_key(raw_bytes):
    import re
    try:
        text = raw_bytes.decode("utf-8", errors="replace").strip()
    except Exception:
        text = ""
    if re.match(r'^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$', text):
        return text
    xor_key = _get_file_xor_key()
    decrypted = bytes([raw_bytes[i] ^ xor_key[i % len(xor_key)] for i in range(len(raw_bytes))])
    try:
        result = decrypted.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""
    if re.match(r'^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$', result):
        return result
    return ""


def load_saved_license():
    if EMBEDDED_LICENSE_KEY:
        return EMBEDDED_LICENSE_KEY

    path = get_license_file()
    if os.path.isfile(path):
        try:
            with open(path, "rb") as f:
                raw = f.read()
                if raw:
                    key = _decrypt_key(raw)
                    if key:
                        return key
        except Exception:
            pass

    return ""


def save_license_key(key):
    if EMBEDDED_LICENSE_KEY:
        return True

    path = get_license_file()
    try:
        encrypted = _encrypt_key(key)
        with open(path, "wb") as f:
            f.write(encrypted)
        return True
    except Exception:
        return False


def delete_license_files():
    path = get_license_file()
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass


def verify_signature(data_dict, signature):
    secret = _decode_secret()
    payload = json.dumps(data_dict, sort_keys=True, separators=(',', ':'))
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def sign_request(body_dict):
    secret = _decode_secret()
    timestamp = str(int(import_time()))
    nonce = hashlib.md5(os.urandom(16)).hexdigest()[:12]
    body_json = json.dumps(body_dict, sort_keys=True, separators=(',', ':'))
    sign_payload = f"{timestamp}:{nonce}:{body_json}"
    sig = hmac.new(
        secret.encode('utf-8'),
        sign_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return timestamp, nonce, sig


def import_time():
    import time as _t
    return _t.time()


def validate_license(key, endpoint="validate"):
    if not LICENSE_SERVER_URL:
        return {"valid": True, "remaining_text": "No server configured", "remaining_seconds": 999999}
    try:
        import urllib.request
        url = LICENSE_SERVER_URL.rstrip("/") + f"/api/{endpoint}"
        body = {"key": key, "version": APP_VERSION}
        timestamp, nonce, req_sig = sign_request(body)
        req_data = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers={
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": req_sig,
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        data = result.get("data", {})
        sig = result.get("signature", "")

        if not verify_signature(data, sig):
            return {"valid": False, "error": "Invalid server signature"}

        return data
    except Exception as e:
        return {"valid": False, "error": f"Server unreachable: {str(e)[:80]}"}


def check_for_update(key):
    if not LICENSE_SERVER_URL:
        return None
    try:
        import urllib.request
        url = LICENSE_SERVER_URL.rstrip("/") + "/api/update_check"
        body = {"key": key, "version": APP_VERSION}
        timestamp, nonce, req_sig = sign_request(body)
        req_data = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers={
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": req_sig,
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        data = result.get("data", {})
        sig = result.get("signature", "")
        if not verify_signature(data, sig):
            return None
        if data.get("update_available"):
            return data
        return None
    except Exception:
        return None


def _report_download_progress(pct, version, status="downloading"):
    if not LICENSE_SERVER_URL:
        return
    try:
        import urllib.request
        url = LICENSE_SERVER_URL.rstrip("/") + "/api/report_download_progress"
        key = load_saved_license() or EMBEDDED_LICENSE_KEY
        body = {
            "license_key": key,
            "progress": pct,
            "version": version,
            "status": status,
        }
        timestamp, nonce, req_sig = sign_request(body)
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": req_sig,
        })
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def download_update(update_info, progress_callback=None):
    if not LICENSE_SERVER_URL:
        return None
    try:
        import urllib.request
        token = update_info.get("download_token", "")
        if not token:
            return None
        version = update_info.get("latest_version", "")
        url = LICENSE_SERVER_URL.rstrip("/") + f"/api/download_update/{token}"
        req = urllib.request.Request(url)
        _report_download_progress(0, version, "downloading")
        with urllib.request.urlopen(req, timeout=300) as resp:
            total_size = update_info.get("file_size", 0)
            data = bytearray()
            block_size = 65536
            downloaded = 0
            last_reported = 0
            while True:
                chunk = resp.read(block_size)
                if not chunk:
                    break
                data.extend(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = min(100, int(downloaded * 100 / total_size))
                    if progress_callback:
                        progress_callback(pct, downloaded, total_size)
                    if pct - last_reported >= 5:
                        last_reported = pct
                        _report_download_progress(pct, version, "downloading")

        if len(data) < 1024:
            _report_download_progress(0, version, "failed")
            return None

        expected_hash = update_info.get("sha256", "")
        if expected_hash:
            actual_hash = hashlib.sha256(data).hexdigest()
            if actual_hash != expected_hash:
                _report_download_progress(0, version, "failed")
                return None

        if total_size > 0 and len(data) != total_size:
            _report_download_progress(0, version, "failed")
            return None

        temp_dir = os.path.join(APP_DIR, "_update")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"update_{version or 'new'}.exe")
        with open(temp_path, "wb") as f:
            f.write(data)
        _report_download_progress(100, version, "completed")
        return temp_path
    except Exception:
        try:
            _report_download_progress(0, update_info.get("latest_version", ""), "failed")
        except Exception:
            pass
        return None


def apply_update_and_restart(new_exe_path):
    if sys.platform != "win32":
        return False
    if not getattr(sys, 'frozen', False):
        return False
    try:
        current_exe = sys.executable
        backup_path = current_exe + ".bak"

        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except Exception:
                pass

        os.rename(current_exe, backup_path)

        shutil.copy2(new_exe_path, current_exe)

        try:
            os.remove(new_exe_path)
            update_dir = os.path.dirname(new_exe_path)
            if os.path.isdir(update_dir) and not os.listdir(update_dir):
                os.rmdir(update_dir)
        except Exception:
            pass

        return True
    except Exception:
        if os.path.exists(backup_path) and not os.path.exists(current_exe):
            try:
                os.rename(backup_path, current_exe)
            except Exception:
                pass
        return False


def _is_suspended_error(error_msg):
    return "suspended" in error_msg.lower()


def _is_fatal_license_error(error_msg):
    fatal_phrases = ["expired", "revoked", "deleted", "not found"]
    lower = error_msg.lower()
    return any(phrase in lower for phrase in fatal_phrases)


class LicenseDialog(QDialog):
    def __init__(self, parent=None, error_msg=""):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - License")
        self.setFixedSize(420, 260)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.result_key = ""

        self.setStyleSheet(f"""
            QDialog {{ background: #0a0a0a; border: 1px solid #1e1e1e; }}
            QLabel {{ color: #f0f0f0; background: transparent; }}
            QLineEdit {{
                background: #111; border: 1px solid #2a2a2a; border-radius: 6px;
                color: #ff8c33; padding: 10px 12px; font-size: 14px;
                font-family: Consolas, monospace; letter-spacing: 1px;
            }}
            QLineEdit:focus {{ border-color: #ff6a00; }}
            QPushButton {{
                background: #ff6a00; color: white; border: none; border-radius: 6px;
                padding: 10px 24px; font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background: #ff8c33; }}
            QPushButton:disabled {{ background: #333; color: #666; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(12)

        title = QLabel(APP_NAME)
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #ff6a00;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Enter your license key to continue")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #666;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        if error_msg:
            err_label = QLabel(error_msg)
            err_label.setFont(QFont("Segoe UI", 9))
            err_label.setStyleSheet("color: #ff4444;")
            err_label.setAlignment(Qt.AlignCenter)
            err_label.setWordWrap(True)
            layout.addWidget(err_label)

        layout.addSpacing(8)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXXX-XXXXX-XXXXX-XXXXX")
        self.key_input.setMaxLength(23)
        layout.addWidget(self.key_input)

        btn_row = QHBoxLayout()
        self.activate_btn = QPushButton("Activate")
        self.activate_btn.clicked.connect(self.on_activate)
        btn_row.addWidget(self.activate_btn)

        quit_btn = QPushButton("Quit")
        quit_btn.setStyleSheet("background: #1e1e1e; color: #888;")
        quit_btn.clicked.connect(self.reject)
        btn_row.addWidget(quit_btn)
        layout.addLayout(btn_row)

        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.key_input.returnPressed.connect(self.on_activate)

    def on_activate(self):
        key = self.key_input.text().strip()
        if not key:
            self.status_label.setStyleSheet("color: #ff4444;")
            self.status_label.setText("Please enter a license key")
            return

        self.activate_btn.setEnabled(False)
        self.status_label.setStyleSheet("color: #888;")
        self.status_label.setText("Validating...")
        QApplication.processEvents()

        result = validate_license(key)
        if result.get("valid"):
            self.result_key = key
            self.accept()
        else:
            self.activate_btn.setEnabled(True)
            self.status_label.setStyleSheet("color: #ff4444;")
            self.status_label.setText(result.get("error", "Validation failed"))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)


class LockScreen(QWidget):
    def __init__(self, reason="License expired"):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - Locked")
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setStyleSheet("background: #0a0a0a; border: 1px solid #1e1e1e;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        title = QLabel(APP_NAME)
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #ff4444;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        msg = QLabel(reason)
        msg.setFont(QFont("Segoe UI", 11))
        msg.setStyleSheet("color: #ccc;")
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        quit_btn = QPushButton("Close")
        quit_btn.setStyleSheet("""
            QPushButton { background: #ff4444; color: white; border: none;
                         border-radius: 6px; padding: 10px 24px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #ff6666; }
        """)
        quit_btn.clicked.connect(lambda: QApplication.instance().quit())
        layout.addWidget(quit_btn)


def _show_suspended_and_exit(app, splash=None):
    if splash:
        splash.hide()
    lock = LockScreen("License suspended.\nContact the developer.")
    lock.show()
    app._lock_screen = lock
    QTimer.singleShot(15000, app.quit)
    sys.exit(app.exec_())


def check_license_or_prompt(app, splash=None):
    if not LICENSE_SERVER_URL:
        return True

    saved_key = load_saved_license()
    error_msg = ""

    if saved_key:
        if splash:
            splash.set_progress(5, "Checking license...")
            app.processEvents()

        result = validate_license(saved_key)
        if result.get("valid"):
            return True
        error_msg = result.get("error", "License invalid")

        if _is_suspended_error(error_msg):
            _show_suspended_and_exit(app, splash)

        if error_msg == "License already activated":
            hb = validate_license(saved_key, "heartbeat")
            if hb.get("valid"):
                return True
            error_msg = hb.get("error", "License invalid")
            if _is_suspended_error(error_msg):
                _show_suspended_and_exit(app, splash)

        if EMBEDDED_LICENSE_KEY:
            return False

    if EMBEDDED_LICENSE_KEY:
        return False

    if splash:
        splash.hide()

    while True:
        dialog = LicenseDialog(error_msg=error_msg)
        if dialog.exec_() == QDialog.Accepted:
            if not save_license_key(dialog.result_key):
                from PyQt5.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setWindowTitle("Warning")
                msg.setText("License activated but could not save the key file.\n\n"
                            "You may be asked to enter the key again next time.\n\n"
                            "To fix this, make sure the folder containing\n"
                            f"{os.path.basename(sys.executable)} is writable.")
                msg.setStyleSheet("QMessageBox { background: #1a1a1a; color: white; }"
                                  "QLabel { color: white; }"
                                  "QPushButton { background: #ff6a00; color: white; border: none; "
                                  "border-radius: 4px; padding: 6px 16px; }"
                                  "QPushButton:hover { background: #ff8c33; }")
                msg.exec_()
            if splash:
                splash.show()
            return True
        else:
            return False


def kill_all_roblox_pids(app):
    if sys.platform != "win32":
        return
    if hasattr(app, '_roblox_pid') and app._roblox_pid:
        if is_pid_alive(app._roblox_pid):
            kill_pid_tree(app._roblox_pid)
    if hasattr(app, '_watcher_state'):
        state = app._watcher_state
        for pid in state.get("my_pids", set()):
            if is_pid_alive(pid):
                kill_pid_tree(pid)
        my_files = state.get("my_files", set())
        if my_files:
            clear_instance_login(my_files)


def start_license_watchdog(app):
    if not LICENSE_SERVER_URL:
        return None

    key = load_saved_license()
    if not key:
        return None

    app._license_fail_count = 0
    app._license_fatal_count = 0

    def check():
        result = validate_license(key, "heartbeat")
        if not result.get("valid"):
            error_msg = result.get("error", "")
            is_network_error = "unreachable" in error_msg.lower() or "timeout" in error_msg.lower()
            is_suspended = _is_suspended_error(error_msg)
            is_fatal = _is_fatal_license_error(error_msg)

            if is_network_error:
                app._license_fail_count += 1
                app._license_fatal_count = 0
                if app._license_fail_count < LICENSE_OFFLINE_GRACE:
                    return
            elif is_suspended or is_fatal:
                app._license_fatal_count += 1
                app._license_fail_count = 0
                if app._license_fatal_count < LICENSE_FATAL_GRACE:
                    return
            else:
                app._license_fail_count += 1
                if app._license_fail_count < LICENSE_OFFLINE_GRACE:
                    return

            app._license_fail_count = 0
            app._license_fatal_count = 0

            if hasattr(app, '_license_timer'):
                app._license_timer.stop()
            kill_all_roblox_pids(app)
            if hasattr(app, '_bg_timer'):
                app._bg_timer.stop()

            if is_suspended:
                lock = LockScreen("License suspended.\nContact the developer.")
            elif not EMBEDDED_LICENSE_KEY:
                delete_license_files()
                lock = LockScreen(result.get("error", "License expired or revoked"))
            else:
                lock = LockScreen(result.get("error", "License expired or revoked"))

            lock.show()
            app._lock_screen = lock
            QTimer.singleShot(10000, app.quit)
        else:
            app._license_fail_count = 0
            app._license_fatal_count = 0

    timer = QTimer()
    timer.timeout.connect(check)
    timer.start(LICENSE_CHECK_INTERVAL)
    app._license_timer = timer
    return timer


def main():
    if sys.platform != "win32":
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"denfi.{APP_NAME}.launcher")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    icon_path = os.path.join(APP_DIR, "icon.ico")
    if not os.path.exists(icon_path) and getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    if getattr(sys, 'frozen', False):
        bak_path = sys.executable + ".bak"
        if os.path.exists(bak_path):
            try:
                os.remove(bak_path)
            except Exception:
                pass
        update_dir = os.path.join(APP_DIR, "_update")
        if os.path.isdir(update_dir):
            try:
                shutil.rmtree(update_dir, ignore_errors=True)
            except Exception:
                pass

    splash_pix = create_splash_pixmap()
    splash = SplashScreen(splash_pix)
    splash.set_progress(0, "Starting...")
    splash.show()
    app.processEvents()

    if not acquire_launcher_lock():
        saved_key = load_saved_license()
        if saved_key and LICENSE_SERVER_URL:
            splash.set_progress(5, "Checking license...")
            app.processEvents()
            hb = validate_license(saved_key, "heartbeat")
            if hb.get("valid"):
                pass
            else:
                error_msg = hb.get("error", "")
                if _is_suspended_error(error_msg):
                    _show_suspended_and_exit(app, splash)

    if not check_license_or_prompt(app, splash):
        release_launcher_lock()
        sys.exit(0)

    saved_key_for_update = load_saved_license()
    if saved_key_for_update and LICENSE_SERVER_URL:
        splash.set_progress(8, "Checking for updates...")
        app.processEvents()
        update_info = check_for_update(saved_key_for_update)
        if update_info:
            new_version = update_info.get("latest_version", "?")
            file_size = update_info.get("file_size", 0)
            size_mb = file_size / 1024 / 1024 if file_size else 0

            def on_download_progress(pct, downloaded, total):
                dl_mb = downloaded / 1024 / 1024
                splash.set_progress(8 + int(pct * 0.85), f"Downloading v{new_version}... {dl_mb:.1f}/{size_mb:.1f} MB")
                app.processEvents()

            splash.set_progress(8, f"Update v{new_version} found ({size_mb:.1f} MB)...")
            app.processEvents()

            new_exe = download_update(update_info, on_download_progress)
            if new_exe:
                splash.set_progress(95, f"Installing v{new_version}...")
                app.processEvents()
                if apply_update_and_restart(new_exe):
                    splash.set_progress(100, f"Update v{new_version} installed!")
                    app.processEvents()
                    splash.hide()
                    msg = QMessageBox()
                    msg.setWindowTitle("Update Installed")
                    msg.setText(f"Update v{new_version} installed successfully!\n\nPlease reopen the app to use the new version.")
                    msg.setIcon(QMessageBox.Information)
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.setStyleSheet("QMessageBox { background-color: #1a1a1a; color: #f0f0f0; } QPushButton { background-color: #00c853; color: #fff; padding: 6px 20px; border: none; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #00a844; }")
                    msg.exec_()
                    release_launcher_lock()
                    sys.exit(0)
                else:
                    splash.set_progress(8, "Update failed, continuing...")
                    app.processEvents()

    paths = get_paths()

    log_lines = []
    log_lines.append(f"Launcher: {APP_NAME} v{APP_VERSION}")
    log_lines.append(f"Time: {datetime.datetime.now()}")
    log_lines.append(f"Base path: {paths['base']}")

    sync_state = {"do_sync": False, "source": "", "fp": ""}
    step_index = [0]

    def do_step():
        idx = step_index[0]

        if idx == 0:
            splash.set_progress(10, "Preparing folders...")
            app.processEvents()
            os.makedirs(paths["roblox"], exist_ok=True)
            os.makedirs(paths["cache"], exist_ok=True)
            os.makedirs(paths["logs"], exist_ok=True)
            log_lines.append("Folders ready")

        elif idx == 1:
            splash.set_progress(25, "Checking Roblox files...")
            app.processEvents()
            exe_path = os.path.join(paths["roblox"], "RobloxPlayerBeta.exe")
            if os.path.isfile(exe_path):
                files = os.listdir(paths["roblox"])
                dll_count = len([f for f in files if f.lower().endswith(".dll")])
                log_lines.append(f"Found {len(files)} files, {dll_count} DLLs")
            else:
                log_lines.append("RobloxPlayerBeta.exe not found yet")

        elif idx == 2:
            splash.set_progress(40, "Scanning for updates...")
            app.processEvents()
            system_path, system_fp, sys_version = find_system_roblox()

            if sys_version:
                splash.roblox_version = sys_version
            elif not splash.roblox_version:
                detected = get_roblox_version(paths["roblox"])
                splash.roblox_version = detected if detected else "Roblox"

            if system_path:
                portable_fp = get_folder_fingerprint(paths["roblox"])
                needs_update = system_fp and (system_fp != portable_fp)
                needs_first = not os.path.isfile(os.path.join(paths["roblox"], "RobloxPlayerBeta.exe"))

                if needs_update or needs_first:
                    sync_state["do_sync"] = True
                    sync_state["source"] = system_path
                    sync_state["fp"] = system_fp
                    reason = "first sync" if needs_first else "update detected"
                    log_lines.append(f"Sync needed ({reason}): {system_path}")
                else:
                    log_lines.append("Roblox files up to date")
            else:
                log_lines.append("No system Roblox found")

        elif idx == 3:
            if sync_state["do_sync"]:
                splash.set_progress(55, "Syncing Roblox files...")
                app.processEvents()
                try:
                    count, removed, failed = sync_files(sync_state["source"], paths["roblox"])
                    log_lines.append(f"Synced {count} files, cleaned {removed} old files")
                    if failed:
                        log_lines.append(f"Failed to sync: {', '.join(failed)}")
                    splash.set_progress(70, f"Synced {count} files!")
                    app.processEvents()
                except PermissionError as e:
                    log_lines.append(f"Sync blocked: {e}")
                    splash.set_progress(70, "Close Roblox and try again!")
                    app.processEvents()
                    splash.show_error(str(e))
                    write_log(paths["logs"], "\n".join(log_lines))
                    QTimer.singleShot(5000, app.quit)
                    return app.exec_()
                except Exception as e:
                    log_lines.append(f"Sync failed: {e}")
                    splash.set_progress(70, "Sync failed - using existing files")
                    app.processEvents()
            else:
                splash.set_progress(70, "Files ready!")
                app.processEvents()

        elif idx == 4:
            exe_path = os.path.join(paths["roblox"], "RobloxPlayerBeta.exe")
            if not os.path.isfile(exe_path):
                log_lines.append("ERROR: RobloxPlayerBeta.exe not found")
                log_lines.append(f"Expected at: {paths['roblox']}")
                write_log(paths["logs"], "\n".join(log_lines))

                splash.show_error(
                    f"No Roblox files found!\n"
                    f"Copy files to: {paths['roblox']}"
                )
                app.processEvents()
                QTimer.singleShot(5000, app.quit)
                return

            splash.set_progress(75, "Grabbing mutex...")
            app.processEvents()

            mutex_ok = grab_roblox_mutex()
            if mutex_ok:
                log_lines.append("Mutex acquired - multi-client enabled")
            else:
                log_lines.append("Could not acquire mutex (non-Windows or error)")

            splash.set_progress(80, "Clearing login data...")
            app.processEvents()

            login_result = clear_roblox_login()
            log_lines.append(f"Login clear (rbx-storage.db): {login_result}")

            ensure_windowed_mode()
            log_lines.append("Windowed mode settings applied")

            splash.set_progress(85, "Launching Roblox...")
            app.processEvents()

            try:
                process = subprocess.Popen(
                    [exe_path],
                    cwd=paths["roblox"],
                )
                app._roblox_pid = process.pid
                log_lines.append(f"Roblox launched (PID: {process.pid})")
                log_lines.append(f"Executable: {exe_path}")
            except Exception as e:
                log_lines.append(f"Launch failed: {e}")
                write_log(paths["logs"], "\n".join(log_lines))

                splash.show_error(
                    f"Could not launch Roblox!\n"
                    f"{str(e)[:60]}"
                )
                app.processEvents()
                QTimer.singleShot(5000, app.quit)
                return

        elif idx == 5:
            splash.set_progress(100, "Roblox is running!")
            app.processEvents()
            write_log(paths["logs"], "\n".join(log_lines))

            release_launcher_lock()

            app.setQuitOnLastWindowClosed(False)
            start_license_watchdog(app)
            files_before = get_existing_memprof_files()

            def hide_and_watch():
                splash.hide()
                state = {"phase": "WAIT_FILES", "my_files": set(), "my_pids": set(),
                         "no_window_count": 0, "cleanup_attempts": 0}
                app._watcher_state = state

                def watcher_tick():
                    if state["phase"] == "WAIT_FILES":
                        current_files = get_existing_memprof_files()
                        new_files = current_files - files_before
                        if new_files:
                            state["my_files"] = new_files
                            state["my_pids"] = set()
                            for f in new_files:
                                pid = parse_memprof_pid(f)
                                if pid:
                                    state["my_pids"].add(pid)
                            state["phase"] = "ACTIVE"

                    elif state["phase"] == "ACTIVE":
                        has_window = False
                        for pid in state["my_pids"]:
                            if pid_has_visible_window(pid):
                                has_window = True
                                break
                        if has_window:
                            state["no_window_count"] = 0
                        else:
                            state["no_window_count"] += 1
                            if state["no_window_count"] >= 2:
                                state["phase"] = "CLOSING"

                    elif state["phase"] == "CLOSING":
                        for pid in state["my_pids"]:
                            if is_pid_alive(pid):
                                kill_pid_tree(pid)
                        state["phase"] = "CLEANUP"

                    elif state["phase"] == "CLEANUP":
                        state["cleanup_attempts"] += 1
                        clear_instance_login(state["my_files"])
                        remaining = False
                        real_local = os.environ.get("LOCALAPPDATA", "")
                        local_storage = os.path.join(real_local, "Roblox", "LocalStorage")
                        for f in state["my_files"]:
                            if os.path.isfile(os.path.join(local_storage, f)):
                                remaining = True
                        if not remaining or state["cleanup_attempts"] >= 6:
                            app.quit()

                timer = QTimer()
                timer.timeout.connect(watcher_tick)
                timer.start(3000)
                app._bg_timer = timer

            QTimer.singleShot(1500, hide_and_watch)
            return

        step_index[0] += 1
        QTimer.singleShot(400, do_step)

    QTimer.singleShot(300, do_step)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
