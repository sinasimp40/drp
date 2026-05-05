# License, Build, and Sync Fixes

  ## What & Why
  Three issues need fixing:
  1. **Shared license abuse** — Two people can use the same key simultaneously with no restriction. Need single-session enforcement so only one person can use a key at a time.
  2. **Stale icon during build** — The icon conversion skips if icon.ico already exists, and PyInstaller caches old builds. Users replacing their PNG see the old icon persist.
  3. **Roblox sync robustness** — The sync logic works but needs hardening: better error messages if files are locked, and verification that the sync completed correctly.

  ## Done looks like
  - If someone tries to use a license key that's already in use from a different IP, they get rejected with a clear error ("License already in use on another device")
  - The original user keeps working uninterrupted
  - If the original user disconnects (heartbeat timeout), the key becomes available again
  - Building the launcher always picks up the latest icon image — replacing a PNG and rebuilding shows the new icon every time
  - PyInstaller build cache is cleaned before each build
  - Roblox sync handles locked files gracefully with clear error messages
  - Sync verifies RobloxPlayerBeta.exe exists in the portable folder after sync completes

  ## Out of scope
  - HWID binding (hardware ID lock) — not adding this, IP-based session lock is sufficient
  - HTTPS/SSL for the license server
  - Auto-update mechanism for the launcher itself

  ## Tasks

  1. **Single-session enforcement on server**
     - On validate: if key is active and last heartbeat is recent (< 5 min) from a different IP, reject with "License already in use"
     - On heartbeat: same check — reject if IP doesn't match the active session IP
     - If heartbeat times out (user goes offline for 5+ min), the key becomes available for any IP again
     - Pending keys activate normally regardless of IP (first come first served)
     - Update dashboard to show session IP clearly

  2. **Fix icon conversion caching**
     - In convert_icon.py: remove the early-return check for existing icon.ico — always reconvert from source image if a source image exists
     - In build_exe.bat: remove the "if exist icon.ico skip" check — always run convert_icon.py
     - Add --clean flag to the PyInstaller command to clear build cache
     - Delete build/ and dist/ folders at the start of build_exe.bat for a clean slate
     - Add priority: if icon.png exists, prefer it over random images in the folder

  3. **Harden Roblox sync**
     - Add file-in-use detection: if shutil.copy2 fails with PermissionError, show a clear message ("Close Roblox before syncing")
     - After sync completes, verify RobloxPlayerBeta.exe exists in the portable folder
     - Add a retry mechanism (up to 3 attempts with short delay) for individual file copy failures
     - Log which files were synced and which failed

  4. **Update launcher license validation for session enforcement**
     - Handle new "License already in use" error from server — show it clearly in the license dialog instead of a generic error
     - Don't delete the .license_key file on "already in use" error (it's not expired/revoked, just busy)

  ## Relevant files
  - `license_server/server.py`
  - `launcher.py`
  - `build_exe.bat`
  - `convert_icon.py`
  - `license_server/templates/dashboard.html`
  - `license_server/templates/history.html`
  