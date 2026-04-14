# Portable Roblox Launcher

## Overview
A zero-interaction portable Roblox launcher. Double-click the .exe and it does everything automatically:
1. Shows custom-named splash screen (e.g. "DENFI ROBLOX PORTABLE")
2. Auto-syncs Roblox files if an update is detected on the system
3. Clears login data (rbx-storage.db) so each instance starts fresh
4. Grabs the Roblox mutex to allow multiple instances
5. Launches Roblox from the portable folder
6. Stays running in background to hold the mutex, cleans up login on exit

## How It Works
- The build script asks for your Roblox files path AND launcher name, bakes both into the exe
- The launcher checks `%LOCALAPPDATA%\Roblox\Versions\` for the latest Roblox version
- Compares it against the files in the configured folder using fingerprinting
- If there's a newer version (or first run), it syncs everything automatically
- Before launching, deletes `%LOCALAPPDATA%\Roblox\rbx-storage.db` to ensure fresh login
- Grabs `ROBLOX_singletonEvent` mutex (same as MultiRoblox) so multiple instances can coexist
- Launcher stays running hidden in background to hold the mutex alive
- When Roblox closes, deletes rbx-storage.db again and exits
- No config files needed at runtime — path and name are hardcoded during build

## Multi-Instance Flow
1. Run exe → clears rbx-storage.db → grabs mutex → launches Roblox (fresh, not logged in)
2. Log into Account A
3. Run exe again → clears rbx-storage.db → grabs mutex → launches second Roblox (fresh)
4. Log into Account B
5. Both stay open because both launchers hold the mutex in background
6. Close Roblox → launcher detects it → clears rbx-storage.db → exits

## Folder Structure
```
YourChosenFolder\
  RobloxPlayerBeta.exe   <- Roblox files live here
  Cache\                 <- Portable Roblox data
  Logs\                  <- Launch logs
```

## Files
- **launcher.py** — Main application (splash screen, auto-sync, login clear, mutex, auto-launch)
- **build_exe.bat** — Windows build script (asks for name + path, converts icons, builds exe)
- **build_config.py** — Helper that writes path and app name into launcher.py during build
- **convert_icon.py** — Auto-converts PNG/JPG/BMP/etc to icon.ico for the build
- **requirements.txt** — Python dependencies (PyQt5, Pillow, PyInstaller)

## Building
1. Install Python from python.org (check "Add to PATH")
2. Optional: Place any image file (PNG, JPG, etc.) next to the build script for the icon
3. Optional: Place `splash_logo.png` for the logo on the splash screen
4. Run `build_exe.bat`
5. Enter the launcher name when prompted (e.g. "DENFI ROBLOX", "MY LAUNCHER")
6. Enter the path to your Roblox files when prompted
7. Get `{YourName}.exe` from `dist\` folder

## Theme
- Background: black (#0a0a0a)
- Accent: orange (#ff6a00), lighter (#ff8c33), darker (#cc5500)
- Splash shows: logo + custom name + "PORTABLE" + progress bar + Roblox version

## Tech Stack
- Python 3.11, PyQt5, Pillow, PyInstaller, ctypes (Windows mutex)
