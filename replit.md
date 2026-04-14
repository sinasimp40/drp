# Portable Roblox Launcher

## Overview
A zero-interaction portable Roblox launcher. Double-click the .exe and it does everything automatically:
1. Validates license key with online server (if configured)
2. Shows custom-named splash screen (e.g. "DENFI ROBLOX PORTABLE")
3. Auto-syncs Roblox files if an update is detected on the system
4. Clears login data (rbx-storage.db) so each instance starts fresh
5. Grabs the Roblox mutex to allow multiple instances
6. Launches Roblox from the portable folder
7. Stays running in background to hold the mutex, cleans up login on exit

## How It Works
- The build script asks for your Roblox files path, launcher name, and license server URL — bakes all into the exe
- The launcher checks `%LOCALAPPDATA%\Roblox\Versions\` for the latest Roblox version
- Compares it against the files in the configured folder using fingerprinting
- If there's a newer version (or first run), it syncs everything automatically
- Before launching, deletes `%LOCALAPPDATA%\Roblox\rbx-storage.db` to ensure fresh login
- Grabs `ROBLOX_singletonEvent` mutex (same as MultiRoblox) so multiple instances can coexist
- Launcher stays running hidden in background to hold the mutex alive
- When Roblox closes, deletes rbx-storage.db again and exits
- No config files needed at runtime — path, name, and license server are hardcoded during build

## License System
- License server runs on your RDP (default: 144.31.48.238:3842)
- Admin dashboard at the server URL — create keys, monitor online users, revoke access
- Dashboard updates live every 5 seconds via AJAX (no page reload), with real-time countdown timers
- Launcher prompts for license key on first run, saves it locally
- Validates with server before launching, re-checks every 15 seconds for near-instant revocation
- If license expires or is revoked, shows lock screen and stops
- Offline grace: 3 consecutive server failures tolerated before locking (prevents brief network blips from killing sessions)
- Server signs responses with HMAC to prevent tampering
- Optional: leave license server URL blank during build to disable checking

## Multi-Instance Flow
1. Run exe → validates license → clears rbx-storage.db → grabs mutex → launches Roblox (fresh, not logged in)
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

license_server\          <- Deploy this to your RDP
  server.py              <- Flask license server + admin dashboard
  templates/             <- Dashboard HTML templates
  licenses.db            <- SQLite database (auto-created)
  DEPLOY.md              <- Deployment instructions
```

## Files
- **launcher.py** — Main application (license check, splash screen, auto-sync, login clear, mutex, auto-launch)
- **build_exe.bat** — Windows build script (asks for name + path + license URL, converts icons, builds exe)
- **build_config.py** — Helper that writes path, app name, and license URL into launcher.py during build
- **convert_icon.py** — Auto-converts PNG/JPG/BMP/etc to icon.ico for the build
- **requirements.txt** — Python dependencies (PyQt5, Pillow, PyInstaller)
- **license_server/** — License server directory (deploy to RDP separately)

## Building
1. Install Python from python.org (check "Add to PATH")
2. Optional: Place any image file (PNG, JPG, etc.) next to the build script for the icon
3. Optional: Place `splash_logo.png` for the logo on the splash screen
4. Run `build_exe.bat`
5. Enter the launcher name when prompted (e.g. "DENFI ROBLOX", "MY LAUNCHER")
6. Enter the path to your Roblox files when prompted
7. Enter the license server URL (e.g. http://144.31.48.238:3842) or press Enter to skip
8. Get `{YourName}.exe` from `dist\` folder

## License Server Setup
See `license_server/DEPLOY.md` for full instructions.
Quick: copy `license_server/` to your RDP, `pip install flask`, `python server.py`

## Theme
- Background: black (#0a0a0a)
- Accent: orange (#ff6a00), lighter (#ff8c33), darker (#cc5500)
- Splash shows: logo + custom name + "PORTABLE" + progress bar + Roblox version

## Tech Stack
- Python 3.11, PyQt5, Pillow, PyInstaller, ctypes (Windows mutex)
- Flask, SQLite (license server)
- HMAC-SHA256 (signed API responses)
