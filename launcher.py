import sys
import os
import json
import subprocess
import datetime
import shutil
import hashlib

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QMessageBox, QGroupBox, QGridLayout,
    QSplashScreen, QProgressBar, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QColor, QPainter, QPixmap, QIcon, QFont, QLinearGradient

APP_NAME = "DENFI ROBLOX"
APP_DISPLAY = "Denfi Roblox"
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
CARD_BG = "#141414"
CARD_BORDER = "#2a2a2a"
ORANGE = "#ff6a00"
ORANGE_LIGHT = "#ff8c33"
ORANGE_DARK = "#cc5500"
TEXT_WHITE = "#f0f0f0"
TEXT_GRAY = "#888888"
TEXT_DIM = "#555555"
GREEN = "#00cc66"
RED = "#ff3333"
YELLOW = "#ffaa00"

STYLESHEET = f"""
QMainWindow {{
    background-color: {BG};
}}
QWidget {{
    background-color: {BG};
    color: {TEXT_WHITE};
    font-family: 'Segoe UI', 'Arial', sans-serif;
}}
QGroupBox {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: 10px;
    margin-top: 6px;
    padding: 18px;
    padding-top: 36px;
    font-size: 13px;
    font-weight: bold;
    color: {ORANGE};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 18px;
    padding: 0 10px;
    color: {ORANGE};
    font-size: 13px;
}}
QPushButton {{
    background-color: {CARD_BORDER};
    color: {TEXT_WHITE};
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    padding: 10px 22px;
    font-size: 12px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: #3a3a3a;
    border-color: {ORANGE};
    color: {ORANGE};
}}
QPushButton:pressed {{
    background-color: {ORANGE_DARK};
    color: white;
}}
QPushButton#launchBtn {{
    background-color: {ORANGE};
    color: #0a0a0a;
    font-size: 18px;
    font-weight: bold;
    padding: 16px 60px;
    border-radius: 10px;
    border: 2px solid {ORANGE_LIGHT};
}}
QPushButton#launchBtn:hover {{
    background-color: {ORANGE_LIGHT};
    border-color: {ORANGE_LIGHT};
    color: #0a0a0a;
}}
QPushButton#launchBtn:pressed {{
    background-color: {ORANGE_DARK};
}}
QPushButton#launchBtn:disabled {{
    background-color: #2a2a2a;
    color: #555555;
    border-color: #333333;
}}
QPushButton#updateBtn {{
    background-color: transparent;
    color: {ORANGE};
    border: 1px solid {ORANGE};
    font-size: 11px;
    padding: 8px 16px;
}}
QPushButton#updateBtn:hover {{
    background-color: {ORANGE};
    color: #0a0a0a;
}}
QPushButton#autoUpdateBtn {{
    background-color: {ORANGE};
    color: #0a0a0a;
    border: 1px solid {ORANGE_LIGHT};
    font-size: 11px;
    font-weight: bold;
    padding: 8px 16px;
}}
QPushButton#autoUpdateBtn:hover {{
    background-color: {ORANGE_LIGHT};
}}
QTextEdit {{
    background-color: #0d0d0d;
    color: {TEXT_GRAY};
    border: 1px solid {CARD_BORDER};
    border-radius: 6px;
    padding: 10px;
    font-size: 11px;
    font-family: 'Consolas', 'Courier New', monospace;
    selection-background-color: {ORANGE_DARK};
}}
QLabel {{
    background-color: transparent;
    color: {TEXT_GRAY};
}}
QLabel#titleLabel {{
    font-size: 26px;
    font-weight: bold;
    color: {ORANGE};
    letter-spacing: 2px;
}}
QLabel#subtitleLabel {{
    font-size: 11px;
    color: {TEXT_DIM};
    letter-spacing: 1px;
}}
QLabel#statusOk {{
    color: {GREEN};
    font-weight: bold;
    font-size: 12px;
}}
QLabel#statusBad {{
    color: {RED};
    font-weight: bold;
    font-size: 12px;
}}
QLabel#statusWarn {{
    color: {YELLOW};
    font-weight: bold;
    font-size: 12px;
}}
QLabel#statusLabel {{
    color: {TEXT_GRAY};
    font-size: 12px;
}}
QLabel#pathLabel {{
    font-size: 11px;
    font-family: 'Consolas', 'Courier New', monospace;
    color: {ORANGE_LIGHT};
    padding: 8px 12px;
    background-color: #1a1a1a;
    border: 1px solid {CARD_BORDER};
    border-radius: 6px;
}}
QLabel#footerLabel {{
    color: {TEXT_DIM};
    font-size: 11px;
}}
QLabel#sectionHint {{
    color: {TEXT_DIM};
    font-size: 11px;
}}
QLabel#updateAlert {{
    color: {ORANGE};
    font-size: 12px;
    font-weight: bold;
    padding: 6px 10px;
    background-color: #1a1200;
    border: 1px solid {ORANGE_DARK};
    border-radius: 6px;
}}
QProgressBar {{
    background-color: #1a1a1a;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ORANGE};
    border-radius: 4px;
}}
"""


