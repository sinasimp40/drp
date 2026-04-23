---
title: Build verification and OTA download safety checks
---
# Build Verification and OTA Download Safety

## What & Why
User reports that after rebuilding all configs and downloading the DENFI ROBLOX exe, the launcher shows "ForUNetHUB ROBLOX" splash and wrong icon. Most likely cause is the OTA update replacing the exe with the wrong config's build (since matching was broken before Task #7 fix). However, we must also verify the build process itself correctly isolates each config, and add safeguards so this cannot happen again.

## Done looks like
- Build process logs which APP_NAME and icon are being used per config for traceability
- After build, each exe is verified to contain the correct APP_NAME string
- OTA update check now also validates that the server's response config matches the launcher's own APP_NAME before accepting the update — preventing a wrong-config exe from ever being installed
- Build download buttons on the admin page clearly show which config each download belongs to

## Out of scope
- Changing the build parallelism model (ThreadPoolExecutor is fine)
- Admin panel UI redesign

## Tasks
1. **Add build verification** — After PyInstaller produces the exe, read the binary and verify it contains the expected APP_NAME string. Log a warning if mismatched. Also log which icon_filename and app_name are being built for each config at the start of the build.
2. **Add OTA client-side safety check** — In the launcher's update check flow, if the server response includes config metadata (like app_name), verify it matches the launcher's own APP_NAME before proceeding with the download. Add an `app_name` field to the update check response from the server so the launcher can verify.
3. **Preserve exe filename during OTA swap** — When the OTA update replaces the current exe, ensure the new exe keeps the original filename (not the downloaded artifact's name), so a DENFIROBLOX.exe stays as DENFIROBLOX.exe even after update.

## Relevant files
- `launcher.py:728-755`
- `launcher.py:782-860`
- `license_server/server.py:907-1070`
- `license_server/server.py:1587-1660`