# OTA Update System with Server-Side Builds

## What & Why
Add a full OTA (over-the-air) update system so the admin can push launcher code updates to all users automatically. Each user has a unique .exe build (different app name, icon, file path), so the server must store per-user build configs, run PyInstaller to produce personalized .exe files, and serve them to each user's launcher on startup. The admin needs real-time visibility into build progress and user update status via WebSocket.

## Done looks like
- Admin dashboard has a "Builds" page where each user's build config is stored (app name, icon, hardcoded path, license key, shared secret)
- Admin can set a version number (e.g. "1.1.0") and upload updated source code, then hit "Build All" to trigger server-side builds
- Each user's build shows real-time progress (1% increments) on the admin dashboard via WebSocket — no page refresh needed
- Build progress bar fills smoothly as PyInstaller runs for each user config
- Launcher checks server version on startup (during splash screen "Checking for updates...") and downloads its personalized .exe if a newer version exists
- Download progress is reported back to the server so the admin sees each user's download percentage in real time via WebSocket
- Launcher self-replaces using a temp file + batch script swap (Windows limitation: can't overwrite a running .exe)
- Dashboard and history pages show each user's current launcher version (sent via heartbeat)
- Admin can see at a glance: who's updated, who's still on an old version, who's currently downloading
- Version number is admin-chosen (not auto-incremented)
- Existing license system, heartbeat, IP binding, and suspended logic remain fully intact — no regressions

## Out of scope
- Auto-building when source code is uploaded (admin manually triggers "Build All")
- Rollback to previous versions
- Delta/patch updates (full .exe replacement only)
- Building for non-Windows platforms

## Tasks
1. **Database schema for build configs and versions** — Add tables for storing per-user build configurations (app name, icon path, hardcoded path, embedded license key, shared secret) and version metadata (version number, source code path, build status per config). Migrate existing DB safely.

2. **Admin build config management pages** — Add admin pages to create/edit/delete build configs (one per user/launcher variant). Each config stores: display name, app name, icon file (uploaded), hardcoded path, license server URL, shared secret, and embedded license key. Add icon file upload handling with storage on disk.

3. **Server-side build engine** — Implement a background build system that runs PyInstaller for each build config using the uploaded source code and each config's settings. Use `build_config.py` and `convert_icon.py` logic to patch `launcher.py` before each build. Track build progress by parsing PyInstaller output and mapping it to a 0-100% scale. Store completed .exe files on disk organized by config ID and version.

4. **WebSocket integration for real-time build progress** — Add Flask-SocketIO (or similar) WebSocket support. Broadcast build progress events (per-config percentage, overall count) to connected admin clients. Broadcast download progress events when users download updates. Admin dashboard JS connects to WebSocket and updates progress bars live.

5. **Admin builds dashboard page** — Create the "Builds" page showing: version input field, "Build All" button, per-config build status with progress bars, overall progress counter, and post-build status (ready/failed). After builds complete, show each user's update status (waiting/downloading with %/updated). Include current version column in the main dashboard and history tables.

6. **Launcher version check and OTA download** — Add version check to launcher startup (during splash screen). Launcher sends its current APP_VERSION to a new `/api/update_check` endpoint. If server has a newer version, launcher downloads the .exe from `/api/download_update` while reporting progress back to the server. Self-replacement uses a temp .bat script that waits for the old process to exit, replaces the .exe, and relaunches.

7. **Heartbeat version reporting** — Extend heartbeat payload to include APP_VERSION. Server stores the reported version per license. Dashboard displays each user's running version in real time.

8. **Build status and download progress API endpoints** — Add endpoints: `/api/update_check` (launcher checks version), `/api/download_update/<config_id>` (launcher downloads .exe with chunked transfer), `/api/report_download_progress` (launcher reports download % back to server for admin visibility), `/api/build_status` (admin polls or WebSocket pushes build state).

## Relevant files
- `license_server/server.py`
- `license_server/templates/base.html`
- `license_server/templates/dashboard.html`
- `license_server/templates/history.html`
- `launcher.py`
- `build_config.py`
- `build_exe.bat`
- `convert_icon.py`
- `requirements.txt`