def get_file_hash(filepath):
    h = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


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


def create_splash():
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
    start_y = 50
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
    font = QFont("Segoe UI", 32, QFont.Bold)
    font.setLetterSpacing(QFont.AbsoluteSpacing, 4)
    painter.setFont(font)
    painter.drawText(0, 130, 500, 50, Qt.AlignCenter, APP_NAME)

    painter.setPen(QColor(TEXT_DIM))
    font2 = QFont("Segoe UI", 12)
    font2.setLetterSpacing(QFont.AbsoluteSpacing, 6)
    painter.setFont(font2)
    painter.drawText(0, 180, 500, 30, Qt.AlignCenter, "PORTABLE")

    painter.setPen(QColor(TEXT_DIM))
    font3 = QFont("Segoe UI", 9)
    painter.setFont(font3)
    painter.drawText(0, 260, 500, 20, Qt.AlignCenter, "Loading launcher...")

    painter.setPen(QColor(ORANGE_DARK))
    painter.drawRect(100, 290, 300, 4)
    painter.fillRect(100, 290, 200, 4, QColor(ORANGE))

    painter.setPen(QColor(TEXT_DIM))
    font4 = QFont("Segoe UI", 8)
    painter.setFont(font4)
    painter.drawText(0, 300, 500, 20, Qt.AlignCenter, f"v{APP_VERSION}")

    painter.end()
    return splash_pix


class DenfiRobloxLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_DISPLAY} - Portable Launcher")
        self.setMinimumSize(720, 620)
        self.resize(780, 660)

        icon_path = os.path.join(APP_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.roblox_found = False
        self.config = self.load_config()
        self.ensure_folders()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(10)

        self.build_header(layout)
        self.build_folder_info(layout)
        self.build_status_section(layout)
        self.build_launch_section(layout)
        self.build_log_section(layout)
        self.build_footer(layout)

        self.check_roblox_files()
        QTimer.singleShot(1000, self.auto_check_update)

    def ensure_folders(self):
        os.makedirs(ROBLOX_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(LOGS_DIR, exist_ok=True)

        readme = os.path.join(ROBLOX_DIR, "PLACE_ROBLOX_HERE.txt")
        if not os.path.exists(readme) and len(os.listdir(ROBLOX_DIR)) == 0:
            with open(readme, "w") as f:
                f.write(f"{APP_NAME} - Portable Launcher\n")
                f.write("=" * 40 + "\n\n")
                f.write("PLACE YOUR ROBLOX FILES HERE\n\n")
                f.write("Copy ALL files from your Roblox installation:\n\n")
                f.write("  Where to find them:\n")
                f.write("  %LOCALAPPDATA%\\Roblox\\Versions\\[version-hash]\\\n\n")
                f.write("  Files needed:\n")
                f.write("  - RobloxPlayerBeta.exe\n")
                f.write("  - All .dll files\n")
                f.write("  - All other files in that folder\n\n")
                f.write("After copying, just run the launcher!\n")

    def build_header(self, parent_layout):
        header = QHBoxLayout()
        header.setSpacing(14)

        icon = QLabel()
        pixmap = QPixmap(48, 48)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        block = 14
        gap = 3
        for r in range(3):
            for c in range(3):
                x = c * (block + gap)
                y = r * (block + gap)
                if r == 2 and c == 2:
                    painter.setBrush(QColor(ORANGE_DARK))
                else:
                    painter.setBrush(QColor(ORANGE))
                painter.drawRoundedRect(x, y, block, block, 2, 2)
        painter.end()
        icon.setPixmap(pixmap)
        icon.setFixedSize(48, 48)
        header.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        text_col.addWidget(title)
        subtitle = QLabel("PORTABLE LAUNCHER")
        subtitle.setObjectName("subtitleLabel")
        text_col.addWidget(subtitle)
        header.addLayout(text_col)

        header.addStretch()

        version_label = QLabel(f" v{APP_VERSION} ")
        version_label.setStyleSheet(
            f"background-color: #1a1a1a; color: {ORANGE}; "
            f"padding: 4px 14px; border-radius: 4px; font-size: 11px; "
            f"font-weight: bold; border: 1px solid {CARD_BORDER};"
        )
        header.addWidget(version_label)

        parent_layout.addLayout(header)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {CARD_BORDER};")
        parent_layout.addWidget(sep)

    def build_folder_info(self, parent_layout):
        group = QGroupBox("ROBLOX FILES")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        path_label = QLabel(ROBLOX_DIR)
        path_label.setObjectName("pathLabel")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        hint = QLabel(
            "Roblox files are loaded from the RobloxFiles folder next to this launcher."
        )
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.update_alert = QLabel("")
        self.update_alert.setObjectName("updateAlert")
        self.update_alert.setVisible(False)
        layout.addWidget(self.update_alert)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        open_btn = QPushButton("Open Folder")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setFixedWidth(140)
        open_btn.clicked.connect(self.open_roblox_folder)
        btn_row.addWidget(open_btn)

        update_btn = QPushButton("Update Roblox Files")
        update_btn.setObjectName("updateBtn")
        update_btn.setCursor(Qt.PointingHandCursor)
        update_btn.setFixedWidth(180)
        update_btn.setToolTip("Copy updated Roblox files from your system into the same RobloxFiles folder")
        update_btn.clicked.connect(self.update_roblox_files)
        btn_row.addWidget(update_btn)

        self.auto_update_btn = QPushButton("Update Available - Click to Sync")
        self.auto_update_btn.setObjectName("autoUpdateBtn")
        self.auto_update_btn.setCursor(Qt.PointingHandCursor)
        self.auto_update_btn.clicked.connect(self.auto_sync_update)
        self.auto_update_btn.setVisible(False)
        btn_row.addWidget(self.auto_update_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        parent_layout.addWidget(group)

    def build_status_section(self, parent_layout):
        group = QGroupBox("STATUS")
        grid = QGridLayout(group)
        grid.setSpacing(8)
        grid.setContentsMargins(12, 12, 12, 12)

        labels = ["RobloxPlayerBeta.exe", "DLL Files", "Roblox Version", "Ready to Launch"]
        self.status_values = []

        for i, text in enumerate(labels):
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {TEXT_DIM}; border-radius: 4px;")
            grid.addWidget(dot, i, 0, Qt.AlignCenter)

            name_label = QLabel(text)
            name_label.setObjectName("statusLabel")
            grid.addWidget(name_label, i, 1)

            val_label = QLabel("Checking...")
            val_label.setObjectName("statusLabel")
            grid.addWidget(val_label, i, 2)
            self.status_values.append((dot, val_label))

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 2)
        parent_layout.addWidget(group)

    def build_launch_section(self, parent_layout):
        launch_frame = QWidget()
        launch_frame.setStyleSheet(
            f"background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 10px;"
        )
        layout = QHBoxLayout(launch_frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        layout.addStretch()

        self.launch_btn = QPushButton("LAUNCH ROBLOX")
        self.launch_btn.setObjectName("launchBtn")
        self.launch_btn.setCursor(Qt.PointingHandCursor)
        self.launch_btn.clicked.connect(self.launch_roblox)
        self.launch_btn.setEnabled(False)
        layout.addWidget(self.launch_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_all)
        layout.addWidget(refresh_btn)

        layout.addStretch()
        parent_layout.addWidget(launch_frame)

    def build_log_section(self, parent_layout):
        group = QGroupBox("LOG")
        layout = QVBoxLayout(group)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(90)
        layout.addWidget(self.log_box)

        parent_layout.addWidget(group)
        self.log(f"{APP_NAME} started")
        self.log(f"Roblox folder: {ROBLOX_DIR}")

    def build_footer(self, parent_layout):
        footer = QHBoxLayout()
        self.footer_label = QLabel("Ready")
        self.footer_label.setObjectName("footerLabel")
        footer.addWidget(self.footer_label)
        footer.addStretch()
        credit = QLabel(f"{APP_DISPLAY} Portable v{APP_VERSION}")
        credit.setObjectName("footerLabel")
        footer.addWidget(credit)
        parent_layout.addLayout(footer)

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {message}")

    def refresh_all(self):
        self.check_roblox_files()
        self.auto_check_update()

    def open_roblox_folder(self):
        os.makedirs(ROBLOX_DIR, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(ROBLOX_DIR)
        else:
            subprocess.Popen(["xdg-open", ROBLOX_DIR])
        self.log("Opened RobloxFiles folder")

    def auto_check_update(self):
        system_path, system_fp = find_system_roblox()
        if not system_path:
            self.update_alert.setVisible(False)
            self.auto_update_btn.setVisible(False)
            return

        portable_fp = get_folder_fingerprint(ROBLOX_DIR)
        saved_fp = self.config.get("last_synced_fingerprint", "")

        if system_fp and system_fp != portable_fp and system_fp != saved_fp:
            version_name = os.path.basename(system_path)
            self.update_alert.setText(
                f"Roblox update detected! New version: {version_name}"
            )
            self.update_alert.setVisible(True)
            self.auto_update_btn.setVisible(True)
            self.pending_update_path = system_path
            self.pending_update_fp = system_fp
            self.log(f"Update detected: {version_name}")
        else:
            self.update_alert.setVisible(False)
            self.auto_update_btn.setVisible(False)
            if system_fp:
                self.log("Roblox files are up to date")

    def auto_sync_update(self):
        if not hasattr(self, 'pending_update_path'):
            return

        reply = QMessageBox.question(
            self, "Update Roblox Files",
            f"Update detected at:\n{self.pending_update_path}\n\n"
            f"Sync new files into your RobloxFiles folder?\n"
            f"(Old files will be replaced - same folder, no new folders created)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self.do_update(self.pending_update_path, self.pending_update_fp)

    def update_roblox_files(self):
        system_path, system_fp = find_system_roblox()
        if system_path:
            reply = QMessageBox.question(
                self, "Update Roblox Files",
                f"Found Roblox at:\n{system_path}\n\n"
                f"Sync all files into your RobloxFiles folder?\n"
                f"(Files are replaced in the same folder - nothing new is created)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.do_update(system_path, system_fp)
                return

        folder = QFileDialog.getExistingDirectory(
            self, "Select folder with Roblox files to copy from"
        )
        if folder:
            self.do_update(folder, None)

    def do_update(self, source_dir, fingerprint):
        try:
            self.log(f"Syncing from: {source_dir}")
            self.footer_label.setText("Updating Roblox files...")
            QApplication.processEvents()

            old_files = set()
            if os.path.isdir(ROBLOX_DIR):
                for item in os.listdir(ROBLOX_DIR):
                    if item != "PLACE_ROBLOX_HERE.txt":
                        old_files.add(item)

            new_files = set()
            count = 0
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

            removed = 0
            for old_item in old_files - new_files:
                old_path = os.path.join(ROBLOX_DIR, old_item)
                if os.path.isfile(old_path):
                    os.remove(old_path)
                    removed += 1
                elif os.path.isdir(old_path):
                    shutil.rmtree(old_path)
                    removed += 1

            if fingerprint:
                self.config["last_synced_fingerprint"] = fingerprint
                self.config["last_synced_from"] = source_dir
                self.config["last_synced_time"] = datetime.datetime.now().isoformat()
                self.save_config()

            self.update_alert.setVisible(False)
            self.auto_update_btn.setVisible(False)

            self.log(f"Synced {count} files, removed {removed} old files")
            self.check_roblox_files()

            QMessageBox.information(
                self, "Update Complete",
                f"Roblox files synced!\n\n"
                f"Copied: {count} files\n"
                f"Cleaned up: {removed} old files\n"
                f"From: {source_dir}\n\n"
                f"Everything is in your same RobloxFiles folder."
            )
        except Exception as e:
            self.log(f"Update failed: {str(e)}")
            QMessageBox.critical(self, "Update Failed", f"Could not update files:\n\n{str(e)}")

    def set_status(self, index, text, status):
        dot, label = self.status_values[index]
        label.setText(text)
        if status == "ok":
            dot.setStyleSheet(f"background-color: {GREEN}; border-radius: 4px;")
            label.setObjectName("statusOk")
        elif status == "bad":
            dot.setStyleSheet(f"background-color: {RED}; border-radius: 4px;")
            label.setObjectName("statusBad")
        elif status == "warn":
            dot.setStyleSheet(f"background-color: {YELLOW}; border-radius: 4px;")
            label.setObjectName("statusWarn")
        else:
            dot.setStyleSheet(f"background-color: {TEXT_DIM}; border-radius: 4px;")
            label.setObjectName("statusLabel")
        label.setStyle(label.style())

    def check_roblox_files(self):
        self.roblox_found = False

        if not os.path.isdir(ROBLOX_DIR):
            self.set_status(0, "Folder missing", "bad")
            self.set_status(1, "Folder missing", "bad")
            self.set_status(2, "--", "none")
            self.set_status(3, "NO", "bad")
            self.footer_label.setText("RobloxFiles folder not found")
            self.launch_btn.setEnabled(False)
            return

        exe_path = os.path.join(ROBLOX_DIR, "RobloxPlayerBeta.exe")
        has_exe = os.path.isfile(exe_path)

        try:
            files = os.listdir(ROBLOX_DIR)
        except Exception:
            files = []

        real_files = [f for f in files if f != "PLACE_ROBLOX_HERE.txt"]
        dll_count = len([f for f in files if f.lower().endswith(".dll")])
        total_files = len(real_files)

        if has_exe:
            self.set_status(0, "Found", "ok")
        else:
            self.set_status(0, "Missing", "bad")

        if dll_count > 0:
            self.set_status(1, f"Found ({dll_count} files)", "ok")
        else:
            self.set_status(1, "None found", "warn")

        version_str = self.detect_version()
        if version_str:
            self.set_status(2, version_str, "ok")
        else:
            self.set_status(2, "Unknown", "warn" if has_exe else "none")

        if has_exe:
            self.set_status(3, "YES - Ready!", "ok")
            self.roblox_found = True
            self.footer_label.setText(f"Ready - {total_files} files loaded")
            self.launch_btn.setEnabled(True)
            self.log(f"Roblox OK: {total_files} files, {dll_count} DLLs")
        else:
            self.set_status(3, "NO - Files needed", "bad")
            self.footer_label.setText("Copy Roblox files to RobloxFiles folder")
            self.launch_btn.setEnabled(False)
            self.log("Waiting for Roblox files...")

    def detect_version(self):
        last_from = self.config.get("last_synced_from", "")
        if last_from:
            version_hash = os.path.basename(last_from)
            if version_hash.startswith("version-"):
                return version_hash
        exe_path = os.path.join(ROBLOX_DIR, "RobloxPlayerBeta.exe")
        if os.path.isfile(exe_path):
            stat = os.stat(exe_path)
            mod_time = datetime.datetime.fromtimestamp(stat.st_mtime)
            return f"Synced {mod_time.strftime('%Y-%m-%d %H:%M')}"
        return None

    def launch_roblox(self):
        if not self.roblox_found:
            QMessageBox.warning(
                self, "Cannot Launch",
                "Roblox files not found!\n\n"
                "Copy your Roblox files into the RobloxFiles folder first."
            )
            return

        exe_path = os.path.join(ROBLOX_DIR, "RobloxPlayerBeta.exe")

        self.log("Launching Roblox...")
        self.footer_label.setText("Launching...")

        try:
            env = os.environ.copy()
            env["LOCALAPPDATA"] = os.path.abspath(CACHE_DIR)

            process = subprocess.Popen(
                [exe_path],
                cwd=ROBLOX_DIR,
                env=env,
            )

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(LOGS_DIR, f"launch_{timestamp}.log")
            with open(log_file, "w") as f:
                f.write(f"Launcher: {APP_NAME} v{APP_VERSION}\n")
                f.write(f"Launch Time: {datetime.datetime.now()}\n")
                f.write(f"Executable: {exe_path}\n")
                f.write(f"PID: {process.pid}\n")
                f.write(f"Cache Dir: {os.path.abspath(CACHE_DIR)}\n")
                f.write(f"Roblox Dir: {ROBLOX_DIR}\n")

            self.log(f"Roblox launched! (PID: {process.pid})")
            self.footer_label.setText(f"Roblox running (PID: {process.pid})")

        except FileNotFoundError:
            self.log("Launch failed: RobloxPlayerBeta.exe not found")
            self.footer_label.setText("Launch failed!")
            QMessageBox.critical(
                self, "Launch Failed",
                "Could not find RobloxPlayerBeta.exe\n\n"
                "Make sure you copied all Roblox files to the RobloxFiles folder."
            )
        except Exception as e:
            self.log(f"Launch failed: {str(e)}")
            self.footer_label.setText("Launch failed!")
            QMessageBox.critical(
                self, "Launch Failed",
                f"Could not launch Roblox:\n\n{str(e)}"
            )

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass


class SplashScreen(QSplashScreen):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen)
        self.progress = 0

    def set_progress(self, value):
        self.progress = value
        self.repaint()

    def drawContents(self, painter):
        painter.setPen(QColor(ORANGE))
        bar_y = 290
        bar_w = int(300 * self.progress / 100)
        painter.fillRect(100, bar_y, bar_w, 4, QColor(ORANGE))

        messages = {
            0: "Initializing...",
            20: "Loading configuration...",
            40: "Checking folders...",
            60: "Scanning Roblox files...",
            80: "Checking for updates...",
            100: "Ready!"
        }
        msg = "Loading..."
        for threshold in sorted(messages.keys(), reverse=True):
            if self.progress >= threshold:
                msg = messages[threshold]
                break

        painter.setPen(QColor(TEXT_DIM))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(0, 260, 500, 20, Qt.AlignCenter, msg)


def main():
    if sys.platform != "win32":
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(STYLESHEET)

    icon_path = os.path.join(APP_DIR, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    splash_pix = create_splash()
    splash = SplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    steps = [0, 20, 40, 60, 80, 100]
    current_step = [0]

    def advance_splash():
        if current_step[0] < len(steps):
            splash.set_progress(steps[current_step[0]])
            app.processEvents()
            current_step[0] += 1
            if current_step[0] < len(steps):
                QTimer.singleShot(400, advance_splash)
            else:
                QTimer.singleShot(500, show_main)

    def show_main():
        window = DenfiRobloxLauncher()
        window.show()
        splash.finish(window)
        app.main_window = window

    advance_splash()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
