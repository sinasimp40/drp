# Portable Roblox Launcher

## Recent Changes
- **2026-04-18 — Update progress dialog:** During a launcher self-update download, a dedicated frameless `UpdateProgressDialog` now appears instead of relying on the splash status line. Shows app name, target version, MB downloaded / total, percentage, a real `QProgressBar`, and a prominent "Update in progress — please don't close this window" warning. Splash is hidden while the dialog is up; the dialog stays visible through downloading → installing → restarting phases. On download failure or apply failure, the dialog closes cleanly and the splash returns so the launcher continues normally. Close button / Esc are intentionally swallowed during the update so users can't accidentally interrupt and corrupt the swap. Files: `launcher.py` (`UpdateProgressDialog` class, `main()` update flow).
- **2026-04-18 — Telegram backups:** New `/backups` admin page lets the operator save a Telegram bot token + chat ID and pick a schedule (Off / Every N hours / Daily HH:MM / Weekly day+time). A daemon thread (`telegram_backup.start_scheduler`) wakes every minute and uploads `licenses.db` via the Telegram Bot API (`sendDocument`) using only the standard library — no new pip deps. Settings persist in `license_server/backup_settings.json`; bot token is masked in the UI with a "Replace" affordance. Buttons: **Test Connection** (sends a chat message), **Send Backup Now** (uploads immediately). Last 10 attempts shown with status + message; failures retry once. Routes return JSON when called via XHR, HTML redirects otherwise.
- **2026-04-17 — Admin panel redesign (Sidebar SaaS):** Replaced top-navbar layout with a persistent left sidebar + topbar shell (vanilla CSS in `base.html`, lucide icons inlined as SVG). Dashboard gained a 4-card KPI strip (Total / Online / Suspended / Expiring<24h), icon-button row actions, and a fix for the live `TypeError: 'NoneType' - 'float'` crash that triggered when an active license had `expires_at=NULL` (`server.py` `dashboard()` and `api_dashboard_data()`). Restyled history, builds, create, build_config_form, and login pages. Mobile (<900px) collapses the sidebar to a hamburger drawer; KPI strip stacks; tables scroll horizontally. All existing JS hooks, polling, search, bulk-edit modal, Recover Suspended, and per-row actions preserved. e2e tested green.

## Overview
A zero-interaction portable Roblox launcher. Double-click the .exe and it does everything automatically:
1. Validates license key with online server (if configured)
2. Checks for OTA updates and auto-updates if available
3. Shows custom-named splash screen (e.g. "DENFI ROBLOX PORTABLE")
4. Auto-syncs Roblox files if an update is detected on the system
5. Clears login data (rbx-storage.db) so each instance starts fresh
6. Grabs the Roblox mutex to allow multiple instances
7. Launches Roblox from the portable folder
8. Stays running in background to hold the mutex, cleans up login on exit

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
- Validates with server before launching, re-checks every 10 seconds for near-instant revocation
- Server returns clear status: "License has expired", "License has been revoked", "License suspended", etc.
- One-time activation: once a key is activated (pending → active), it cannot be activated again
- **IP binding (subnet-based)**: first activation records the client IP (`registered_ip`); subsequent heartbeats and validations check the first 3 octets (e.g., 103.188.86.x). IPs in the same /24 subnet are allowed — different subnets trigger suspension. This supports diskless setups where PCs share a subnet but have different last octets.
- **Suspended state**: suspended licenses block usage until an admin unsuspends them. Unsuspending resets the license to pending with cleared IP, allowing re-activation from a new IP.
- Heartbeats keep the running session alive and report launcher version
- Dashboard shows registered IP alongside last-seen IP and launcher version for each license
- **Unsuspend button**: admin can unsuspend a suspended license from the dashboard or history page
- If license expires, is revoked, or is suspended: shows lock screen, kills Roblox
- Suspended licenses do NOT delete the `.license_key` file (so user can reconnect after unsuspend)
- Offline grace: 3 consecutive server failures tolerated before locking (prevents brief network blips from killing sessions)
- Fatal error grace: 3 consecutive fatal/suspended errors required before locking (prevents single-request glitches from killing sessions)
- Server signs responses with HMAC to prevent tampering
- Optional: leave license server URL blank during build to disable checking

## OTA Update System
- **Server-side builds**: Admin configures per-user build configs (app name, icon, Roblox path, license key embedded)
- **Build configs**: Each config links to a license — the license key gets baked into the .exe as EMBEDDED_LICENSE_KEY
- **Build engine**: Server runs PyInstaller per config, patches launcher.py source with config values, produces personalized .exe files
- **Version management**: Admin enters version number (X.Y.Z format) and triggers "Build All" — builds every config
- **Config-change detection**: Each build stores a config_hash (SHA256 of config fields). When a client checks for updates, the server compares config hashes — if the config changed (new icon, path, etc.), the launcher auto-updates even without a version bump
- **Single-config rebuild**: Admin can click "Rebuild" on individual build configs to rebuild just that one client's launcher using the latest version, without rebuilding all configs
- **Build progress**: Real-time progress tracking via WebSocket (Flask-SocketIO) + HTTP polling fallback — admin sees per-config progress bars on the Builds page
- **Launcher OTA**: After license check, launcher calls `/api/update_check` with current version + config_hash. If update available (new version OR config changed), downloads new .exe with progress shown on splash screen
- **Self-replace**: On Windows, launcher writes a .bat script that waits for process exit, swaps old/new exe, relaunches
- **Download tokens**: Update check returns a short-lived token (10 min) for downloading, no signing needed on the download request
- **Admin download**: Admin can download built artifacts directly from the Builds page
- **Version display**: Dashboard and History pages show each user's current launcher version
- **OTA status panel**: Builds page shows per-user update states (outdated/downloading/updated) with download progress
- **Download progress reporting**: Launcher reports download progress back to server via `/api/report_download_progress`
- **SHA-256 verification**: Launcher verifies SHA-256 hash of downloaded binary before applying update
- **Build skipping**: Only active licenses get built; pending, suspended, expired, revoked, deleted licenses are skipped

