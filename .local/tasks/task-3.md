---
title: Harden license activation with HWID binding and encrypted key file
---
# Harden License Activation & Key Security

## What & Why
The current license system has three problems:
1. **No device binding** — An activated license key can be reused from any new launcher build. The server only tracks IP for session locking but doesn't bind a key to a specific machine. If someone gets a key, they can use it from any PC.
2. **License file stored in multiple locations** — The `.license_key` file is saved to ProgramData, AppData, AND the EXE directory. For a diskless cafe setup, it should ONLY be next to the launcher EXE so all clients share it from the server.
3. **License file is plaintext** — Anyone can open `.license_key` and copy the key. It should be encrypted so only the launcher can read it.

## Done looks like
- Server tracks a **hardware ID (HWID)** for each activated license. When a key is activated, the launcher sends a machine fingerprint. The server stores it.
- On subsequent validations, the server checks the HWID matches. If a different machine tries to use an already-activated key, the server rejects it with a clear "License already registered on another device" error.
- The admin dashboard shows the registered HWID for each license and has a "Reset HWID" button so the admin can unbind a key if a customer changes machines.
- License key file is saved ONLY next to the EXE (single location, no ProgramData/AppData fallbacks). If save fails, a warning is shown.
- The `.license_key` file content is encrypted/obfuscated using a machine-derived key so it can't be copied to another PC and can't be read in plaintext.
- License status responses from the server clearly differentiate: `pending` (never activated), `active` (bound to a device), `expired`, `revoked`.
- The validation flow: no key file → prompt user → server checks if pending (activate + bind HWID) or already activated (reject if different HWID) → save encrypted key file.

## Out of scope
- Changing the HMAC signing or API structure
- Modifying the admin login system
- Changing the heartbeat interval or offline grace logic

## Tasks
1. **Generate HWID on launcher** — Create a machine fingerprint function that combines hardware identifiers (machine GUID from Windows registry, volume serial, computer name) into a stable hash. This HWID is sent with every validate/heartbeat request.

2. **Server HWID binding** — Add `hwid` column to the licenses table. On first activation (pending→active), store the HWID. On subsequent validations, reject if HWID doesn't match. Add a "Reset HWID" API endpoint for admin use.

3. **Admin dashboard HWID support** — Show the registered HWID (truncated) on the dashboard for each active license. Add a "Reset HWID" button that clears the binding so the key can be activated on a different machine.

4. **Single-location key storage** — Remove ProgramData and AppData fallback paths. Save `.license_key` only next to the EXE. Keep the warning message if save fails.

5. **Encrypt the license key file** — Encrypt the key file content using a machine-derived key (based on HWID components) so the file can't be read in plaintext and can't be copied to another machine. The launcher decrypts on load.

## Relevant files
- `launcher.py:538-610`
- `launcher.py:800-850`
- `launcher.py:860-900`
- `license_server/server.py:40-51`
- `license_server/server.py:184-270`
- `license_server/templates/dashboard.html`
- `build_config.py`