# Roblox Portable Launcher

## Overview
A desktop GUI application (Python/PyQt5) that serves as a portable Roblox launcher. Users place their Roblox installation files into a specific folder, and this launcher runs Roblox directly from that folder — making it fully portable.

## Architecture
- **launcher.py** — Main application. Python PyQt5 desktop GUI.
- **launcher_config.json** — Stores user preferences (auto-created at runtime).
- **build_exe.bat** — Windows script to compile the app into a standalone .exe using PyInstaller.
- **requirements.txt** — Python dependencies for building on Windows.

## Features
- Browse and select a folder containing Roblox files
- Validates Roblox files (checks for RobloxPlayerBeta.exe, DLLs)
- Setup wizard that creates the portable folder structure (RobloxPortable/RobloxFiles, Logs, Cache)
- Launches Roblox from the selected folder with redirected AppData to keep data portable
- Launch logging with timestamps
- Persistent folder path (remembers last used folder)

## Tech Stack
- Python 3.11
- PyQt5 (GUI framework)
- VNC output for desktop rendering in Replit
- PyInstaller for .exe compilation on Windows

## How It Works
1. User clicks "Setup Folder" to create the portable directory structure
2. User copies their Roblox files into the RobloxFiles subfolder
3. App validates the files are present (checks for RobloxPlayerBeta.exe and DLL files)
4. User clicks "Launch Roblox" to run from the portable folder
5. AppData is redirected to a Cache folder to keep everything self-contained

## Building the EXE
To build a standalone .exe on Windows:
1. Install Python from python.org
2. Run `build_exe.bat`
3. The .exe will be in the `dist/` folder
