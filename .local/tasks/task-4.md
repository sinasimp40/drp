---
title: License key file security and server status clarity
---
# License Security & Key File Hardening

## What & Why
Three issues with the current license system:
1. **No clear activation status enforcement** — The server accepts re-validation of already-active keys without clearly distinguishing "first activation" from "already active on another setup". Error messages should clearly tell the user what's happening: "ready to use", "already activated on another device", "expired", "revoked".
2. **License file saved to multiple locations** — Currently saves to ProgramData, AppData, AND the EXE directory. For a diskless cafe setup, the key file should ONLY be in the same folder as launcher.exe so all clients on the server share it.
3. **License file is plaintext** — Anyone can open `.license_key` and read/copy the key. The file should be encrypted so only the launcher can decrypt it.

## Done looks like
- License key file (`.license_key`) is saved ONLY in the same folder as the launcher EXE. No ProgramData or AppData fallback locations. If saving fails, a clear warning is shown.
- The `.license_key` file content is encrypted — opening it in a text editor shows unreadable binary, not the actual key. Only the launcher can decrypt it using a built-in app-specific key.
- Server properly communicates license states: pending (never activated, ready to use), active (currently in use — session lock via IP still applies), expired, revoked.
- The validate endpoint clearly differentiates between first activation and re-validation, with appropriate error messages.
- The `delete_license_files()` function only cleans the single EXE-directory location.
- Dashboard and admin features continue working as before.

## Out of scope
- HWID / hardware binding (not compatible with diskless setups)
- Changes to HMAC signing, heartbeat intervals, or offline grace logic
- Changes to admin login system

## Tasks
1. **Single-location key storage** — Remove `_get_fallback_paths()`, ProgramData, and AppData fallback logic from `load_saved_license()`, `save_license_key()`, and `delete_license_files()`. Save/load only from the EXE directory. Keep the warning message if save fails.

2. **Encrypt the license key file** — Encrypt the key before writing to `.license_key` using XOR with a static app-derived key (same approach as the secret obfuscation). Decrypt on load. The file should not contain readable text.

3. **Improve server status responses** — Make the validate endpoint return clear, distinct error messages for each state: "License not found", "License already activated" (when active and session-locked by different IP), "License expired", "License revoked". Ensure pending keys activate cleanly and active keys re-validate properly for the same IP/session.

## Relevant files
- `launcher.py:536-610`
- `launcher.py:800-850`
- `launcher.py:866-900`
- `license_server/server.py:184-270`
- `license_server/server.py:40-51`