# Sticky Trial Key + Auto-Provision Build Mode

  ## What & Why
  Three related changes to the launcher + license server, planned together because they touch the same code paths (launcher.py expiry handlers + build_configs schema/form):

  1. **Sticky trial key on expiry** — When a TRIAL build's license expires or is rejected, the launcher must NOT delete the saved hidden `.license_key`. Today it deletes the file, which (combined with subnet quota) is the only thing stopping a user from getting a brand-new trial by re-launching. We want the file to persist so the only way to "reset" is to delete the entire launcher folder. Server-side subnet quota stays as a second line of defense.

  2. **Confirm "delete on expiry" for non-trial manual-key builds** — Today this already happens (line ~2289 `delete_license_files()` is called only when `not EMBEDDED_LICENSE_KEY`). Verify this branch still fires correctly after the trial change above, and ensure on next launch the user sees the LicenseDialog asking for a new key. The admin History page already shows the expired status (no UI change needed).

  3. **NEW "Managed" build mode** (a.k.a. Auto-Provision) — A non-trial build that:
     - Auto-mints a license key on first launch with a duration set in **DAYS** (admin chooses, e.g. 30 days)
     - Auto-downloads + extracts the Roblox bundle from the server (same machinery as trial)
     - Extracts files directly into the launcher folder (no `RobloxFiles` subfolder)
     - Optional subnet quota (default: unlimited, since this is the paid flow)
     - On expiry: deletes the saved key like a normal manual build, so the launcher prompts for a new key the user can buy/get from the developer
     - Mutually exclusive with TRIAL mode in the same build_config

     This removes both manual steps the developer does today: (a) creating a license key by hand and emailing it, and (b) telling the user where to install Roblox. The developer just uploads a bundle once, sets "Managed: 30 days", rebuilds, and shares the public download link. Each user who downloads gets their own auto-issued key tied to their machine/IP.

  ## Done looks like
  - A trial .exe whose timer ran out shows the "Trial Expired – Contact developer" dialog every relaunch and never auto-mints a new trial, even if subnet quota would allow it. Deleting the launcher folder (and re-downloading) is the only reset.
  - A non-trial manual-key .exe whose key expired starts showing the LicenseDialog on next launch (current behavior verified intact).
  - A new **MANAGED MODE** section appears in the build-config form (next to the TRIAL MODE section) with a checkbox + "Duration (days)" + optional "Max provisions per /24 subnet" field. Mutual exclusion with TRIAL is enforced (form-level error if both ticked).
  - Builds list shows a **MANAGED** badge (similar to the TRIAL badge) and a copyable public download link (e.g. `/download_managed/<config_id>`) for each managed config.
  - A user who downloads a managed .exe and runs it on a fresh machine: gets the splash, sees "Activating license...", the .exe auto-mints an N-day key, downloads the Roblox bundle, extracts it next to the .exe, then launches Roblox — zero manual key entry, zero manual install path.
  - After the N days, the launcher detects expiry, deletes the saved key, and shows the manual LicenseDialog so the user can paste a renewal key from the developer.
  - Server admin History page shows the auto-issued license alongside other licenses with note like `MANAGED (app_name) ip=...` and the correct expiry timestamp.
  - Smoke test in the Replit preview verifies: server boots, schema migration runs cleanly on existing DB, build form renders new section, a managed build_config can be created/edited/deleted, mutual exclusion blocks creating both trial+managed in one config, and the new `/api/managed_register` + `/download_managed/<id>` endpoints return the right JSON / HTTP codes via curl.

  ## Out of scope
  - Real end-to-end Windows .exe test on a clean PC (already tracked under task #22).
  - Trial time-left badge on splash (already tracked under task #23).
  - Renewal/extension UI in admin (admin can already extend keys via existing edit-license flow).
  - HTTPS / TLS termination for the public managed download URL (recommend Cloudflare/Caddy in front, same as trial).
  - Per-key revocation UI changes (existing admin page already handles this).
  - Atomic subnet-quota race fix (carried over from prior code review, still out of scope).

  ## Steps
  1. **Make trial key sticky on expiry.** In the launcher, remove the `.license_key` deletion that fires on trial expiry / signature failure / watchdog fatal expiry. Keep the friendly TrialExpiredDialog. Verify the auto-mint guard still requires "no saved key" so a sticky-but-dead trial key blocks re-mint on subsequent launches. Do NOT touch the non-trial expiry branch — it must continue to delete the key.

  2. **Add Managed mode to the database + admin form.** Add three columns to `build_configs`: `is_managed`, `managed_duration_days` (default 30), `managed_max_per_subnet` (default 0 = unlimited). Add a partial unique index so `is_managed` and `is_trial` can never both be 1 on the same row. Update the build-config create/edit handlers to read/write these fields, and reject the form if both TRIAL and MANAGED are ticked. Add a "MANAGED MODE" section in the form template, visually similar to the TRIAL MODE section but with "Duration (days)" and an optional subnet limit.

  3. **Patch launcher source from build_configs (managed flags).** Extend `_patch_launcher_source` to inject `IS_MANAGED = True/False` and `MANAGED_DURATION_DAYS = N` into the launcher source, alongside the existing `IS_TRIAL` patching. Reuse the existing trial XOR-secret machinery so the managed build also has a signed channel for the auto-mint endpoint (no new secret).

  4. **Add server endpoint for managed auto-mint.** New signed endpoint `/api/managed_register` modeled on `/api/trial_register` but: looks up build_config by app_name (or config_id passed in body) where `is_managed = 1`, mints a license with `duration_seconds = managed_duration_days * 86400`, optionally enforces `managed_max_per_subnet` if > 0, returns signed JSON with `license_key`, `expires_at`, `duration_seconds`. Note in the licenses table reads `MANAGED (app_name) ip=...`.

  5. **Add public download route for managed builds.** New route `/download_managed/<int:config_id>` modeled on `/download_trial` but parameterized by config_id (since multiple managed configs can coexist). Same per-IP rate limit. Serves the latest completed build artifact for that config.

  6. **Wire launcher to managed mode end-to-end.** In the splash bootstrap: treat `IS_MANAGED` like `IS_TRIAL` for the bundle-download branch and the get_paths roblox_dir override (extract straight into base). For license acquisition: if no saved key and `IS_MANAGED`, call the new `/api/managed_register` endpoint, save the key, continue. If a saved key exists and validation fails, follow the **non-trial** expiry path (delete key, show LicenseDialog) — NOT the sticky-trial path. EMBEDDED_LICENSE_KEY still wins over both flags if set.

  7. **Builds list UI.** Show a MANAGED badge (purple/blue, distinct from TRIAL orange) next to managed configs, with the copyable `/download_managed/<id>` URL. Pass the URL via `url_for(_external=True)`.

  8. **Smoke test in the Replit preview.** Restart the workflow. Verify: schema migration runs cleanly (check `pragma table_info(build_configs)`), GET /build_config/create renders both sections, POSTing a managed config saves the right columns, mutual exclusion blocks trial+managed in one config, GET /builds shows the MANAGED badge + correct public URL, hitting `/api/managed_register` with a valid signed body returns a license key + expiry, hitting `/download_managed/<id>` either serves the artifact or returns 404 cleanly when no build exists yet, and the trial flow still works (regression check).

  9. **Architect code review.** After the build is done, call the architect on the changed files (launcher.py, server.py, build_config_form.html, builds.html) with the diff to catch any silent bugs, mutual-exclusion edge cases, signature-replay risks, or migration-on-existing-db hazards before handing back to the user.

  ## Relevant files
  - `launcher.py:25-50`
  - `launcher.py:62-90`
  - `launcher.py:1075`
  - `launcher.py:1177-1184`
  - `launcher.py:1280-1395`
  - `launcher.py:2140-2200`
  - `launcher.py:2255-2300`
  - `license_server/server.py:130-220`
  - `license_server/server.py:317-380`
  - `license_server/server.py:1450-1530`
  - `license_server/server.py:1900-2100`
  - `license_server/server.py:2200-2330`
  - `license_server/templates/build_config_form.html`
  - `license_server/templates/builds.html`
  