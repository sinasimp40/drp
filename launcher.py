import sys
import os
import json
import subprocess
import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QFileDialog,
    QMessageBox, QFrame, QGroupBox, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QPixmap

CONFIG_FILE = "launcher_config.json"

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
INPUT_BG = "#0f3460"

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
QLineEdit {{
    background-color: {INPUT_BG};
    color: {TEXT};
    border: 1px solid {CARD_BORDER};
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
    font-family: 'Consolas', 'Courier New', monospace;
}}
QLineEdit:focus {{
    border-color: {ACCENT};
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
    font-size: 16px;
    padding: 14px 36px;
    border-radius: 8px;
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
    font-size: 22px;
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
QLabel#folderStatus {{
    font-size: 11px;
}}
"""


class RobloxPortableLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Roblox Portable Launcher")
        self.setMinimumSize(780, 620)
        self.resize(800, 650)

        self.config = self.load_config()
        self.roblox_found = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        self.build_header(layout)
        self.build_folder_section(layout)
        self.build_status_section(layout)
        self.build_actions_section(layout)
        self.build_log_section(layout)
        self.build_footer(layout)

        self.check_roblox_files()

    def build_header(self, parent_layout):
        header = QHBoxLayout()
        header.setSpacing(12)

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
        title = QLabel("Roblox Portable Launcher")
        title.setObjectName("titleLabel")
        text_col.addWidget(title)
        subtitle = QLabel("Run Roblox from any folder - take it anywhere")
        subtitle.setObjectName("subtitleLabel")
        text_col.addWidget(subtitle)
        header.addLayout(text_col)

        header.addStretch()

        badge = QLabel(" Windows ")
        badge.setStyleSheet(
            f"background-color: {CARD_BORDER}; color: {TEXT}; "
            f"padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: bold;"
        )
        header.addWidget(badge)

        parent_layout.addLayout(header)

    def build_folder_section(self, parent_layout):
        group = QGroupBox("Roblox Folder")

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select folder containing your Roblox files...")
        self.path_input.setText(self.config.get("roblox_folder", ""))
        self.path_input.returnPressed.connect(self.check_roblox_files)
        path_row.addWidget(self.path_input)

        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_folder)
        browse_btn.setFixedWidth(90)
        path_row.addWidget(browse_btn)

        layout.addLayout(path_row)

        self.folder_status_label = QLabel("No folder selected")
        self.folder_status_label.setObjectName("folderStatus")
        layout.addWidget(self.folder_status_label)

        parent_layout.addWidget(group)

    def build_status_section(self, parent_layout):
        group = QGroupBox("File Status")
        grid = QGridLayout(group)
        grid.setSpacing(6)

        labels = ["RobloxPlayerBeta.exe", "DLL Files", "Folder Ready"]
        self.status_values = []

        for i, text in enumerate(labels):
            name_label = QLabel(text)
            name_label.setObjectName("statusLabel")
            grid.addWidget(name_label, i, 0)

            val_label = QLabel("--")
            val_label.setObjectName("statusLabel")
            grid.addWidget(val_label, i, 1)
            self.status_values.append(val_label)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        parent_layout.addWidget(group)

    def build_actions_section(self, parent_layout):
        group = QGroupBox("Actions")
        layout = QHBoxLayout(group)
        layout.setSpacing(10)

        self.launch_btn = QPushButton("Launch Roblox")
        self.launch_btn.setObjectName("launchBtn")
        self.launch_btn.setCursor(Qt.PointingHandCursor)
        self.launch_btn.clicked.connect(self.launch_roblox)
        layout.addWidget(self.launch_btn)

        setup_btn = QPushButton("Setup Folder")
        setup_btn.setCursor(Qt.PointingHandCursor)
        setup_btn.clicked.connect(self.setup_folder)
        layout.addWidget(setup_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.check_roblox_files)
        layout.addWidget(refresh_btn)

        layout.addStretch()
        parent_layout.addWidget(group)

    def build_log_section(self, parent_layout):
        group = QGroupBox("Log")
        layout = QVBoxLayout(group)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(120)
        layout.addWidget(self.log_box)

        parent_layout.addWidget(group)
        self.log("Roblox Portable Launcher started")

    def build_footer(self, parent_layout):
        self.footer_label = QLabel("Ready")
        self.footer_label.setObjectName("statusLabel")
        parent_layout.addWidget(self.footer_label)

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {message}")

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Roblox Files Folder")
        if folder:
            self.path_input.setText(folder)
            self.save_config(folder)
            self.check_roblox_files()
            self.log(f"Folder selected: {folder}")

    def check_roblox_files(self):
        folder = self.path_input.text().strip()
        self.roblox_found = False

        if not folder:
            for v in self.status_values:
                v.setText("--")
                v.setObjectName("statusLabel")
                v.setStyle(v.style())
            self.folder_status_label.setText("No folder selected")
            self.folder_status_label.setStyleSheet(f"color: {TEXT_DIM};")
            self.footer_label.setText("Select a folder with your Roblox files")
            self.launch_btn.setEnabled(False)
            return

        if not os.path.isdir(folder):
            for v in self.status_values:
                v.setText("Not found")
                v.setObjectName("statusBad")
                v.setStyle(v.style())
            self.folder_status_label.setText("Folder does not exist")
            self.folder_status_label.setStyleSheet(f"color: {ERROR};")
            self.footer_label.setText("Folder path is invalid")
            self.launch_btn.setEnabled(False)
            self.log(f"Folder not found: {folder}")
            return

        exe_path = os.path.join(folder, "RobloxPlayerBeta.exe")
        has_exe = os.path.isfile(exe_path)

        try:
            files = os.listdir(folder)
        except Exception:
            files = []

        dll_count = len([f for f in files if f.endswith(".dll")])
        has_dlls = dll_count > 0
        total_files = len(files)

        if has_exe:
            self.status_values[0].setText("Found")
            self.status_values[0].setObjectName("statusOk")
        else:
            self.status_values[0].setText("Missing")
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
            self.status_values[2].setText("Ready")
            self.status_values[2].setObjectName("statusOk")
            self.roblox_found = True
            self.folder_status_label.setText(f"Found {total_files} files in folder")
            self.folder_status_label.setStyleSheet(f"color: {SUCCESS};")
            self.footer_label.setText("Ready to launch!")
            self.launch_btn.setEnabled(True)
            self.log(f"Roblox files verified: {total_files} files, {dll_count} DLLs")
        else:
            self.status_values[2].setText("Not Ready")
            self.status_values[2].setObjectName("statusBad")
            self.folder_status_label.setText("RobloxPlayerBeta.exe is missing")
            self.folder_status_label.setStyleSheet(f"color: {ERROR};")
            self.footer_label.setText("Missing required Roblox files")
            self.launch_btn.setEnabled(False)
            self.log("RobloxPlayerBeta.exe not found in selected folder")
        self.status_values[2].setStyle(self.status_values[2].style())

        self.save_config(folder)

    def launch_roblox(self):
        if not self.roblox_found:
            QMessageBox.warning(
                self, "Cannot Launch",
                "Roblox files not found!\n\n"
                "Please select a folder containing RobloxPlayerBeta.exe first."
            )
            return

        folder = self.path_input.text().strip()
        exe_path = os.path.join(folder, "RobloxPlayerBeta.exe")

        self.log("Launching Roblox...")
        self.footer_label.setText("Launching Roblox...")

        cache_dir = os.path.join(folder, "..", "Cache")
        logs_dir = os.path.join(folder, "..", "Logs")
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)

        try:
            env = os.environ.copy()
            env["LOCALAPPDATA"] = os.path.abspath(cache_dir)

            process = subprocess.Popen(
                [exe_path],
                cwd=folder,
                env=env,
            )

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(logs_dir, f"launch_{timestamp}.log")
            with open(log_file, "w") as f:
                f.write(f"Launch Time: {datetime.datetime.now()}\n")
                f.write(f"Executable: {exe_path}\n")
                f.write(f"PID: {process.pid}\n")
                f.write(f"Cache Dir: {os.path.abspath(cache_dir)}\n")

            self.log(f"Roblox launched successfully (PID: {process.pid})")
            self.footer_label.setText(f"Roblox running (PID: {process.pid})")

            QMessageBox.information(
                self, "Launched!",
                f"Roblox has been launched from:\n{folder}\n\nPID: {process.pid}"
            )
        except Exception as e:
            self.log(f"Launch failed: {str(e)}")
            self.footer_label.setText("Launch failed!")
            QMessageBox.critical(
                self, "Launch Failed",
                f"Could not launch Roblox:\n\n{str(e)}"
            )

    def setup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose where to create the portable folder")
        if not folder:
            return

        portable_dir = os.path.join(folder, "RobloxPortable")
        roblox_files_dir = os.path.join(portable_dir, "RobloxFiles")
        logs_dir = os.path.join(portable_dir, "Logs")
        cache_dir = os.path.join(portable_dir, "Cache")

        try:
            os.makedirs(roblox_files_dir, exist_ok=True)
            os.makedirs(logs_dir, exist_ok=True)
            os.makedirs(cache_dir, exist_ok=True)

            readme_path = os.path.join(roblox_files_dir, "PLACE_ROBLOX_HERE.txt")
            with open(readme_path, "w") as f:
                f.write("PLACE YOUR ROBLOX FILES HERE\n")
                f.write("=" * 40 + "\n\n")
                f.write("Copy ALL files from your Roblox installation:\n\n")
                f.write("  Default location:\n")
                f.write("  %LOCALAPPDATA%\\Roblox\\Versions\\[version-hash]\\\n\n")
                f.write("  Files needed:\n")
                f.write("  - RobloxPlayerBeta.exe\n")
                f.write("  - All .dll files\n")
                f.write("  - All other files in that folder\n")

            self.path_input.setText(roblox_files_dir)
            self.save_config(roblox_files_dir)
            self.check_roblox_files()
            self.log(f"Portable folder created at: {portable_dir}")

            QMessageBox.information(
                self, "Setup Complete",
                f"Portable folder created at:\n{portable_dir}\n\n"
                f"Next step: Copy your Roblox files into:\n{roblox_files_dir}"
            )
        except Exception as e:
            self.log(f"Setup failed: {str(e)}")
            QMessageBox.critical(
                self, "Setup Failed",
                f"Could not create folder:\n\n{str(e)}"
            )

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_config(self, folder):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"roblox_folder": folder}, f, indent=2)
        except Exception:
            pass


def main():
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = RobloxPortableLauncher()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
