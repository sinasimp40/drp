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
    QLabel, QLineEdit, QPushButton, QWidget, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import (
    QColor, QPainter, QPixmap, QIcon, QFont, QFontMetrics, QLinearGradient,
    QRadialGradient, QPen, QPainterPath, QBrush, QFontDatabase
)

APP_NAME = "DENFI ROBLOX"
APP_VERSION = "1.0.1"
HARDCODED_PATH = ""
LICENSE_SERVER_URL = ""
_LICENSE_SECRET_XOR = [0x13,0x12,0x19,0x11,0x1e,0x08,0x1b,0x1e,0x14,0x12,0x19,0x04,0x12,0x08,0x04,0x12,0x14,0x05,0x12,0x03,0x08,0x1c,0x12,0x0e,0x08,0x65,0x67,0x65,0x63]
_LICENSE_SECRET_KEY = 0x57
EMBEDDED_LICENSE_KEY = ""
CONFIG_HASH = ""
CONFIG_ID = 0
LICENSE_CHECK_INTERVAL = 10000
LICENSE_OFFLINE_GRACE = 18
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


_launcher_mutex_handle = None
_update_heartbeat_stop = None
UPDATE_STATE_FILE = ".update_state"
UPDATE_HEARTBEAT_TIMEOUT = 120


def _singleton_mutex_name():
    h = hashlib.sha1(APP_DIR.lower().encode("utf-8", "replace")).hexdigest()[:16]
    return f"Local\\DenfiLauncher_{h}"


def acquire_singleton_mutex():
    global _launcher_mutex_handle
    if sys.platform != "win32":
        return True
    try:
        ERROR_ALREADY_EXISTS = 183
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        kernel32.GetLastError.restype = ctypes.c_uint
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.CreateMutexW(None, 1, _singleton_mutex_name())
        if not handle:
            return False
        last_err = kernel32.GetLastError()
        if last_err == ERROR_ALREADY_EXISTS:
            try:
                kernel32.CloseHandle(handle)
            except Exception:
                pass
            return False
        _launcher_mutex_handle = handle
        return True
    except Exception:
        return False


def acquire_singleton_mutex_with_retry(timeout_s=10.0, interval_s=0.25):
    import time as _t
    deadline = import_time() + timeout_s
    while True:
        if acquire_singleton_mutex():
            return True
        if import_time() >= deadline:
            return False
        try:
            _t.sleep(interval_s)
        except Exception:
            pass


def release_singleton_mutex():
    global _launcher_mutex_handle
    if _launcher_mutex_handle is None or sys.platform != "win32":
        _launcher_mutex_handle = None
        return
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle(_launcher_mutex_handle)
    except Exception:
        pass
    _launcher_mutex_handle = None


def get_update_state_file():
    return os.path.join(APP_DIR, UPDATE_STATE_FILE)


def write_update_state(phase, target_version=""):
    try:
        with open(get_update_state_file(), "w") as f:
            json.dump({
                "pid": os.getpid(),
                "phase": phase,
                "target_version": target_version,
                "started_at": import_time(),
                "last_heartbeat": import_time(),
            }, f)
    except Exception:
        pass


def update_state_heartbeat(phase=None, target_version=None):
    try:
        path = get_update_state_file()
        data = {}
        if os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        existing_pid = data.get("pid")
        if existing_pid and existing_pid != os.getpid():
            return
        data["pid"] = os.getpid()
        data["last_heartbeat"] = import_time()
        if "started_at" not in data:
            data["started_at"] = import_time()
        if phase is not None:
            data["phase"] = phase
        if target_version is not None:
            data["target_version"] = target_version
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def read_update_state():
    try:
        with open(get_update_state_file(), "r") as f:
            return json.load(f)
    except Exception:
        return None


def clear_update_state():
    try:
        os.remove(get_update_state_file())
    except Exception:
        pass


def _is_pid_alive(pid):
    if not pid:
        return False
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True,
            creationflags=0x08000000,
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def is_update_state_stale(state):
    if not state:
        return True
    pid = state.get("pid")
    if pid and pid != os.getpid() and not _is_pid_alive(pid):
        return True
    hb = state.get("last_heartbeat", 0)
    if import_time() - hb > UPDATE_HEARTBEAT_TIMEOUT:
        return True
    return False


def start_update_heartbeat():
    global _update_heartbeat_stop
    import threading
    import time as _t
    _update_heartbeat_stop = threading.Event()
    stop_evt = _update_heartbeat_stop

    def _loop():
        while not stop_evt.is_set():
            update_state_heartbeat()
            stop_evt.wait(15)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def stop_update_heartbeat():
    global _update_heartbeat_stop
    if _update_heartbeat_stop is not None:
        try:
            _update_heartbeat_stop.set()
        except Exception:
            pass
        _update_heartbeat_stop = None


def recover_from_interrupted_update():
    """Run at startup, before acquiring the singleton mutex.

    1. If current.exe is missing but current.exe.bak exists (a swap was
       interrupted), restore the backup.
    2. If the update-gate state file is stale (PID dead or heartbeat
       expired), clear it and remove leftover _update/ temp files.
    3. If no fresh update gate exists and current.exe is in place, the
       leftover .bak from a previous successful update can be removed.
    """
    state = read_update_state()
    state_is_stale = is_update_state_stale(state) if state else True

    if state and state_is_stale:
        clear_update_state()

    if not state_is_stale:
        return

    if sys.platform == "win32" and getattr(sys, 'frozen', False):
        try:
            current_exe = sys.executable
            bak_path = current_exe + ".bak"
            new_path = current_exe + ".new"
            if os.path.exists(bak_path) and not os.path.exists(current_exe):
                try:
                    os.replace(bak_path, current_exe)
                except Exception:
                    pass
            if os.path.exists(new_path) and os.path.exists(current_exe):
                try:
                    os.remove(new_path)
                except Exception:
                    pass
        except Exception:
            pass

    update_dir = os.path.join(APP_DIR, "_update")
    if os.path.isdir(update_dir):
        try:
            shutil.rmtree(update_dir, ignore_errors=True)
        except Exception:
            pass
    if getattr(sys, 'frozen', False):
        try:
            current_exe = sys.executable
            bak_path = current_exe + ".bak"
            if os.path.exists(bak_path) and os.path.exists(current_exe):
                try:
                    os.remove(bak_path)
                except Exception:
                    pass
        except Exception:
            pass


