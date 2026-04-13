# Denfi Roblox - Portable Launcher

## Overview
A desktop GUI application (Python/PyQt5) called "DENFI ROBLOX" with black and orange theme. Runs Roblox from a portable folder — no system installation needed.

## Features
- Splash/loading screen with "DENFI ROBLOX PORTABLE" branding
- Black and orange themed UI
- Auto-detects RobloxFiles folder next to the .exe
- Status indicators with colored dots (green/red/yellow)
- "Update Roblox Files" button that auto-finds your system Roblox installation and copies files
- Launch logging with timestamps
- Custom icon support (place icon.ico next to the launcher)
- Redirects AppData to portable Cache folder

## Folder Structure
```
AnyFolder\
  DenfiRoblox.exe        <- The launcher
  icon.ico               <- Your custom icon (optional)
  RobloxFiles\           <- Roblox files go here (auto-created)
  Cache\                 <- Roblox data (auto-created, keeps portable)
  Logs\                  <- Launch logs (auto-created)
```

## Files
- **launcher.py** — Main application (PyQt5 GUI with splash screen)
- **build_exe.bat** — Windows build script (compiles to .exe via PyInstaller)
- **requirements.txt** — Python dependencies

## Building
1. Install Python from python.org (check "Add to PATH")
2. Optional: Place icon.ico next to launcher.py
3. Run `build_exe.bat`
4. Get `DenfiRoblox.exe` from `dist\` folder

## Tech Stack
- Python 3.11, PyQt5, PyInstaller
