# Denfi Roblox - Portable Launcher

## Overview
A zero-interaction portable Roblox launcher. Double-click the .exe and it does everything automatically:
1. Shows "DENFI ROBLOX PORTABLE" splash screen
2. Auto-syncs Roblox files if an update is detected on the system
3. Launches Roblox from the portable folder
4. Closes itself — no window to interact with

## How It Works
- The launcher checks `%LOCALAPPDATA%\Roblox\Versions\` for the latest Roblox version
- Compares it against the files in `RobloxFiles\` using fingerprinting
- If there's a newer version (or first run), it syncs everything automatically into the same folder
- Old files are cleaned up, new files replace them — no duplicate folders
- Roblox is launched with `LOCALAPPDATA` redirected to the portable `Cache\` folder
- Launcher closes itself after Roblox starts

## Folder Structure
```
AnyFolder\
  DenfiRoblox.exe        <- Double-click this
  icon.ico               <- Your custom icon (optional)
  RobloxFiles\           <- Auto-synced Roblox files
  Cache\                 <- Portable Roblox data
  Logs\                  <- Launch logs
  denfi_config.json      <- Tracks sync state
```

## Files
- **launcher.py** — Main application (splash screen, auto-sync, auto-launch)
- **build_exe.bat** — Windows build script
- **requirements.txt** — Python dependencies

## Building
1. Install Python from python.org (check "Add to PATH")
2. Optional: Place icon.ico next to launcher.py
3. Run `build_exe.bat`
4. Get `DenfiRoblox.exe` from `dist\` folder

## Tech Stack
- Python 3.11, PyQt5, PyInstaller