SPLASH_W = 680
SPLASH_H = 380
ORANGE_W = 290

class SplashScreen(QSplashScreen):
    LOGO_MAX_W = ORANGE_W - 60
    LOGO_MAX_H = 200

    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen)
        self.progress = 0
        self.status_msg = "Initializing..."
        self.error_msg = ""
        self.is_error = False
        self._base_pixmap = pixmap
        self.roblox_version = ""
        self._logo_label = None
        self._logo_movie = None
        self._setup_logo()

    def _logo_center_y(self):
        return SPLASH_H // 2

    def _setup_logo(self):
        from PyQt5.QtGui import QMovie
        logo_path = _find_splash_logo()
        if not logo_path:
            return
        if logo_path.lower().endswith(".gif"):
            movie = QMovie(logo_path)
            if not movie.isValid():
                self._draw_static_logo(logo_path)
                return
            movie.jumpToFrame(0)
            orig = movie.currentPixmap().size()
            if orig.width() > 0 and orig.height() > 0:
                scaled = orig.scaled(self.LOGO_MAX_W, self.LOGO_MAX_H, Qt.KeepAspectRatio)
            else:
                scaled = QSize(self.LOGO_MAX_W, self.LOGO_MAX_H)
            movie.setScaledSize(scaled)
            logo_x = (ORANGE_W - scaled.width()) // 2
            logo_y = self._logo_center_y() - scaled.height() // 2
            lbl = QLabel(self)
            lbl.setStyleSheet("background: transparent;")
            lbl.setFixedSize(scaled)
            lbl.move(logo_x, logo_y)
            lbl.setMovie(movie)
            movie.start()
            self._logo_label = lbl
            self._logo_movie = movie
        else:
            self._draw_static_logo(logo_path)

    def _draw_static_logo(self, path):
        pix = QPixmap(path)
        if pix.isNull():
            return
        pix = pix.scaled(self.LOGO_MAX_W, self.LOGO_MAX_H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_x = (ORANGE_W - pix.width()) // 2
        logo_y = self._logo_center_y() - pix.height() // 2
        lbl = QLabel(self)
        lbl.setStyleSheet("background: transparent;")
        lbl.setFixedSize(pix.width(), pix.height())
        lbl.move(logo_x, logo_y)
        lbl.setPixmap(pix)
        self._logo_label = lbl

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

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseDoubleClickEvent(self, event):
        event.accept()

    def drawContents(self, painter):
        w = SPLASH_W
        h = SPLASH_H
        right_x = ORANGE_W
        right_w = w - ORANGE_W
        pad = 28

        # Bottom row in the dark right column: status (left) + counter (right)
        row_y = h - 50
        row_h = 22

        # Mask the bottom row of the right column so we can repaint cleanly.
        painter.fillRect(right_x, row_y - 4, right_w, row_h + 8, QColor("#0a0a0a"))

        if self.is_error:
            painter.setPen(QColor(RED))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(right_x + pad, row_y, right_w - pad * 2, row_h,
                             Qt.AlignVCenter | Qt.AlignLeft, "ERROR")

            painter.setPen(QColor("#cccccc"))
            painter.setFont(QFont("Segoe UI", 8))
            err_first_line = (self.error_msg.split("\n") + [""])[0]
            painter.drawText(right_x + pad + 60, row_y, right_w - pad * 2 - 60, row_h,
                             Qt.AlignVCenter | Qt.AlignLeft, err_first_line)
            return

        # Animated status dot (left)
        dot_d = 7
        dot_x = right_x + pad
        dot_y = row_y + (row_h - dot_d) // 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ff6a00"))
        painter.drawEllipse(dot_x, dot_y, dot_d, dot_d)

        # Status text
        painter.setPen(QColor("#b3b3b8"))
        status_font = QFont("JetBrains Mono", 9)
        if not status_font.exactMatch():
            status_font = QFont("Consolas", 9)
        painter.setFont(status_font)
        painter.drawText(dot_x + dot_d + 10, row_y, right_w - pad * 2 - dot_d - 10, row_h,
                         Qt.AlignVCenter | Qt.AlignLeft, self.status_msg)

        # Counter "47 / 100" right-aligned
        counter_font = QFont("JetBrains Mono", 9, QFont.Bold)
        if not counter_font.exactMatch():
            counter_font = QFont("Consolas", 9, QFont.Bold)
        painter.setFont(counter_font)
        pct = max(0, min(100, int(self.progress)))
        num_text = f"{pct:02d}"
        # number in white, " / 100" muted
        fm = QFontMetrics(counter_font)
        suffix = " / 100"
        suffix_w = fm.horizontalAdvance(suffix)
        num_w = fm.horizontalAdvance(num_text)
        total_w = num_w + suffix_w
        cx_right = right_x + right_w - pad
        suffix_x = cx_right - suffix_w
        num_x = suffix_x - num_w
        painter.setPen(QColor("#666"))
        painter.drawText(suffix_x, row_y, suffix_w, row_h, Qt.AlignVCenter | Qt.AlignLeft, suffix)
        painter.setPen(QColor("#f4f4f6"))
        painter.drawText(num_x, row_y, num_w, row_h, Qt.AlignVCenter | Qt.AlignLeft, num_text)

        # Optional Roblox version, drawn small under "// LAUNCHER" notch on left block
        if self.roblox_version:
            painter.setPen(QColor(255, 255, 255, 160))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(16, h - 38, ORANGE_W - 32, 14,
                             Qt.AlignLeft | Qt.AlignVCenter, self.roblox_version)


def _find_splash_logo():
    logo_extensions = [".gif", ".png"]
    search_dirs = [
        APP_DIR,
        os.path.dirname(os.path.abspath(__file__)),
    ]
    if getattr(sys, 'frozen', False):
        search_dirs.append(sys._MEIPASS)
    for d in search_dirs:
        for ext in logo_extensions:
            candidate = os.path.join(d, f"splash_logo{ext}")
            if os.path.isfile(candidate):
                return candidate
    return None

_cached_splash_pixmap = None

def _load_roblox_font():
    """Locate Roblox2017.ttf (bundled or alongside the .exe) and register
    it with QFontDatabase. Returns the family name, or None if not found."""
    font_search_dirs = [
        APP_DIR,
        os.path.dirname(os.path.abspath(__file__)),
    ]
    if getattr(sys, 'frozen', False):
        font_search_dirs.append(sys._MEIPASS)
        font_search_dirs.append(os.path.dirname(os.path.abspath(sys.executable)))
    for fd in font_search_dirs:
        for fname in ("Roblox2017.ttf", "Roblox.ttf"):
            candidate = os.path.join(fd, fname)
            if os.path.isfile(candidate):
                font_id = QFontDatabase.addApplicationFont(candidate)
                if font_id >= 0:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        return families[0]
    return None


def _split_title(name):
    """Always render the LAST word on its own line (e.g. 'JAMES ROBLOX' →
    line1='JAMES', line2='ROBLOX'). Single-word names go on line 2 only."""
    parts = (name or "").split()
    if len(parts) >= 2:
        return " ".join(parts[:-1]), parts[-1]
    return "", (parts[0] if parts else "")


def _fit_font(font_family, text, max_w, start_size, min_size, weight=QFont.Bold, spacing=0):
    """Shrink font size until the text fits in max_w. Returns (QFont, QFontMetrics)."""
    size = start_size
    while size >= min_size:
        f = QFont(font_family, size, weight)
        if spacing:
            f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
        fm = QFontMetrics(f)
        if fm.horizontalAdvance(text) <= max_w:
            return f, fm
        size -= 1
    f = QFont(font_family, min_size, weight)
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f, QFontMetrics(f)


def create_splash_pixmap():
    """Render the Horizon design (50/50 split — orange color block left,
    dark info column right). The last word of APP_NAME is always rendered
    on its own line in the Roblox font, in orange."""
    global _cached_splash_pixmap
    if _cached_splash_pixmap is not None:
        return _cached_splash_pixmap

    w, h = SPLASH_W, SPLASH_H
    pix = QPixmap(w, h)
    pix.fill(QColor("#0a0a0a"))

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    # ---------- LEFT ORANGE BLOCK ----------
    orange_grad = QLinearGradient(0, 0, ORANGE_W, h)
    orange_grad.setColorAt(0.0, QColor("#ff8a3a"))
    orange_grad.setColorAt(1.0, QColor("#ee5a00"))
    p.fillRect(0, 0, ORANGE_W, h, orange_grad)

    # diagonal sheen
    sheen = QLinearGradient(0, 0, ORANGE_W, h)
    sheen.setColorAt(0.0, QColor(255, 255, 255, 25))
    sheen.setColorAt(0.55, QColor(255, 255, 255, 0))
    sheen.setColorAt(1.0, QColor(0, 0, 0, 30))
    p.fillRect(0, 0, ORANGE_W, h, sheen)

    # subtle inner shadow on right edge of orange block
    edge = QLinearGradient(ORANGE_W - 12, 0, ORANGE_W, 0)
    edge.setColorAt(0, QColor(0, 0, 0, 0))
    edge.setColorAt(1, QColor(0, 0, 0, 70))
    p.fillRect(ORANGE_W - 12, 0, 12, h, edge)

    # notches: top "DENFI" / bottom "// LAUNCHER"
    notch_font = QFont("JetBrains Mono", 8, QFont.Bold)
    if not notch_font.exactMatch():
        notch_font = QFont("Consolas", 8, QFont.Bold)
    notch_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
    p.setFont(notch_font)
    p.setPen(QColor(255, 255, 255, 200))
    p.drawText(20, 20, ORANGE_W - 40, 16, Qt.AlignLeft | Qt.AlignVCenter, "DENFI")
    p.setPen(QColor(255, 255, 255, 170))
    p.drawText(20, h - 28, ORANGE_W - 40, 16, Qt.AlignLeft | Qt.AlignVCenter, "// LAUNCHER")

    # ---------- RIGHT DARK BLOCK ----------
    right_x = ORANGE_W
    right_w = w - ORANGE_W
    pad = 28

    bg_grad = QLinearGradient(right_x, 0, right_x, h)
    bg_grad.setColorAt(0.0, QColor("#0e0e10"))
    bg_grad.setColorAt(1.0, QColor("#0a0a0a"))
    p.fillRect(right_x, 0, right_w, h, bg_grad)

    # very soft top-right glow
    glow = QRadialGradient(right_x + right_w - 60, 60, 220)
    glow.setColorAt(0, QColor(255, 106, 0, 28))
    glow.setColorAt(1, QColor(0, 0, 0, 0))
    p.fillRect(right_x, 0, right_w, h, glow)

    # outer 1px frame around the whole splash
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#1c1c1c"), 1))
    p.drawRect(0, 0, w - 1, h - 1)

    # ---------- TOP ROW (right): "PREMIUM EDITION" + version pill ----------
    top_y = 28
    pe_font = QFont("Segoe UI", 9, QFont.Bold)
    pe_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
    p.setFont(pe_font)
    p.setPen(QColor("#f4f4f6"))
    p.drawText(right_x + pad, top_y, right_w - pad * 2, 16,
               Qt.AlignLeft | Qt.AlignVCenter, "PREMIUM EDITION")

    # version pill (right)
    ver_text = f"v{APP_VERSION}"
    pill_font = QFont("JetBrains Mono", 8)
    if not pill_font.exactMatch():
        pill_font = QFont("Consolas", 8)
    p.setFont(pill_font)
    fm = QFontMetrics(pill_font)
    pill_pad_x = 10
    pill_h = 18
    pill_w = fm.horizontalAdvance(ver_text) + pill_pad_x * 2
    pill_x = right_x + right_w - pad - pill_w
    pill_y = top_y - 1
    p.setPen(QPen(QColor(255, 255, 255, 35), 1))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, pill_h // 2, pill_h // 2)
    p.setPen(QColor(255, 255, 255, 140))
    p.drawText(pill_x, pill_y, pill_w, pill_h, Qt.AlignCenter, ver_text)

    # ---------- EYEBROW: // NOW LOADING ----------
    eyebrow_font = QFont("JetBrains Mono", 9, QFont.Bold)
    if not eyebrow_font.exactMatch():
        eyebrow_font = QFont("Consolas", 9, QFont.Bold)
    eyebrow_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
    p.setFont(eyebrow_font)
    p.setPen(QColor("#ff6a00"))
    eyebrow_y = 130
    p.drawText(right_x + pad, eyebrow_y, right_w - pad * 2, 16,
               Qt.AlignLeft | Qt.AlignVCenter, "// NOW LOADING")

    # ---------- TITLE (two lines, last word in Roblox font + orange) ----------
    roblox_family = _load_roblox_font()
    line1, line2 = _split_title(APP_NAME)
    max_title_w = right_w - pad * 2

    # Line 1: clean modern condensed sans-serif, white. Prefer Bahnschrift
    # (ships with Windows 10+) for a tall, refined display look that pairs
    # nicely with the chunky Roblox letterform on line 2. Falls back through
    # Segoe UI Semibold for older systems / non-Windows.
    title1_family = "Bahnschrift"
    f_probe = QFont(title1_family)
    if not f_probe.exactMatch():
        title1_family = "Segoe UI Semibold"
        if not QFont(title1_family).exactMatch():
            title1_family = "Segoe UI"

    if line1:
        f1, fm1 = _fit_font(title1_family, line1, max_title_w,
                            start_size=32, min_size=16, weight=QFont.DemiBold,
                            spacing=1)
        p.setFont(f1)
        p.setPen(QColor("#f4f4f6"))
        line1_y = eyebrow_y + 28
        p.drawText(right_x + pad, line1_y, max_title_w, fm1.height() + 4,
                   Qt.AlignLeft | Qt.AlignTop, line1)
        line2_top = line1_y + fm1.height() + 2
    else:
        line2_top = eyebrow_y + 28

    # Line 2: Roblox font, orange (always, even if it isn't literally "ROBLOX")
    if line2:
        family = roblox_family if roblox_family else "Segoe UI"
        f2, fm2 = _fit_font(family, line2, max_title_w,
                            start_size=32, min_size=18, weight=QFont.Bold)
        p.setFont(f2)
        p.setPen(QColor("#ff6a00"))
        p.drawText(right_x + pad, line2_top, max_title_w, fm2.height() + 8,
                   Qt.AlignLeft | Qt.AlignTop, line2)

    # ---------- SUBTITLE ----------
    sub_font = QFont("Segoe UI", 9)
    p.setFont(sub_font)
    p.setPen(QColor(255, 255, 255, 120))
    sub_y = h - 90
    p.drawText(right_x + pad, sub_y, max_title_w, 18,
               Qt.AlignLeft | Qt.AlignVCenter, "Built for performance. Designed to disappear.")

    p.end()
    _cached_splash_pixmap = pix
    return pix


def get_license_file():
    return os.path.join(APP_DIR, ".license_key")


def _get_stable_xor_key():
    seed = "DENFI_STABLE_LICENSE_FILE_KEY_V1"
    return hashlib.md5(seed.encode("utf-8")).digest()


def _get_file_xor_key():
    seed = APP_NAME + "LIC" + str(len(_LICENSE_SECRET_XOR))
    return hashlib.md5(seed.encode("utf-8")).digest()


def _xor_with(raw_bytes, xor_key):
    return bytes([raw_bytes[i] ^ xor_key[i % len(xor_key)] for i in range(len(raw_bytes))])


def _encrypt_key(plaintext):
    xor_key = _get_stable_xor_key()
    return _xor_with(plaintext.encode("utf-8"), xor_key)


def _try_decode(raw_bytes, xor_key):
    import re
    decrypted = _xor_with(raw_bytes, xor_key)
    try:
        result = decrypted.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""
    if re.match(r'^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$', result):
        return result
    return ""


def _decrypt_key(raw_bytes):
    import re
    try:
        text = raw_bytes.decode("utf-8", errors="replace").strip()
    except Exception:
        text = ""
    if re.match(r'^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$', text):
        return text
    for xor_key in (_get_stable_xor_key(), _get_file_xor_key()):
        result = _try_decode(raw_bytes, xor_key)
        if result:
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
                        _hide_file_windows(path)
                        return key
        except Exception:
            pass

    return ""


def _hide_file_windows(path):
    """Set the Windows Hidden + System attribute on a file so it doesn't
    show up in Explorer with default settings. Silent no-op on non-Windows
    or on any failure (the file is still usable either way)."""
    try:
        if sys.platform != "win32":
            return
        import ctypes
        FILE_ATTRIBUTE_HIDDEN = 0x02
        FILE_ATTRIBUTE_SYSTEM = 0x04
        ctypes.windll.kernel32.SetFileAttributesW(
            ctypes.c_wchar_p(path),
            FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM,
        )
    except Exception:
        pass


def save_license_key(key):
    if EMBEDDED_LICENSE_KEY:
        return True

    path = get_license_file()
    try:
        encrypted = _encrypt_key(key)
        with open(path, "wb") as f:
            f.write(encrypted)
        _hide_file_windows(path)
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
        import urllib.request, urllib.error
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
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as he:
            body_text = ""
            try:
                body_text = he.read().decode('utf-8', errors='replace')
                result = json.loads(body_text)
            except Exception:
                hint = ""
                if he.code == 403:
                    hint = " (check that your PC clock is set correctly)"
                return {"valid": False, "error": f"Server error {he.code}{hint}"}
            data = result.get("data", {}) if isinstance(result, dict) else {}
            err_msg = data.get("error") if isinstance(data, dict) else None
            if not err_msg:
                err_msg = f"Server error {he.code}"
            if he.code == 403 and "expired" in (err_msg or "").lower():
                err_msg += " — please correct your PC clock"
            return {"valid": False, "error": err_msg}

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
        body = {"key": key, "version": APP_VERSION, "app_name": APP_NAME, "config_hash": CONFIG_HASH, "config_id": CONFIG_ID}
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
            "app_name": APP_NAME,
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
    """Download the update in a background thread so the Qt event loop on the
    main thread keeps running. This is what stops the splash GIF from freezing
    while the .exe is being pulled down."""
    if not LICENSE_SERVER_URL:
        return None

    import threading
    import time as _time
    import urllib.request
    try:
        from PyQt5.QtWidgets import QApplication
    except Exception:
        QApplication = None  # type: ignore

    token = update_info.get("download_token", "")
    if not token:
        return None
    version = update_info.get("latest_version", "")
    total_size = update_info.get("file_size", 0)
    expected_hash = update_info.get("sha256", "")
    url = LICENSE_SERVER_URL.rstrip("/") + f"/api/download_update/{token}"

    state = {
        "downloaded": 0,
        "total": total_size,
        "pct": 0,
        "result": None,
        "error": None,
        "done": False,
        "last_reported_remote": 0,
    }

    def worker():
        try:
            req = urllib.request.Request(url)
            _report_download_progress(0, version, "downloading")
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = bytearray()
                # Smaller block size + thread isolation = the UI stays buttery
                # smooth and we can still report fine-grained progress.
                block_size = 16384
                downloaded = 0
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    data.extend(chunk)
                    downloaded += len(chunk)
                    state["downloaded"] = downloaded
                    if total_size > 0:
                        pct = min(100, int(downloaded * 100 / total_size))
                        state["pct"] = pct
                        if pct - state["last_reported_remote"] >= 5:
                            state["last_reported_remote"] = pct
                            try:
                                _report_download_progress(pct, version, "downloading")
                            except Exception:
                                pass

            if len(data) < 1024:
                _report_download_progress(0, version, "failed")
                state["error"] = "short_response"
                return

            if expected_hash:
                actual_hash = hashlib.sha256(data).hexdigest()
                if actual_hash != expected_hash:
                    _report_download_progress(0, version, "failed")
                    state["error"] = "hash_mismatch"
                    return

            if total_size > 0 and len(data) != total_size:
                _report_download_progress(0, version, "failed")
                state["error"] = "size_mismatch"
                return

            temp_dir = os.path.join(APP_DIR, "_update")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f"update_{version or 'new'}.exe")
            with open(temp_path, "wb") as f:
                f.write(data)
            _report_download_progress(100, version, "completed")
            state["result"] = temp_path
        except Exception as e:
            state["error"] = e
            try:
                _report_download_progress(0, version, "failed")
            except Exception:
                pass
        finally:
            state["done"] = True

    t = threading.Thread(target=worker, name="UpdateDownloader", daemon=True)
    t.start()

    app = QApplication.instance() if QApplication is not None else None
    last_dispatched_pct = -1
    last_dispatched_dl = -1
    while not state["done"]:
        if app is not None:
            # Pump Qt events so QMovie animates and the splash repaints.
            app.processEvents()
        pct = state["pct"]
        dl = state["downloaded"]
        if progress_callback and (pct != last_dispatched_pct or dl - last_dispatched_dl >= 65536):
            last_dispatched_pct = pct
            last_dispatched_dl = dl
            try:
                progress_callback(pct, dl, state["total"])
            except Exception:
                pass
        _time.sleep(0.03)

    # Final flush of UI + progress.
    if app is not None:
        app.processEvents()
    if progress_callback:
        try:
            progress_callback(state["pct"], state["downloaded"], state["total"])
        except Exception:
            pass

    return state["result"]


