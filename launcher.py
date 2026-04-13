import sys
import os
import json
import subprocess
import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QMessageBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPixmap, QIcon

APP_NAME = "Denfi Roblox"
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

DARK_BG = "#1a1a2e"
CARD_BG = "#16213e"
CARD_BORDER = "#0f3460"
ACCENT = "#e94560"
ACCENT_HOVER = "#ff6b81"
TEXT = "#eaeaea"
TEXT_DIM = "#8892b0"
SUCCESS = "#00d672"
WARNING = "#ffa502"
ERROR = "#ff4757"

STYLESHEET = f"""
QMainWindow {{
    background-color: {DARK_BG};
}}
QWidget {{
    background-color: {DARK_BG};
    color: {TEXT};
    font-family: 'Segoe UI', 'Arial', sans-serif;
}}
QGroupBox {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: 8px;
    margin-top: 8px;
    padding: 16px;
    padding-top: 32px;
    font-size: 14px;
    font-weight: bold;
    color: {TEXT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {TEXT};
}}
QPushButton {{
    background-color: {CARD_BORDER};
    color: {TEXT};
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 12px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#launchBtn {{
    background-color: {ACCENT};
    color: white;
    font-size: 18px;
    padding: 18px 50px;
    border-radius: 10px;
}}
QPushButton#launchBtn:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#launchBtn:disabled {{
    background-color: #3a3a5e;
    color: #6a6a8e;
}}
QTextEdit {{
    background-color: #0d1117;
    color: {TEXT_DIM};
    border: 1px solid {CARD_BORDER};
    border-radius: 4px;
    padding: 8px;
    font-size: 11px;
    font-family: 'Consolas', 'Courier New', monospace;
}}
QLabel {{
    background-color: transparent;
    color: {TEXT_DIM};
}}
QLabel#titleLabel {{
    font-size: 24px;
    font-weight: bold;
    color: {TEXT};
}}
QLabel#subtitleLabel {{
    font-size: 12px;
    color: {TEXT_DIM};
}}
QLabel#statusOk {{
    color: {SUCCESS};
    font-weight: bold;
    font-size: 12px;
}}
QLabel#statusBad {{
    color: {ERROR};
    font-weight: bold;
    font-size: 12px;
}}
QLabel#statusWarn {{
    color: {WARNING};
    font-weight: bold;
    font-size: 12px;
}}
QLabel#statusLabel {{
    color: {TEXT_DIM};
    font-size: 12px;
}}
QLabel#pathLabel {{
    font-size: 11px;
    font-family: 'Consolas', 'Courier New', monospace;
    color: {TEXT_DIM};
    padding: 6px 10px;
    background-color: #0f3460;
    border-radius: 4px;
}}
"""


class DenfiRobloxLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - Portable Launcher")
        self.setMinimumSize(700, 580)
        self.resize(780, 620)

        icon_path = os.path.join(APP_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.roblox_found = False

        self.ensure_folders()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)

        self.build_header(layout)
        self.build_folder_info(layout)
        self.build_status_section(layout)
        self.build_launch_section(layout)
        self.build_log_section(layout)
        self.build_footer(layout)

        self.check_roblox_files()

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
        pixmap = QPixmap(50, 50)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(ACCENT))
        painter.drawRoundedRect(5, 5, 18, 18, 3, 3)
        painter.drawRoundedRect(27, 5, 18, 18, 3, 3)
        painter.drawRoundedRect(5, 27, 18, 18, 3, 3)
        painter.setBrush(QColor("#c53030"))
        painter.drawRoundedRect(27, 27, 18, 18, 3, 3)
        painter.end()
        icon.setPixmap(pixmap)
        icon.setFixedSize(50, 50)
        header.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        text_col.addWidget(title)
        subtitle = QLabel("Portable Roblox Launcher - No installation needed")
        subtitle.setObjectName("subtitleLabel")
        text_col.addWidget(subtitle)
        header.addLayout(text_col)

        header.addStretch()

        version_label = QLabel(f" v{APP_VERSION} ")
        version_label.setStyleSheet(
            f"background-color: {CARD_BORDER}; color: {TEXT}; "
            f"padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: bold;"
        )
        header.addWidget(version_label)

        parent_layout.addLayout(header)

    def build_folder_info(self, parent_layout):
        group = QGroupBox("Roblox Files Location")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        info_label = QLabel("The launcher automatically reads Roblox from this folder:")
        info_label.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        layout.addWidget(info_label)

        path_label = QLabel(ROBLOX_DIR)
        path_label.setObjectName("pathLabel")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        hint = QLabel(
            "Just copy all your Roblox files into the RobloxFiles folder next to this launcher, then click Launch!"
        )
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        open_btn = QPushButton("Open RobloxFiles Folder")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setFixedWidth(220)
        open_btn.clicked.connect(self.open_roblox_folder)
        layout.addWidget(open_btn)

        parent_layout.addWidget(group)

    def build_status_section(self, parent_layout):
        group = QGroupBox("File Check")
        grid = QGridLayout(group)
        grid.setSpacing(6)

        labels = ["RobloxPlayerBeta.exe", "DLL Files", "Ready to Launch"]
        self.status_values = []

        for i, text in enumerate(labels):
            name_label = QLabel(text)
            name_label.setObjectName("statusLabel")
            grid.addWidget(name_label, i, 0)

            val_label = QLabel("Checking...")
            val_label.setObjectName("statusLabel")
            grid.addWidget(val_label, i, 1)
            self.status_values.append(val_label)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        parent_layout.addWidget(group)

    def build_launch_section(self, parent_layout):
        group = QGroupBox("")
        group.setStyleSheet(
            f"QGroupBox {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; "
            f"border-radius: 8px; padding: 20px; }}"
        )
        layout = QHBoxLayout(group)
        layout.setSpacing(12)

        layout.addStretch()

        self.launch_btn = QPushButton(f"Launch Roblox")
        self.launch_btn.setObjectName("launchBtn")
        self.launch_btn.setCursor(Qt.PointingHandCursor)
        self.launch_btn.clicked.connect(self.launch_roblox)
        self.launch_btn.setEnabled(False)
        layout.addWidget(self.launch_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.check_roblox_files)
        layout.addWidget(refresh_btn)

        layout.addStretch()
        parent_layout.addWidget(group)

    def build_log_section(self, parent_layout):
        group = QGroupBox("Activity Log")
        layout = QVBoxLayout(group)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(100)
        layout.addWidget(self.log_box)

        parent_layout.addWidget(group)
        self.log(f"{APP_NAME} started")
        self.log(f"Looking for Roblox files in: {ROBLOX_DIR}")

    def build_footer(self, parent_layout):
        self.footer_label = QLabel("Ready")
        self.footer_label.setObjectName("statusLabel")
        parent_layout.addWidget(self.footer_label)

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {message}")

    def open_roblox_folder(self):
        os.makedirs(ROBLOX_DIR, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(ROBLOX_DIR)
        else:
            subprocess.Popen(["xdg-open", ROBLOX_DIR])
        self.log("Opened RobloxFiles folder")

    def check_roblox_files(self):
        self.roblox_found = False

        if not os.path.isdir(ROBLOX_DIR):
            for v in self.status_values:
                v.setText("Folder missing")
                v.setObjectName("statusBad")
                v.setStyle(v.style())
            self.footer_label.setText("RobloxFiles folder not found")
            self.launch_btn.setEnabled(False)
            self.log("RobloxFiles folder is missing")
            return

        exe_path = os.path.join(ROBLOX_DIR, "RobloxPlayerBeta.exe")
        has_exe = os.path.isfile(exe_path)

        try:
            files = os.listdir(ROBLOX_DIR)
        except Exception:
            files = []

        real_files = [f for f in files if f != "PLACE_ROBLOX_HERE.txt"]
        dll_count = len([f for f in files if f.lower().endswith(".dll")])
        has_dlls = dll_count > 0
        total_files = len(real_files)

        if has_exe:
            self.status_values[0].setText("Found")
            self.status_values[0].setObjectName("statusOk")
        else:
            self.status_values[0].setText("Missing - copy it to RobloxFiles folder")
            self.status_values[0].setObjectName("statusBad")
        self.status_values[0].setStyle(self.status_values[0].style())

        if has_dlls:
            self.status_values[1].setText(f"Found ({dll_count} files)")
            self.status_values[1].setObjectName("statusOk")
        else:
            self.status_values[1].setText("None found")
            self.status_values[1].setObjectName("statusWarn")
        self.status_values[1].setStyle(self.status_values[1].style())

        if has_exe:
            self.status_values[2].setText("YES - Ready!")
            self.status_values[2].setObjectName("statusOk")
            self.roblox_found = True
            self.footer_label.setText(f"Ready! Found {total_files} Roblox files")
            self.launch_btn.setEnabled(True)
            self.log(f"Roblox files OK: {total_files} files, {dll_count} DLLs")
        else:
            self.status_values[2].setText("NO - Files missing")
            self.status_values[2].setObjectName("statusBad")
            self.footer_label.setText("Copy your Roblox files to the RobloxFiles folder")
            self.launch_btn.setEnabled(False)
            self.log("Waiting for Roblox files...")
        self.status_values[2].setStyle(self.status_values[2].style())

    def launch_roblox(self):
        if not self.roblox_found:
            QMessageBox.warning(
                self, "Cannot Launch",
                "Roblox files not found!\n\n"
                "Copy your Roblox files into the RobloxFiles folder first."
            )
            return

        exe_path = os.path.join(ROBLOX_DIR, "RobloxPlayerBeta.exe")

        self.log("Launching Roblox from portable folder...")
        self.footer_label.setText("Launching Roblox...")

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

    window = DenfiRobloxLauncher()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
