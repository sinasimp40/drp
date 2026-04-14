import sys
import os
import subprocess
import datetime
import shutil
import ctypes

from PyQt5.QtWidgets import (
    QApplication, QSplashScreen
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (
    QColor, QPainter, QPixmap, QIcon, QFont, QLinearGradient,
    QRadialGradient, QPen, QPainterPath, QBrush
)

APP_NAME = "DENFI ROBLOX"
APP_VERSION = "1.0.0"
HARDCODED_PATH = ""

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
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            count += 1
        elif os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            count += 1

    for old_item in old_files - new_files:
        old_path = os.path.join(roblox_dir, old_item)
        if os.path.isfile(old_path):
            os.remove(old_path)
            removed += 1
        elif os.path.isdir(old_path):
            shutil.rmtree(old_path)
            removed += 1

    return count, removed


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
        elif item_lower == "appstorage.json":
            should_delete = True
        if should_delete:
            try:
                os.remove(os.path.join(local_storage, item))
                cleared += 1
            except Exception:
                pass
    return f"cleared_{cleared}"


def is_roblox_running():
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe", "/NH"],
            capture_output=True, text=True,
            creationflags=0x08000000
        )
        return "RobloxPlayerBeta.exe" in result.stdout
    except Exception:
        return False


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


def create_splash_pixmap():
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
    return splash_pix


def main():
    if sys.platform != "win32":
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    icon_path = os.path.join(APP_DIR, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    paths = get_paths()

    splash_pix = create_splash_pixmap()
    splash = SplashScreen(splash_pix)
    splash.show()
    app.processEvents()

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
                    count, removed = sync_files(sync_state["source"], paths["roblox"])
                    log_lines.append(f"Synced {count} files, cleaned {removed} old files")
                    splash.set_progress(70, f"Synced {count} files!")
                    app.processEvents()
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

            splash.set_progress(85, "Launching Roblox...")
            app.processEvents()

            try:
                process = subprocess.Popen(
                    [exe_path],
                    cwd=paths["roblox"],
                )
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

            app.setQuitOnLastWindowClosed(False)

            def hide_and_watch():
                splash.hide()
                initial_check_done = [False]

                def check_roblox():
                    if not initial_check_done[0]:
                        if is_roblox_running():
                            initial_check_done[0] = True
                        return
                    if not is_roblox_running():
                        clear_roblox_login()
                        app.quit()

                timer = QTimer()
                timer.timeout.connect(check_roblox)
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