### OTA Database Tables
- `build_configs` — per-user build configuration (app_name, hardcoded_path, icon, license_server_url, license_secret, linked license_id)
- `builds` — build runs (version, status, progress, timestamps)
- `build_artifacts` — per-config results within a build (exe filename, file size, status, progress, config_hash)
- `licenses.launcher_version` — tracks each launcher's reported version from heartbeats

### OTA API Endpoints
- `POST /api/update_check` (signed) — launcher checks for updates
- `GET /api/download_update/<token>` — launcher downloads new .exe
- `POST /build_config/<config_id>/rebuild` (admin) — rebuild single config with latest version
- `POST /api/trigger_build` (admin) — triggers build for all configs
- `GET /api/build_status/<build_id>` (admin) — poll build progress
- `GET /api/build_status_all` (admin) — check if any active build
- `GET /api/download_artifact/<build_id>/<config_id>` (admin) — download built .exe
- `POST /api/report_download_progress` — launcher reports download % back to server
- `GET /api/ota_status` (admin) — per-user OTA state (outdated/downloading/updated), resolves version via embedded_key fallback
- `POST /api/upload_launcher` (admin) — upload launcher.py source file for builds
- `GET /api/launcher_info` (admin) — returns detected version, app name, size, modified time of current launcher.py
- `POST /api/upload_server` (admin) — upload server.py, creates backup, auto-restarts server after 3 seconds
- `GET /api/server_info` (admin) — returns size, modified time of current server.py

### Build File Storage
- Built .exe files stored at: `license_server/builds/<version>/<config_id>/<ExeName>.exe`
- Icons stored at: `license_server/build_icons/<filename>.ico`
- Temp work directories cleaned up after each build

## Multi-Instance Flow
1. Run exe → validates license → checks for updates → clears rbx-storage.db → grabs mutex → launches Roblox (fresh, not logged in)
2. Log into Account A
3. Run exe again → clears rbx-storage.db → grabs mutex → launches second Roblox (fresh)
4. Log into Account B
5. Both stay open because both launchers hold the mutex in background
6. Close Roblox → launcher detects it → clears rbx-storage.db → exits

### Single-Instance Lock & Update Safety
- Real Windows kernel mutex (`CreateMutexW`, name scoped to install path hash) enforces one launcher per install. The OS releases it automatically on crash/exit.
- If a second launcher starts while one is already running, it shows a brief "Launcher is already running" / "Update in progress — please wait" splash and exits cleanly.
- Mutex is released only after Roblox launches successfully, so the user can re-run the launcher to start additional Roblox sessions.
- `.update_state` JSON file (pid, phase, target_version, started_at, last_heartbeat) is the dedicated update gate. A background heartbeat thread refreshes it every 15s while downloading/applying. Stale gates (dead PID or heartbeat > 120s) are cleared at startup.
- Update swap is atomic: stage `current.exe.new`, `os.replace` current → `.bak`, `os.replace` `.new` → current, with rollback if the second step fails. `current.exe` is never left missing.
- After applying the update, the new exe is spawned with `--post-update-restart`; the child retries mutex acquisition for up to 10 s to ride over the brief overlap with the exiting parent.
- Startup recovery restores `current.exe` from `.bak` if the previous run was killed mid-swap.

## Folder Structure
```
YourChosenFolder\
  RobloxPlayerBeta.exe   <- Roblox files live here
  Cache\                 <- Portable Roblox data
  Logs\                  <- Launch logs

license_server\          <- Deploy this to your RDP
  server.py              <- Flask license server + admin dashboard + OTA build engine
  templates/             <- Dashboard, History, Builds HTML templates
  licenses.db            <- SQLite database (auto-created)
  builds/                <- Built .exe artifacts (auto-created)
  build_icons/           <- Uploaded icons (auto-created)
  DEPLOY.md              <- Deployment instructions
```

## Files
- **launcher.py** — Main application (license check, OTA update, splash screen, auto-sync, login clear, mutex, auto-launch, lock file)
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
Quick: copy `license_server/` to your RDP, `pip install flask flask-socketio Pillow pyinstaller`, `python server.py`
Place `launcher.py` either next to or inside the `license_server/` folder — the server checks both locations.

## Theme
- Background: black (#0a0a0a)
- Accent: orange (#ff6a00), lighter (#ff8c33), darker (#cc5500)
- Splash shows: logo + custom name + "PORTABLE" + progress bar + Roblox version

## Tech Stack
- Python 3.11, PyQt5, Pillow, PyInstaller, ctypes (Windows mutex)
- Flask, Flask-SocketIO, SQLite (license server)
- HMAC-SHA256 (signed API responses)

## License Statuses
- **pending** — created, not yet activated
- **active** — activated and running, countdown in progress
- **expired** — time ran out
- **revoked** — admin manually revoked
- **deleted** — admin deleted (soft delete)
- **suspended** — IP mismatch detected, waiting for admin unsuspend
