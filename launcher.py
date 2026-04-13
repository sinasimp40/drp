import sys
import os
import json
import subprocess
import datetime
import shutil

from PyQt5.QtWidgets import (
    QApplication, QSplashScreen, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (
    QColor, QPainter, QPixmap, QIcon, QFont, QLinearGradient,
    QRadialGradient, QPen, QPainterPath, QBrush
)

APP_NAME = "DENFI ROBLOX"
APP_VERSION = "1.0.0"

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()
CONFIG_FILE = os.path.join(APP_DIR, "denfi_config.json")

BG = "#0a0a0a"
ORANGE = "#ff6a00"
ORANGE_LIGHT = "#ff8c33"
ORANGE_DARK = "#cc5500"
TEXT_WHITE = "#f0f0f0"
TEXT_DIM = "#555555"
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


def get_paths(config):
    base = config.get("denfi_path", APP_DIR)
    return {
        "base": base,
        "roblox": os.path.join(base, "RobloxFiles"),
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


class SplashScreen(QSplashScreen):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen)
        self.progress = 0
        self.status_msg = "Initializing..."
        self.error_msg = ""
        self.is_error = False
        self._base_pixmap = pixmap

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

            painter.setPen(QColor("#444444"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(0, version_y, w, 16, Qt.AlignCenter, f"v{APP_VERSION}")


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

    block_size = 18
    gap = 5
    grid_w = 3 * block_size + 2 * gap
    grid_x = (w - grid_w) // 2
    grid_y = 50
    painter.setPen(Qt.NoPen)
    for row in range(3):
        for col in range(3):
            x = grid_x + col * (block_size + gap)
            y = grid_y + row * (block_size + gap)
            block_grad = QLinearGradient(x, y, x + block_size, y + block_size)
            if row == 2 and col == 2:
                block_grad.setColorAt(0, QColor("#cc5500"))
                block_grad.setColorAt(1, QColor("#993d00"))
            else:
                block_grad.setColorAt(0, QColor("#ff7a1a"))
                block_grad.setColorAt(1, QColor("#ff6a00"))

            path = QPainterPath()
            path.addRoundedRect(x, y, block_size, block_size, 4, 4)
            painter.fillPath(path, block_grad)

            highlight = QLinearGradient(x, y, x, y + block_size)
            highlight.setColorAt(0, QColor(255, 255, 255, 35))
            highlight.setColorAt(0.5, QColor(255, 255, 255, 0))
            painter.fillPath(path, highlight)

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


def ask_for_path(app, config):
    if "denfi_path" in config:
        return True

    msg = QMessageBox()
    msg.setWindowTitle(APP_NAME)
    msg.setIcon(QMessageBox.Question)
    msg.setText(
        "Welcome to Denfi Roblox Portable!\n\n"
        "Where do you want to store your Roblox files?\n\n"
        "A 'RobloxFiles' folder will be created at the location you choose."
    )
    msg.setStyleSheet(
        f"QMessageBox {{ background-color: {BG}; color: {TEXT_WHITE}; }}"
        f"QLabel {{ color: {TEXT_WHITE}; font-size: 12px; }}"
        f"QPushButton {{ background-color: #2a2a2a; color: {TEXT_WHITE}; "
        f"border: 1px solid #3a3a3a; padding: 8px 20px; border-radius: 4px; "
        f"font-weight: bold; font-size: 11px; }}"
        f"QPushButton:hover {{ background-color: {ORANGE}; color: #0a0a0a; }}"
    )

    here_btn = msg.addButton("Use current folder", QMessageBox.AcceptRole)
    custom_btn = msg.addButton("Choose custom folder", QMessageBox.ActionRole)
    msg.exec_()

    clicked = msg.clickedButton()

    if clicked == custom_btn:
        folder = QFileDialog.getExistingDirectory(None, "Choose folder for Denfi Roblox")
        if not folder:
            return False
        config["denfi_path"] = folder
    else:
        config["denfi_path"] = APP_DIR

    save_config(config)
    return True


def main():
    if sys.platform != "win32":
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    icon_path = os.path.join(APP_DIR, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    config = load_config()

    if "denfi_path" not in config:
        if not ask_for_path(app, config):
            sys.exit(0)

    paths = get_paths(config)

    splash_pix = create_splash_pixmap()
    splash = SplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    log_lines = []
    log_lines.append(f"Launcher: {APP_NAME} v{APP_VERSION}")
    log_lines.append(f"Time: {datetime.datetime.now()}")
    log_lines.append(f"Base path: {paths['base']}")

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
            system_path, system_fp = find_system_roblox()

            config["_do_sync"] = False
            if system_path:
                portable_fp = get_folder_fingerprint(paths["roblox"])
                saved_fp = config.get("last_synced_fingerprint", "")
                needs_update = system_fp and (system_fp != portable_fp) and (system_fp != saved_fp)
                needs_first = not os.path.isfile(os.path.join(paths["roblox"], "RobloxPlayerBeta.exe"))

                if needs_update or needs_first:
                    config["_sync_source"] = system_path
                    config["_sync_fp"] = system_fp
                    config["_do_sync"] = True
                    reason = "first sync" if needs_first else "update detected"
                    log_lines.append(f"Sync needed ({reason}): {system_path}")
                else:
                    log_lines.append("Roblox files up to date")
            else:
                log_lines.append("No system Roblox found")

        elif idx == 3:
            if config.get("_do_sync"):
                splash.set_progress(55, "Syncing Roblox files...")
                app.processEvents()
                source = config.pop("_sync_source", "")
                fp = config.pop("_sync_fp", "")
                config.pop("_do_sync", None)
                try:
                    count, removed = sync_files(source, paths["roblox"])
                    config["last_synced_fingerprint"] = fp
                    config["last_synced_from"] = source
                    config["last_synced_time"] = datetime.datetime.now().isoformat()
                    save_config(config)
                    log_lines.append(f"Synced {count} files, cleaned {removed} old files")
                    splash.set_progress(70, f"Synced {count} files!")
                    app.processEvents()
                except Exception as e:
                    log_lines.append(f"Sync failed: {e}")
                    splash.set_progress(70, "Sync failed - using existing files")
                    app.processEvents()
            else:
                config.pop("_do_sync", None)
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

            splash.set_progress(85, "Launching Roblox...")
            app.processEvents()

            try:
                env = os.environ.copy()
                env["LOCALAPPDATA"] = os.path.abspath(paths["cache"])

                process = subprocess.Popen(
                    [exe_path],
                    cwd=paths["roblox"],
                    env=env,
                )
                log_lines.append(f"Roblox launched (PID: {process.pid})")
                log_lines.append(f"Executable: {exe_path}")
                log_lines.append(f"Cache: {os.path.abspath(paths['cache'])}")
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
            QTimer.singleShot(1200, app.quit)
            return

        step_index[0] += 1
        QTimer.singleShot(400, do_step)

    QTimer.singleShot(300, do_step)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
