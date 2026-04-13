# Denfi Roblox - Portable Launcher

## Overview
A zero-interaction portable Roblox launcher. Double-click the .exe and it does everything automatically:
1. Shows "DENFI ROBLOX PORTABLE" splash screen
2. Auto-syncs Roblox files if an update is detected on the system
3. Launches Roblox from the portable folder
4. Closes itself — no window to interact with

## How It Works
- The build script asks for your Roblox files path and bakes it into the exe
- The launcher checks `%LOCALAPPDATA%\Roblox\Versions\` for the latest Roblox version
- Compares it against the files in the configured folder using fingerprinting
- If there's a newer version (or first run), it syncs everything automatically
- Old files are cleaned up, new files replace them — no duplicate folders
- Roblox is launched with `LOCALAPPDATA` redirected to the portable `Cache\` folder
- Launcher closes itself after Roblox starts
- No config files needed at runtime — path is hardcoded during build

## Folder Structure
```
YourChosenFolder\
  RobloxPlayerBeta.exe   <- Roblox files live here
  Cache\                 <- Portable Roblox data
  Logs\                  <- Launch logs
```

## Files
- **launcher.py** — Main application (splash screen, auto-sync, auto-launch)
- **build_exe.bat** — Windows build script (asks for Roblox path, converts icons, builds exe)
- **build_config.py** — Helper that writes the chosen path into launcher.py during build
- **convert_icon.py** — Auto-converts PNG/JPG/BMP/etc to icon.ico for the build
- **requirements.txt** — Python dependencies (PyQt5, Pillow, PyInstaller)

## Building
1. Install Python from python.org (check "Add to PATH")
2. Optional: Place any image file (PNG, JPG, etc.) next to the build script for the icon
3. Run `build_exe.bat`
4. Enter the path to your Roblox files when prompted
5. Get `DenfiRoblox.exe` from `dist\` folder

## Tech Stack
- Python 3.11, PyQt5, Pillow, PyInstaller
