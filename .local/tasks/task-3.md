---
title: Sticky trial expiry + premium-build Roblox bundle fallback
---
# Launcher License + Bundle Overhaul

## What & Why
Today the launcher behaves inconsistently between trial and full‑license builds:

- When a **trial** expires, the launcher deletes the local key file. That makes it trivial to "reset" by just re‑launching, which is the opposite of what we want for trials.
- When a **paid license** expires, deleting the key file is the right behavior (so the user is prompted for a new key), and we want to keep that.
- Only **trial** builds know how to download Roblox files from our server. Full‑license builds rely on the user already having Roblox installed locally or on a hardcoded path baked into the build config — which means the admin has to know/set a path per machine and, if files are missing, the launcher just fails.

This task makes trial expiry "sticky" (hard to reset without nuking the install folder), keeps paid‑license expiry behavior as‑is, and brings the trial's auto‑download‑and‑extract Roblox bundle flow to paid builds as a fallback so the admin never has to worry about file paths or whether Roblox is installed.

The server already supports per‑license duration (`expires_at` / `duration_seconds`) and the heartbeat enforces it, so the "admin sets how many days" piece is already wired — no changes needed there beyond confirming it works end‑to‑end.

## Done looks like
- **Trial expired**: launcher shows the existing "Trial Ended" dialog. The hidden `.license_key` file is **kept**, marked as "trial-exhausted" so re‑launching does not silently issue a new trial and does not prompt for a new key. The only way to start a fresh trial is to delete the launcher folder entirely.
- **Paid license expired or revoked**: launcher deletes the local key file and on next run prompts the user for a new license key (current behavior preserved). Suspended licenses still keep the file so the user auto‑recovers when admin un‑suspends.
- **Paid build, Roblox files missing or incomplete**: launcher downloads the latest Roblox bundle from the server (same `/api/roblox_bundle/info` + `/download/<token>` flow trial uses today), verifies SHA‑256, extracts into the launcher's `RobloxFiles` folder, and continues. If a system Roblox install is found, the existing sync path still runs and stays the preferred update source.
- **Paid build, files already present and current**: behavior is unchanged from today (no unnecessary re‑downloads — the `.bundle_version` marker is honored).
- Admin creates a license with N days in the dashboard → launcher honors that duration via the existing heartbeat/expiry flow. No manual file path needs to be set on the build config for the bundle fallback to work.
- No regressions in: trial registration, suspended‑license recovery, embedded‑key builds, HMAC request signing, splash UI/progress, or the admin dashboard.

## Out of scope
- Redesigning the admin dashboard or launcher UI.
- Changing the build/PyInstaller pipeline itself.
- Adding new server endpoints (we reuse `/api/roblox_bundle/info` and `/api/roblox_bundle/download/<token>`).
- Multi‑bundle / per‑build‑config bundles (still one shared latest bundle).
- Removing `hardcoded_path` from build configs — it stays as an optional override.

## Steps
1. **Make trial expiry sticky on the launcher.** Stop deleting `.license_key` when a trial expires; instead, write a small "trial exhausted" marker (hidden + system attrs like the key file) next to it. On startup, if that marker is present, skip auto trial registration and go straight to the Trial Ended dialog. Suspension path is unchanged.

2. **Preserve paid‑license expiry behavior.** Confirm the current "delete key on expired/revoked, keep on suspended" branch for non‑trial, non‑embedded builds still runs and is covered by the new logic. Add a short comment so the intent is obvious.

3. **Add bundle fallback for paid builds.** Extend the splash‑screen step that currently only runs for trials so paid builds also call the existing `download_and_extract_roblox_bundle(...)` when `RobloxPlayerBeta.exe` is missing from the resolved Roblox folder, or when no system Roblox install is found and the local folder has no `.bundle_version`. System‑roblox sync remains the primary update path when a system install exists.

4. **Make the bundle fallback work without `hardcoded_path`.** Ensure `get_paths()` returns a sensible writable Roblox folder for paid builds even when no `hardcoded_path` is configured (today it already falls back to `APP_DIR/RobloxFiles` — verify and document). The admin should be able to leave `hardcoded_path` blank in the build config and still get a working launcher.

5. **Confirm the admin "set N days" flow end‑to‑end.** No code change expected: verify that creating a paid license with a chosen duration in the dashboard results in the launcher locking out at the right time via the existing heartbeat. Note any gap found and fix only if trivial.

6. **Bump `requirements.txt` hygiene.** While we're here, dedupe the duplicate `flask` lines so future installs are clean. (Cosmetic; do not change pinned versions.)

7. **Run a code review pass.** After implementation, call the architect with a diff of the launcher + server changes to catch security/regression risks (HMAC handling, file‑deletion edge cases, trial‑abuse vectors). Fix any high‑severity findings before declaring done.

8. **Test in this environment.** Start the license server, exercise: (a) create a paid key with a short duration and validate via curl/heartbeat, (b) confirm the bundle info + download endpoints respond, (c) static‑analyze the launcher changes since we can't run PyQt5 here. Document any limitations.

## Architectural notes
- Keep the trial‑exhausted marker logic launcher‑side only — do not invent a new server endpoint. The server already refuses re‑use of an expired trial key; the marker just prevents the client from silently asking for a new one.
- Do not change the on‑wire HMAC signing format or the bundle token contract — both are shared with already‑built launcher executables in the wild.
- The bundle fallback must be strictly additive: if a system Roblox install is present and current, the existing sync path wins (faster, no network).

## Relevant files
- `launcher.py:27-30`
- `launcher.py:62-87`
- `launcher.py:1075-1180`
- `launcher.py:1280-1530`
- `launcher.py:2240-2305`
- `launcher.py:2440-2510`
- `license_server/server.py:81-145`
- `license_server/server.py:198-260`
- `license_server/server.py:500-560`
- `license_server/server.py:1532-1600`
- `license_server/server.py:1974-2050`
- `license_server/server.py:2200-2320`
- `build_config.py`
- `requirements.txt`