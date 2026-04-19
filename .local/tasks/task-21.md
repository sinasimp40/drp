---
title: Trial mode (auto-license + auto-Roblox-bundle)
---
# Trial Mode Zero Setup

## What & Why
Ship a "trial" launcher .exe that any user can run with **zero setup**. On first launch it auto-registers a time-limited license against our server (no key prompt) and auto-downloads + extracts the latest Roblox files bundle from the license server straight into `./RobloxFiles/`, with real-time extraction progress on the existing Horizon splash. The trial .exe is just another `build_configs` row, so the existing "Build All" flow rebuilds it with every launcher version bump automatically.

## Done looks like
- An admin can mark a build config as **"This is the trial config"** and set its trial duration (hours) and per-subnet quota in the dashboard.
- An admin can upload a **Roblox files .zip** from a new "Roblox Bundle" page; the dashboard shows the current bundle version, size, sha256, and upload date.
- A trial .exe handed to a brand-new Windows user (no `.license_key`, no `RobloxFiles/`, no patching) works end-to-end: splash shows **Activating trial → Downloading Roblox files XX/YY MB → Extracting NN/TOTAL → Launching Roblox**, then Roblox starts.
- On a second run, the launcher uses the cached license + cached RobloxFiles and starts in seconds with no downloads.
- When the trial expires, the user sees a friendly "Trial expired — get a full license" screen, NOT a key prompt or a crash.
- A "Build All" rebuild produces a fresh trial .exe alongside every other config, and existing trial users receive the new version through the existing OTA flow.
- The non-trial launcher behavior is **completely unchanged** for existing customers.

## Out of scope
- Payment / checkout flow for upgrading from trial to paid (just a button that opens an external URL).
- Hardware-fingerprint binding of trial licenses (IP-subnet quota only, same as the existing system).
- Differential / patch updates of the Roblox bundle (full re-download when bundle version bumps).
- Localizing splash strings (English only for now, matching current launcher).

## Steps

1. **Schema + migration** — Add `is_trial`, `parent_config_id` to `licenses`; add `is_trial`, `trial_duration_seconds`, `trial_max_per_subnet` to `build_configs`; add a new `roblox_bundles` table for uploaded bundles with version / size / sha256 / file path / uploaded_at. Backfill existing rows with safe defaults so current licenses and configs keep working.

2. **Trial register endpoint** — Add `POST /api/trial_register` that accepts only requests signed with a separate trial-only HMAC secret (so leaks of the trial key cannot mint paid licenses). Looks up the trial build config by `config_id`, enforces the per-/24-subnet quota by counting prior trial licenses for that config, then mints a fresh `active` license with `is_trial=1`, `parent_config_id=cfg.id`, `expires_at = now + cfg.trial_duration_seconds`, returns the key in a signed response. Returns 429 when the subnet quota is hit.

3. **Roblox bundle endpoints + admin upload** — Add admin upload form + page that accepts a .zip, computes sha256, stores it under `license_server/roblox_bundles/v<n>.zip`, and inserts a row marking it as the current bundle. Add `GET /api/roblox_bundle/info` (returns current version, size, sha256, single-use download token) and `GET /api/roblox_bundle/download/<token>` (streams the zip; token TTL ~10 min, single use). Both signed.

4. **Build config form additions** — In the build config create/edit form, add the "This is the trial config" toggle, "Trial duration (hours)" input, and "Max trials per /24 subnet" input. Show a small TRIAL badge on the trial row in the builds list. Enforce that at most one config has `is_trial=1` at a time.

5. **Bake trial flag into launcher at build time** — Update `build_config.py` to patch `IS_TRIAL` and `TRIAL_REGISTER_SECRET` (only set for the trial config) into `launcher.py` the same way it already patches `LICENSE_SERVER_URL` etc. For non-trial builds these stay at their default (`IS_TRIAL = False`).

6. **Launcher: trial branch in startup** — In `main()`, before the existing license check: if `IS_TRIAL` is true and `.license_key` is missing, show splash "Activating trial..." and call the trial-register endpoint, then save the returned key with the existing encrypted save path. If the call returns 429 or fails, show a friendly error on the splash and exit. If the saved key later validates as expired, show a new TrialExpiredDialog (styled like the existing WarningDialog) with "Get Full License" and "Quit" buttons — never the key prompt. Non-trial behavior is untouched.

7. **Launcher: auto Roblox bundle download + real-time extraction on splash** — When `RobloxFiles/RobloxPlayerBeta.exe` is missing OR the cached `RobloxFiles/.bundle_version` is older than the server's, call `/api/roblox_bundle/info`, stream the zip to a temp file with progress driving splash 10–60%, then use `zipfile.ZipFile` with manual per-member extraction in a worker thread that updates a shared state dict; the GUI thread polls and calls `splash.set_progress(60 + 35*done/total, f"Extracting... {done}/{total}")`. Verify sha256, write `.bundle_version`, delete the temp zip. Use the SAME worker-thread + state + `processEvents` pattern that `download_update` already uses — no new dialogs. Non-trial builds keep using `find_system_roblox` + `sync_files`.

8. **Public trial download link** — Add `GET /download_trial` (or similar) that serves the latest completed .exe of the current trial config without requiring auth, with a small per-IP rate limit so it can't be hammered. Show that link on the trial config's row in the dashboard so admin can copy it.

9. **Architect code review** — Have the architect review the full diff focusing on: trial endpoint abuse / embedded secret blast radius, IP-subnet quota bypasses, race between download/extract worker thread and Qt repaint, partial-download resume + corrupt-zip handling, disk-space checks, regression risk for existing non-trial launchers, and whether any existing endpoint behavior changed.

10. **End-to-end testing on a clean folder** — Build a trial .exe via the dashboard, run on a Windows session with no `RobloxFiles/` and no `.license_key`, confirm the full happy path (activate → download → extract → launch). Then run again and confirm the fast path (cached key + cached files). Then admin-expire the license and confirm the TrialExpiredDialog appears. Then trigger Build All and confirm the trial .exe rebuilds and existing trial users receive the OTA. Run the full non-trial launcher path on a separate config to confirm zero regression.

## Architectural constraints
- Everything happens on the **existing Horizon splash** — do NOT introduce any new top-level dialogs for download, extraction, or trial activation. The only new dialog is the post-expiry "Trial expired" screen.
- The trial register endpoint MUST use a different shared secret than the main license API. Leaking the trial .exe should never let an attacker mint paid licenses or call admin endpoints.
- Rate-limiting on `/api/trial_register` is mandatory — without it, anyone can mint unlimited trial keys.
- The schema migration must be **backwards compatible** — existing `.license_key` files, existing licenses, and existing builds must keep working unchanged.

## Relevant files
- `launcher.py:1-50,612-850,1063-1170,1208-1270,2160-2260`
- `license_server/server.py:30-50,125-260,1500-1710,1786-1942,2015-2130,2612-2790`
- `build_config.py`
- `license_server/templates/builds.html`
- `license_server/templates/build_config_form.html`
- `license_server/templates/base.html`
- `build_exe.bat`
- `replit.md`