# License System for Roblox Launcher

## What & Why
Add an online license validation system so only authorized users can run the launcher. The license server runs on the user's RDP server (144.31.48.238:3842) and provides an admin dashboard to manage keys, track usage, and control access in real-time. The launcher checks in periodically and locks itself when the license expires.

## Done looks like
- License server runs on port 3842 with an admin dashboard
- Admin can create license keys with custom duration (minutes, hours, days)
- Admin dashboard shows: who's online, remaining time, license key, active/expired/deleted status
- License history page showing all keys ever created with their status
- Admin can delete/revoke any license key instantly
- Launcher prompts for license key on first run, validates it online
- Launcher re-checks the license every few minutes while running
- When license expires or is revoked, launcher shows a lock screen and stops Roblox
- License key is stored locally so user doesn't re-enter it each time
- Server responses are signed to prevent tampering
- Communication uses a shared secret so fake servers can't be spoofed

## Out of scope
- Payment/billing integration
- User registration/accounts (admin manages keys directly)
- HWID binding (not suitable for diskless/cafe setups)

## Tasks

1. **License server backend** — Build a Flask web API with SQLite database. Endpoints: create key (with duration), validate key (returns signed response with time remaining), heartbeat (periodic check-in), revoke key, list all keys. Include a shared secret for request signing.

2. **Admin dashboard** — Web UI served by the same Flask app. Pages: create new license (pick duration), active licenses table (key, user online status, time remaining, actions), license history (all keys with status: active/expired/deleted). Clean dark theme with orange accents matching the launcher branding.

3. **Launcher license integration** — On startup, before any Roblox logic, check for stored license key. If none, show a license key input dialog. Validate key with server. If valid, proceed to normal launch flow. If invalid/expired, show lock screen. While running, re-check every 2-3 minutes. If check fails (expired/revoked), show lock screen and quit Roblox.

4. **Anti-bypass protections** — Server signs responses with HMAC using a shared secret embedded in the launcher. Launcher verifies signature before trusting response. Key validation requires server to be reachable (no offline grace). Obfuscate the shared secret in the built executable.

5. **Build system updates** — Update build_exe.bat to ask for the license server URL during build (default: http://144.31.48.238:3842). Bake the server URL into the launcher via build_config.py. Add server files to the project with instructions for deploying on the RDP.

## Relevant files
- `launcher.py`
- `build_exe.bat`
- `build_config.py`
