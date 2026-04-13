import sys
import os
import json
import subprocess
import datetime
import shutil
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QSplashScreen
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPixmap, QIcon, QFont, QLinearGradient

APP_NAME = "DENFI ROBLOX"
APP_VERSION = "1.0.0"

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()
ROBLOX_DIR = os.path.join(APP_DIR, "RobloxFiles")
CACHE_DIR = os.path.join(APP_DIR, "Cache")
LOGS_DIR = os.path.join(APP_DIR, "Logs")
CONFIG_FILE = os.path.join(APP_DIR, "denfi_config.json")

BG = "#0a0a0a"
ORANGE = "#ff6a00"
ORANGE_LIGHT = "#ff8c33"
ORANGE_DARK = "#cc5500"
TEXT_WHITE = "#f0f0f0"
TEXT_DIM = "#555555"
GREEN = "#00cc66"
RED = "#ff3333"


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def write_log(message):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, f"launch_{timestamp}.log")
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
        return None, None
    local_app = os.environ.get("LOCALAPPDATA", "")
    versions_path = os.path.join(local_app, "Roblox", "Versions")
    if not os.path.isdir(versions_path):
        return None, None
    versions = []
    for item in os.listdir(versions_path):
        full = os.path.join(versions_path, item)
        if os.path.isdir(full) and os.path.isfile(os.path.join(full, "RobloxPlayerBeta.exe")):
            versions.append(full)
    if not versions:
        return None, None
    versions.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    latest = versions[0]
    fingerprint = get_folder_fingerprint(latest)
    return latest, fingerprint


def sync_files(source_dir, config):
    count = 0
    removed = 0

    old_files = set()
    if os.path.isdir(ROBLOX_DIR):
        for item in os.listdir(ROBLOX_DIR):
            if item != "PLACE_ROBLOX_HERE.txt":
                old_files.add(item)

    new_files = set()
    for item in os.listdir(source_dir):
        src = os.path.join(source_dir, item)
        dst = os.path.join(ROBLOX_DIR, item)
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
        old_path = os.path.join(ROBLOX_DIR, old_item)
        if os.path.isfile(old_path):
            os.remove(old_path)
            removed += 1
        elif os.path.isdir(old_path):
            shutil.rmtree(old_path)
            removed += 1

    return count, removed


class SplashScreen(QSplashScreen):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen)
        self.progress = 0
        self.status_msg = "Initializing..."

    def set_progress(self, value, msg=""):
        self.progress = value
        if msg:
            self.status_msg = msg
        self.repaint()

    def drawContents(self, painter):
        painter.fillRect(100, 290, int(300 * self.progress / 100), 4, QColor(ORANGE))

        painter.setPen(QColor(TEXT_DIM))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(0, 255, 500, 20, Qt.AlignCenter, self.status_msg)