def apply_update_and_restart(new_exe_path):
    if sys.platform != "win32":
        return False
    if not getattr(sys, 'frozen', False):
        return False

    current_exe = sys.executable
    backup_path = current_exe + ".bak"
    staging_path = current_exe + ".new"

    try:
        update_state_heartbeat(phase="applying")

        for p in (backup_path, staging_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        shutil.copy2(new_exe_path, staging_path)

        os.replace(current_exe, backup_path)
        try:
            os.replace(staging_path, current_exe)
        except Exception:
            if os.path.exists(backup_path) and not os.path.exists(current_exe):
                try:
                    os.replace(backup_path, current_exe)
                except Exception:
                    pass
            raise

        try:
            os.remove(new_exe_path)
            update_dir = os.path.dirname(new_exe_path)
            if os.path.isdir(update_dir) and not os.listdir(update_dir):
                os.rmdir(update_dir)
        except Exception:
            pass

        update_state_heartbeat(phase="restarting")

        child_env = os.environ.copy()
        for _pyi_var in (
            "_MEIPASS2",
            "_PYI_APPLICATION_HOME_DIR",
            "_PYI_ARCHIVE_FILE",
            "_PYI_PARENT_PROCESS_LEVEL",
            "_PYI_SPLASH_IPC",
            "PYI_SPLASH_IPC",
        ):
            child_env.pop(_pyi_var, None)
        child_env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"

        try:
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_BREAKAWAY_FROM_JOB = 0x01000000
            flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB
            subprocess.Popen(
                [current_exe, "--post-update-restart"],
                creationflags=flags,
                close_fds=True,
                cwd=os.path.dirname(current_exe) or None,
                env=child_env,
            )
        except Exception:
            try:
                subprocess.Popen(
                    [current_exe, "--post-update-restart"],
                    close_fds=True,
                    env=child_env,
                )
            except Exception:
                pass

        return True
    except Exception:
        try:
            if os.path.exists(staging_path):
                os.remove(staging_path)
        except Exception:
            pass
        try:
            if os.path.exists(backup_path) and not os.path.exists(current_exe):
                os.replace(backup_path, current_exe)
        except Exception:
            pass
        return False


def _is_suspended_error(error_msg):
    return "suspended" in error_msg.lower()


def _is_fatal_license_error(error_msg):
    fatal_phrases = ["expired", "revoked", "deleted", "not found"]
    lower = error_msg.lower()
    return any(phrase in lower for phrase in fatal_phrases)


class UpdateProgressDialog(QDialog):
    """Horizon-style update dialog. Same 680x380 50/50 split as the splash:
    orange color block on the left (with "// UPDATING" notch) and a dark
    column on the right that holds the version pill, two-line title, the
    orange progress bar, the byte counter and a small status line."""

    def __init__(self, version="", total_bytes=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Updating")
        self.setFixedSize(SPLASH_W, SPLASH_H)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._total_bytes = total_bytes or 0
        self._version = version or "?"
        self._downloaded = 0
        self._pct = 0
        self._status = "Preparing download..."
        self._phase = "downloading"

        right_x = ORANGE_W
        right_w = SPLASH_W - ORANGE_W
        pad = 28

        bar_w = right_w - pad * 2
        bar_h = 14
        bar_x = right_x + pad
        bar_y = 250

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setGeometry(bar_x, bar_y, bar_w, bar_h)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background: rgba(255,255,255,18); "
            "border: 1px solid rgba(255,255,255,30); border-radius: 7px; }"
            "QProgressBar::chunk { background-color: #ff6a00; border-radius: 6px; }"
        )

    # ---- public API (same shape as before) -----------------------------

    def set_download_progress(self, downloaded_bytes, total_bytes):
        if total_bytes and total_bytes > 0:
            self._total_bytes = total_bytes
        self._downloaded = downloaded_bytes or 0
        total = self._total_bytes if self._total_bytes else (total_bytes or 0)
        if total > 0:
            self._pct = max(0, min(100, int(self._downloaded * 100 / total)))
        else:
            self._pct = 0
        self.progress_bar.setValue(self._pct)
        self._status = f"// downloading update  {self._pct:>3}%"
        self.update()

    def set_phase(self, phase, version=None):
        if version:
            self._version = version
        self._phase = phase
        if phase == "installing":
            self._pct = 100
            self.progress_bar.setValue(100)
            self._status = f"// installing version {self._version}"
        elif phase == "restarting":
            self._pct = 100
            self.progress_bar.setValue(100)
            self._status = f"// restarting into version {self._version}"
        elif phase == "failed":
            self._status = "// update failed — continuing"
        self.update()

    def closeEvent(self, event):
        event.ignore()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape,):
            event.ignore()
            return
        super().keyPressEvent(event)

    # ---- painting ------------------------------------------------------

    def paintEvent(self, event):
        w, h = SPLASH_W, SPLASH_H
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        # ---------- LEFT ORANGE BLOCK ----------
        orange_grad = QLinearGradient(0, 0, ORANGE_W, h)
        orange_grad.setColorAt(0.0, QColor("#ff8a3a"))
        orange_grad.setColorAt(1.0, QColor("#ee5a00"))
        p.fillRect(0, 0, ORANGE_W, h, orange_grad)

        sheen = QLinearGradient(0, 0, ORANGE_W, h)
        sheen.setColorAt(0.0, QColor(255, 255, 255, 25))
        sheen.setColorAt(0.55, QColor(255, 255, 255, 0))
        sheen.setColorAt(1.0, QColor(0, 0, 0, 30))
        p.fillRect(0, 0, ORANGE_W, h, sheen)

        edge = QLinearGradient(ORANGE_W - 12, 0, ORANGE_W, 0)
        edge.setColorAt(0, QColor(0, 0, 0, 0))
        edge.setColorAt(1, QColor(0, 0, 0, 70))
        p.fillRect(ORANGE_W - 12, 0, 12, h, edge)

        # large "OTA" wordmark on the orange block (decorative)
        ota_font = QFont("Bahnschrift", 96, QFont.Black)
        if not ota_font.exactMatch():
            ota_font = QFont("Segoe UI Black", 96, QFont.Black)
        ota_font.setLetterSpacing(QFont.AbsoluteSpacing, 4)
        p.setFont(ota_font)
        p.setPen(QColor(255, 255, 255, 55))
        p.drawText(0, 0, ORANGE_W, h, Qt.AlignCenter, "OTA")

        # notches: top "DENFI" / bottom "// UPDATER"
        notch_font = QFont("JetBrains Mono", 8, QFont.Bold)
        if not notch_font.exactMatch():
            notch_font = QFont("Consolas", 8, QFont.Bold)
        notch_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(notch_font)
        p.setPen(QColor(255, 255, 255, 200))
        p.drawText(20, 20, ORANGE_W - 40, 16, Qt.AlignLeft | Qt.AlignVCenter, "DENFI")
        p.setPen(QColor(255, 255, 255, 170))
        p.drawText(20, h - 28, ORANGE_W - 40, 16, Qt.AlignLeft | Qt.AlignVCenter, "// UPDATER")

        # ---------- RIGHT DARK BLOCK ----------
        right_x = ORANGE_W
        right_w = SPLASH_W - ORANGE_W
        pad = 28

        bg_grad = QLinearGradient(right_x, 0, right_x, h)
        bg_grad.setColorAt(0.0, QColor("#0e0e10"))
        bg_grad.setColorAt(1.0, QColor("#0a0a0a"))
        p.fillRect(right_x, 0, right_w, h, bg_grad)

        glow = QRadialGradient(right_x + right_w - 60, 60, 220)
        glow.setColorAt(0, QColor(255, 106, 0, 28))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(right_x, 0, right_w, h, glow)

        # outer 1px frame
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#1c1c1c"), 1))
        p.drawRect(0, 0, w - 1, h - 1)

        # ---------- TOP ROW: "PREMIUM EDITION" + version pill ----------
        top_y = 28
        pe_font = QFont("Segoe UI", 9, QFont.Bold)
        pe_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(pe_font)
        p.setPen(QColor("#f4f4f6"))
        p.drawText(right_x + pad, top_y, right_w - pad * 2, 16,
                   Qt.AlignLeft | Qt.AlignVCenter, "PREMIUM EDITION")

        ver_text = f"v{self._version}"
        pill_font = QFont("JetBrains Mono", 8)
        if not pill_font.exactMatch():
            pill_font = QFont("Consolas", 8)
        p.setFont(pill_font)
        fm = QFontMetrics(pill_font)
        pill_pad_x = 10
        pill_h = 18
        pill_w = fm.horizontalAdvance(ver_text) + pill_pad_x * 2
        pill_x = right_x + right_w - pad - pill_w
        pill_y = top_y - 1
        p.setPen(QPen(QColor("#ff6a00"), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, pill_h // 2, pill_h // 2)
        p.setPen(QColor("#ff6a00"))
        p.drawText(pill_x, pill_y, pill_w, pill_h, Qt.AlignCenter, ver_text)

        # ---------- EYEBROW: // UPDATING ----------
        eyebrow_font = QFont("JetBrains Mono", 9, QFont.Bold)
        if not eyebrow_font.exactMatch():
            eyebrow_font = QFont("Consolas", 9, QFont.Bold)
        eyebrow_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(eyebrow_font)
        p.setPen(QColor("#ff6a00"))
        eyebrow_y = 92
        p.drawText(right_x + pad, eyebrow_y, right_w - pad * 2, 16,
                   Qt.AlignLeft | Qt.AlignVCenter, "// UPDATING")

        # ---------- TITLE (two lines, last word in Roblox font + orange) ----
        roblox_family = _load_roblox_font()
        line1, line2 = _split_title(APP_NAME)
        max_title_w = right_w - pad * 2

        title1_family = "Bahnschrift"
        if not QFont(title1_family).exactMatch():
            title1_family = "Segoe UI Semibold"
            if not QFont(title1_family).exactMatch():
                title1_family = "Segoe UI"

        if line1:
            f1, fm1 = _fit_font(title1_family, line1, max_title_w,
                                start_size=28, min_size=14, weight=QFont.DemiBold,
                                spacing=1)
            p.setFont(f1)
            p.setPen(QColor("#f4f4f6"))
            line1_y = eyebrow_y + 26
            p.drawText(right_x + pad, line1_y, max_title_w, fm1.height() + 4,
                       Qt.AlignLeft | Qt.AlignTop, line1)
            line2_top = line1_y + fm1.height() + 2
        else:
            line2_top = eyebrow_y + 26

        if line2:
            family = roblox_family if roblox_family else "Segoe UI"
            f2, fm2 = _fit_font(family, line2, max_title_w,
                                start_size=28, min_size=16, weight=QFont.Bold)
            p.setFont(f2)
            p.setPen(QColor("#ff6a00"))
            p.drawText(right_x + pad, line2_top, max_title_w, fm2.height() + 8,
                       Qt.AlignLeft | Qt.AlignTop, line2)

        # ---------- BYTE COUNTER (right-aligned, above the bar) ----------
        total_mb = self._total_bytes / 1024 / 1024 if self._total_bytes else 0
        dl_mb = self._downloaded / 1024 / 1024
        if total_mb > 0:
            counter_text = f"{dl_mb:>5.1f} / {total_mb:.1f} MB"
        else:
            counter_text = f"{dl_mb:.1f} MB"

        counter_font = QFont("JetBrains Mono", 9)
        if not counter_font.exactMatch():
            counter_font = QFont("Consolas", 9)
        p.setFont(counter_font)
        p.setPen(QColor(255, 255, 255, 200))
        p.drawText(right_x + pad, 228, right_w - pad * 2, 16,
                   Qt.AlignRight | Qt.AlignVCenter, counter_text)

        pct_font = QFont("JetBrains Mono", 9, QFont.Bold)
        if not pct_font.exactMatch():
            pct_font = QFont("Consolas", 9, QFont.Bold)
        p.setFont(pct_font)
        p.setPen(QColor("#ff6a00"))
        p.drawText(right_x + pad, 228, right_w - pad * 2, 16,
                   Qt.AlignLeft | Qt.AlignVCenter, f"{self._pct:>3}%")

        # ---------- STATUS LINE (below the bar) ----------
        status_font = QFont("JetBrains Mono", 9)
        if not status_font.exactMatch():
            status_font = QFont("Consolas", 9)
        p.setFont(status_font)
        if self._phase == "failed":
            p.setPen(QColor("#ff6a6a"))
        else:
            p.setPen(QColor(255, 255, 255, 150))
        p.drawText(right_x + pad, 286, right_w - pad * 2, 16,
                   Qt.AlignLeft | Qt.AlignVCenter, self._status)

        # ---------- SUBTITLE / DON'T CLOSE WARNING ----------
        sub_font = QFont("Segoe UI", 9)
        p.setFont(sub_font)
        p.setPen(QColor(255, 187, 51, 220))
        sub_y = h - 50
        p.drawText(right_x + pad, sub_y, max_title_w, 18,
                   Qt.AlignLeft | Qt.AlignVCenter,
                   "Update in progress — please don't close this window.")

        p.end()


class UpdateInstalledDialog(QDialog):
    def __init__(self, version="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Installed")
        self.setFixedSize(400, 220)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.setStyleSheet("""
            QDialog { background: #1c1c26; border: 1px solid #2a2a38; border-radius: 10px; }
            QLabel { color: #e8e8ef; background: transparent; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(10)

        icon_label = QLabel("\u2714")
        icon_label.setFont(QFont("Segoe UI", 28))
        icon_label.setStyleSheet("color: #ff6a00;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        title = QLabel("Update Installed")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #ff6a00;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        msg = QLabel(f"Version {version} installed successfully!\nPlease reopen the app to use the new version.")
        msg.setFont(QFont("Segoe UI", 10))
        msg.setStyleSheet("color: #b0b0c0;")
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        layout.addSpacing(8)

        ok_btn = QPushButton("OK")
        ok_btn.setFixedHeight(36)
        ok_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        ok_btn.setStyleSheet("""
            QPushButton { background: #ff6a00; color: white; border: none; border-radius: 6px; padding: 8px 32px; }
            QPushButton:hover { background: #ff8c33; }
        """)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)


class WarningDialog(QDialog):
    def __init__(self, title_text="Warning", message="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title_text)
        self.setFixedSize(420, 200)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.setStyleSheet("""
            QDialog { background: #1c1c26; border: 1px solid #2a2a38; border-radius: 10px; }
            QLabel { color: #e8e8ef; background: transparent; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #ffbb33;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        msg_label = QLabel(message)
        msg_label.setFont(QFont("Segoe UI", 10))
        msg_label.setStyleSheet("color: #b0b0c0;")
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        layout.addSpacing(6)

        ok_btn = QPushButton("OK")
        ok_btn.setFixedHeight(34)
        ok_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        ok_btn.setStyleSheet("""
            QPushButton { background: #ff6a00; color: white; border: none; border-radius: 6px; padding: 8px 32px; }
            QPushButton:hover { background: #ff8c33; }
        """)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)


class LicenseDialog(QDialog):
    def __init__(self, parent=None, error_msg=""):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - License")
        self.setFixedSize(420, 260)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.result_key = ""

        self.setStyleSheet(f"""
            QDialog {{ background: #1c1c26; border: 1px solid #2a2a38; border-radius: 10px; }}
            QLabel {{ color: #e8e8ef; background: transparent; }}
            QLineEdit {{
                background: #16161e; border: 1px solid #333345; border-radius: 6px;
                color: #ff8c33; padding: 10px 12px; font-size: 14px;
                font-family: Consolas, monospace; letter-spacing: 1px;
            }}
            QLineEdit:focus {{ border-color: #ff6a00; }}
            QPushButton {{
                background: #ff6a00; color: white; border: none; border-radius: 6px;
                padding: 10px 24px; font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background: #ff8c33; }}
            QPushButton:disabled {{ background: #2a2a38; color: #6a6a80; }}
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
        subtitle.setStyleSheet("color: #7a7a90;")
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
        quit_btn.setStyleSheet("background: #222230; color: #9a9ab0;")
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
        self.status_label.setStyleSheet("color: #9a9ab0;")
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
        self.setStyleSheet("background: #1c1c26; border: 1px solid #2a2a38; border-radius: 10px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        title = QLabel(APP_NAME)
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #ee5555;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        msg = QLabel(reason)
        msg.setFont(QFont("Segoe UI", 11))
        msg.setStyleSheet("color: #b0b0c0;")
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        quit_btn = QPushButton("Close")
        quit_btn.setStyleSheet("""
            QPushButton { background: #ee5555; color: white; border: none;
                         border-radius: 6px; padding: 10px 24px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #ff7777; }
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
                warn_dlg = WarningDialog(
                    title_text="Warning",
                    message="License activated but could not save the key file.\n\n"
                            "You may be asked to enter the key again next time.\n\n"
                            "To fix this, make sure the folder containing "
                            f"{os.path.basename(sys.executable)} is writable."
                )
                warn_dlg.exec_()
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

    recover_from_interrupted_update()

    is_post_update_restart = "--post-update-restart" in sys.argv

    if is_post_update_restart:
        got_mutex = acquire_singleton_mutex_with_retry(timeout_s=10.0)
        if got_mutex:
            clear_update_state()
    else:
        got_mutex = acquire_singleton_mutex()

    if not got_mutex:
        state = read_update_state()
        if state and not is_update_state_stale(state):
            ver = state.get("target_version") or ""
            if ver:
                msg = f"Update to v{ver} in progress\nPlease wait..."
            else:
                msg = "Update in progress\nPlease wait..."
        else:
            msg = "Launcher is already running"

        splash_pix = create_splash_pixmap()
        splash = SplashScreen(splash_pix)
        splash.set_progress(100, msg)
        splash.show()
        app.processEvents()
        QTimer.singleShot(2500, app.quit)
        app.exec_()
        sys.exit(0)

    splash_pix = create_splash_pixmap()
    splash = SplashScreen(splash_pix)
    splash.set_progress(0, "Starting...")
    splash.show()
    app.processEvents()

    if not check_license_or_prompt(app, splash):
        release_singleton_mutex()
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

            update_dialog = UpdateProgressDialog(version=new_version, total_bytes=file_size)
            splash.hide()
            update_dialog.show()
            app.processEvents()

            def on_download_progress(pct, downloaded, total):
                update_dialog.set_download_progress(downloaded, total)
                dl_mb = downloaded / 1024 / 1024
                splash.set_progress(8 + int(pct * 0.85), f"Downloading v{new_version}... {dl_mb:.1f}/{size_mb:.1f} MB")
                app.processEvents()

            write_update_state("downloading", new_version)
            start_update_heartbeat()
            handing_off_to_child = False
            try:
                splash.set_progress(8, f"Update v{new_version} found ({size_mb:.1f} MB)...")
                app.processEvents()

                new_exe = download_update(update_info, on_download_progress)
                if new_exe:
                    update_dialog.set_phase("installing", new_version)
                    app.processEvents()
                    splash.set_progress(95, f"Installing v{new_version}...")
                    app.processEvents()
                    if apply_update_and_restart(new_exe):
                        handing_off_to_child = True
                        update_dialog.set_phase("restarting", new_version)
                        splash.set_progress(100, f"Restarting into v{new_version}...")
                        app.processEvents()
                        QTimer.singleShot(800, app.quit)
                        app.exec_()
                        sys.exit(0)
                    else:
                        update_dialog.set_phase("failed")
                        app.processEvents()
                        splash.set_progress(8, "Update failed, continuing...")
                        app.processEvents()
                else:
                    update_dialog.set_phase("failed")
                    app.processEvents()
            finally:
                stop_update_heartbeat()
                if not handing_off_to_child:
                    clear_update_state()
                    try:
                        update_dialog.hide()
                        update_dialog.deleteLater()
                    except Exception:
                        pass
                    splash.show()
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
                _roblox_popen_kwargs = {
                    "cwd": paths["roblox"],
                    "close_fds": True,
                }
                if sys.platform == "win32":
                    _DETACHED_PROCESS = 0x00000008
                    _CREATE_NEW_PROCESS_GROUP = 0x00000200
                    _CREATE_BREAKAWAY_FROM_JOB = 0x01000000
                    _roblox_popen_kwargs["creationflags"] = (
                        _DETACHED_PROCESS
                        | _CREATE_NEW_PROCESS_GROUP
                        | _CREATE_BREAKAWAY_FROM_JOB
                    )
                process = subprocess.Popen([exe_path], **_roblox_popen_kwargs)
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

            release_singleton_mutex()

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
