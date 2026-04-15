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
- License server runs on your server (set URL during build)
- Admin dashboard — create keys, monitor online users, revoke access
- Dashboard updates live every 5 seconds via AJAX (no page reload), with real-time countdown timers
- New keys start as **Pending** — countdown only begins when someone actually activates the key
- Launcher prompts for license key on first run, saves encrypted `.license_key` file next to the EXE
- **Embedded key mode**: bake a license key into the EXE at build time — perfect for diskless setups
- Key file is **encrypted** (XOR with app-derived key) — raw binary, cannot be read in a text editor, only the launcher can decrypt it
- Key file saved **only** next to the EXE — no ProgramData/AppData fallbacks (diskless-friendly: all clients share one file)
- Validates with server before launching, re-checks every 15 seconds for near-instant revocation
- Server returns clear status: "License has expired", "License has been revoked", "License suspended", etc.
- One-time activation: once a key is activated (pending → active), it cannot be activated again
- **IP binding**: first activation records the client IP (`registered_ip`); subsequent heartbeats and validations check against it. If IP changes, license is auto-suspended.
- **Suspended state**: suspended licenses block usage until an admin unsuspends them. Unsuspending resets the license to pending with cleared IP, allowing re-activation from a new IP.
- Heartbeats keep the running session alive
- Dashboard shows registered IP alongside last-seen IP for each license
- **Unsuspend button**: admin can unsuspend a suspended license from the dashboard or history page
- If license expires, is revoked, or is suspended: shows lock screen, kills Roblox
- Suspended licenses do NOT delete the `.license_key` file (so user can reconnect after unsuspend)
- Offline grace: 3 consecutive server failures tolerated before locking (prevents brief network blips from killing sessions)
- Fatal error grace: 3 consecutive fatal/suspended errors required before locking (prevents single-request glitches from killing sessions)
- Server signs responses with HMAC to prevent tampering
- Optional: leave license server URL blank during build to disable checking

## Multi-Instance Flow
1. Run exe → validates license → clears rbx-storage.db → grabs mutex → launches Roblox (fresh, not logged in)
2. Log into Account A
3. Run exe again → clears rbx-storage.db → grabs mutex → launches second Roblox (fresh)
4. Log into Account B
5. Both stay open because both launchers hold the mutex in background
6. Close Roblox → launcher detects it → clears rbx-storage.db → exits

### Lock File (Multi-Instance Race Condition Fix)
- A `.launcher_lock` file prevents race conditions when two launcher instances start within seconds
- The lock contains PID and timestamp; if the lock is < 10 seconds old and the PID is alive, the second instance skips re-prompting for a license
- Lock is released after Roblox launches successfully

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
- **launcher.py** — Main application (license check, splash screen, auto-sync, login clear, mutex, auto-launch, lock file)
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
8. Enter the shared secret (or press Enter for default)
9. **For diskless setups**: Enter a license key to embed, or press Enter to skip (users will enter manually)
10. Get `{YourName}.exe` from `dist\` folder

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

## License Statuses
- **pending** — created, not yet activated
- **active** — activated and running, countdown in progress
- **expired** — time ran out
- **revoked** — admin manually revoked
- **deleted** — admin deleted (soft delete)
- **suspended** — IP mismatch detected, waiting for admin unsuspend
