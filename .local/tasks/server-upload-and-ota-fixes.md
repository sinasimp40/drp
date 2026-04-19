# Server.py Upload & OTA Auto-Update Fixes

## What & Why
The admin currently can only upload `launcher.py` from the Builds page, but not `server.py`. When server-side fixes are made (like the update_check fallback), the user has to manually copy `server.py` to their Windows machine. Adding a server.py upload feature with auto-restart lets the admin update the server from the browser.

Additionally, the update_check endpoint and OTA status panel have already been fixed in the codebase but need final verification: the update_check now falls back to any available build config when no linked license or embedded key is set, and the OTA status panel now shows all active licenses regardless of linking.

## Done looks like
- Builds page has a "Server Source" section alongside "Launcher Source" showing current server.py version/info
- Admin can upload a new server.py which replaces the running one and auto-restarts the server
- The upload validates the file is a valid server.py before replacing
- After restart, the admin is redirected back to the Builds page
- The update_check fallback (find any build config if none linked) works correctly so launchers without linked licenses can auto-update
- OTA status panel shows all active licenses with their versions, no linking required

## Out of scope
- Automatic syncing between Replit and the Windows server
- Multiple server file uploads (only server.py)

## Tasks
1. **Add server.py upload endpoint** — Create a POST route `/api/upload_server` that accepts a server.py upload, validates it contains expected server markers, saves it over the current server.py, and schedules a server restart.

2. **Add server info endpoint** — Create GET route `/api/server_info` that returns the current server.py file size, modified date, and detected version if any.

3. **Add Server Source UI section** — Add a card on the Builds page (similar to the Launcher Source card) showing current server.py info and an upload form. The card should show file size and last modified time.

4. **Server auto-restart after upload** — After saving the new server.py, schedule a delayed restart of the server process so the response can be sent before the server stops.

## Relevant files
- `license_server/server.py:1286-1351`
- `license_server/templates/builds.html:12-29`
- `license_server/templates/builds.html:345-373`
