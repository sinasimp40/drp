---
title: Smarter OTA config matching by app name
---
# Smarter OTA Config Matching

## What & Why
When a launcher checks for OTA updates, the server must determine which build config's exe to send back. Currently, the matching logic (`api_update_check`) tries: (1) match by `license_id`, (2) match by `embedded_key`, (3) fall back to the most recently created config. If licenses aren't assigned to configs, step 1 fails and users can receive the wrong exe (e.g. a "DENFI ROBLOX" user gets the "ForUNetHUB ROBLOX" build).

The fix adds the launcher's `APP_NAME` to the update check request and uses it as a matching fallback on the server side, so even without license assignment, users get the correct exe.

## Done looks like
- Launcher sends its `APP_NAME` alongside `key` and `version` in the update check request
- Server uses app_name matching as a fallback step between embedded_key and "most recent config"
- The OTA Status table on the Builds page shows the correct app name for each license
- Users always receive the correct config's exe during OTA updates, even when no license is explicitly assigned to a config

## Out of scope
- Changing the admin panel config assignment UI
- Modifying the manual download flow from the Builds page

## Tasks
1. **Launcher: send APP_NAME in update check** — Add `"app_name": APP_NAME` to the request body in the `check_for_update()` function.
2. **Server: add app_name fallback matching** — In `api_update_check()`, after the embedded_key lookup fails, try matching by `app_name` before falling back to the most recently created config.
3. **Server: use app_name in OTA status** — Ensure the dashboard OTA status section uses app_name matching consistently so the correct config name appears for each license.

## Relevant files
- `launcher.py:728-753`
- `license_server/server.py:1587-1655`
- `license_server/server.py:1775-1824`