def create_splash_pixmap():
    splash_pix = QPixmap(500, 320)
    splash_pix.fill(QColor(BG))

    painter = QPainter(splash_pix)
    painter.setRenderHint(QPainter.Antialiasing)

    grad = QLinearGradient(0, 0, 500, 320)
    grad.setColorAt(0, QColor("#0a0a0a"))
    grad.setColorAt(0.5, QColor("#111111"))
    grad.setColorAt(1, QColor("#0a0a0a"))
    painter.fillRect(0, 0, 500, 320, grad)

    painter.setPen(Qt.NoPen)
    block_size = 16
    gap = 4
    start_x = 185
    start_y = 40
    for row in range(3):
        for col in range(3):
            x = start_x + col * (block_size + gap)
            y = start_y + row * (block_size + gap)
            if row == 2 and col == 2:
                painter.setBrush(QColor(ORANGE_DARK))
            else:
                painter.setBrush(QColor(ORANGE))
            painter.drawRoundedRect(x, y, block_size, block_size, 3, 3)

    painter.setPen(QColor(ORANGE))
    font = QFont("Segoe UI", 34, QFont.Bold)
    font.setLetterSpacing(QFont.AbsoluteSpacing, 4)
    painter.setFont(font)
    painter.drawText(0, 120, 500, 50, Qt.AlignCenter, APP_NAME)

    painter.setPen(QColor(ORANGE_DARK))
    font2 = QFont("Segoe UI", 14)
    font2.setLetterSpacing(QFont.AbsoluteSpacing, 8)
    painter.setFont(font2)
    painter.drawText(0, 170, 500, 30, Qt.AlignCenter, "PORTABLE")

    painter.setPen(QColor(TEXT_DIM))
    painter.setFont(QFont("Segoe UI", 9))
    painter.drawText(0, 255, 500, 20, Qt.AlignCenter, "Initializing...")

    painter.setPen(QColor("#1a1a1a"))
    painter.drawRect(100, 290, 300, 4)

    painter.setPen(QColor(TEXT_DIM))
    painter.setFont(QFont("Segoe UI", 8))
    painter.drawText(0, 300, 500, 20, Qt.AlignCenter, f"v{APP_VERSION}")

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

    splash_pix = create_splash_pixmap()
    splash = SplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    config = load_config()
    log_lines = []
    log_lines.append(f"Launcher: {APP_NAME} v{APP_VERSION}")
    log_lines.append(f"Time: {datetime.datetime.now()}")

    steps = [
        (10, "Preparing folders..."),
        (25, "Checking Roblox files..."),
        (40, "Scanning for updates..."),
        (60, None),
        (80, "Launching Roblox..."),
        (100, "Done!"),
    ]
    step_index = [0]
    error_occurred = [False]

    def do_step():
        idx = step_index[0]
        if idx >= len(steps) or error_occurred[0]:
            return

        progress, msg = steps[idx]

        if idx == 0:
            splash.set_progress(progress, msg)
            app.processEvents()
            os.makedirs(ROBLOX_DIR, exist_ok=True)
            os.makedirs(CACHE_DIR, exist_ok=True)
            os.makedirs(LOGS_DIR, exist_ok=True)
            log_lines.append("Folders ready")

        elif idx == 1:
            splash.set_progress(progress, msg)
            app.processEvents()
            exe_path = os.path.join(ROBLOX_DIR, "RobloxPlayerBeta.exe")
            if not os.path.isfile(exe_path):
                log_lines.append("RobloxPlayerBeta.exe not found in RobloxFiles")
            else:
                files = os.listdir(ROBLOX_DIR)
                dll_count = len([f for f in files if f.lower().endswith(".dll")])
                log_lines.append(f"Found {len(files)} files, {dll_count} DLLs")

        elif idx == 2:
            splash.set_progress(progress, msg)
            app.processEvents()
            system_path, system_fp = find_system_roblox()
            if system_path:
                portable_fp = get_folder_fingerprint(ROBLOX_DIR)
                saved_fp = config.get("last_synced_fingerprint", "")
                needs_update = system_fp and (system_fp != portable_fp) and (system_fp != saved_fp)
                needs_first_sync = not os.path.isfile(os.path.join(ROBLOX_DIR, "RobloxPlayerBeta.exe"))

                if needs_update or needs_first_sync:
                    reason = "first sync" if needs_first_sync else "update detected"
                    log_lines.append(f"Syncing Roblox files ({reason}): {system_path}")
                    steps[3] = (60, f"Syncing files from system...")
                    config["_pending_sync"] = system_path
                    config["_pending_fp"] = system_fp
                else:
                    log_lines.append("Roblox files up to date")
                    steps[3] = (60, "Files up to date!")
            else:
                log_lines.append("No system Roblox found (will use existing files)")
                steps[3] = (60, "Using existing files...")

        elif idx == 3:
            progress_val, msg_val = steps[3]
            splash.set_progress(progress_val, msg_val)
            app.processEvents()

            pending_sync = config.pop("_pending_sync", None)
            pending_fp = config.pop("_pending_fp", None)
            if pending_sync:
                try:
                    count, removed = sync_files(pending_sync, config)
                    config["last_synced_fingerprint"] = pending_fp
                    config["last_synced_from"] = pending_sync
                    config["last_synced_time"] = datetime.datetime.now().isoformat()
                    save_config(config)
                    log_lines.append(f"Synced {count} files, cleaned {removed} old files")
                except Exception as e:
                    log_lines.append(f"Sync failed: {e}")

        elif idx == 4:
            splash.set_progress(progress, msg)
            app.processEvents()

            exe_path = os.path.join(ROBLOX_DIR, "RobloxPlayerBeta.exe")
            if not os.path.isfile(exe_path):
                splash.set_progress(100, "Error: No Roblox files found!")
                app.processEvents()
                log_lines.append("ERROR: RobloxPlayerBeta.exe not found")
                log_lines.append(f"Please copy Roblox files to: {ROBLOX_DIR}")
                error_occurred[0] = True
                write_log("\n".join(log_lines))

                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None, APP_NAME,
                    f"Roblox files not found!\n\n"
                    f"Please copy your Roblox files to:\n{ROBLOX_DIR}\n\n"
                    f"You can find them at:\n"
                    f"%LOCALAPPDATA%\\Roblox\\Versions\\[version-hash]\\"
                )
                app.quit()
                return

            try:
                env = os.environ.copy()
                env["LOCALAPPDATA"] = os.path.abspath(CACHE_DIR)

                process = subprocess.Popen(
                    [exe_path],
                    cwd=ROBLOX_DIR,
                    env=env,
                )
                log_lines.append(f"Roblox launched (PID: {process.pid})")
                log_lines.append(f"Executable: {exe_path}")
                log_lines.append(f"Cache: {os.path.abspath(CACHE_DIR)}")
            except Exception as e:
                log_lines.append(f"Launch failed: {e}")
                error_occurred[0] = True
                splash.set_progress(100, f"Launch failed!")
                app.processEvents()
                write_log("\n".join(log_lines))

                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None, APP_NAME,
                    f"Could not launch Roblox:\n\n{str(e)}"
                )
                app.quit()
                return

        elif idx == 5:
            splash.set_progress(progress, msg)
            app.processEvents()
            write_log("\n".join(log_lines))
            QTimer.singleShot(800, app.quit)
            return

        step_index[0] += 1
        QTimer.singleShot(500, do_step)

    QTimer.singleShot(300, do_step)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
