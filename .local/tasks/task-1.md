---
title: Config-change detection & single-config rebuild
---
# Config-Change Detection & Single-Config Rebuild

## What & Why
When an admin edits a build config (icon, Roblox path, app name, etc.), the client's launcher should detect the change and auto-download the rebuilt `.exe` — without requiring a version bump. Currently the OTA system only triggers on version number changes, so config-only edits require a full "Build All" with a bumped version. This feature adds config fingerprinting and a per-config rebuild button so individual clients get updates when their config changes, independent of the global version.

## Done looks like
- Each build artifact stores a hash/fingerprint of the config settings used to build it.
- The launcher sends its current config hash when checking for updates.
- The server detects "same version but config changed" and tells the launcher to update.
- A "Rebuild" button on each build config in the dashboard lets the admin rebuild just that one config using the latest version, without rebuilding all configs.
- The launcher correctly downloads and installs the new `.exe` when the config hash changes.
- Existing version-based OTA updates still work as before.

## Out of scope
- Per-config versioning (version stays shared/global).
- Changing the "Build All" flow (it continues to work as-is).
- UI redesign of the builds dashboard (only adding the rebuild button).

## Tasks
1. **Add `config_hash` column to `build_artifacts`** — Add a new column to the `build_artifacts` table that stores a SHA256 hash of the config fields (app_name, hardcoded_path, license_server_url, license_secret, icon_filename, embedded_key) used at build time. Add a helper function to compute this hash from a config dict.

2. **Store config hash during builds** — In `_run_single_build` and `_run_build_all`, compute and store the config hash in `build_artifacts` when a build completes. This applies to both "Build All" and the new single-config rebuild.

3. **Add single-config rebuild route** — Add a `/build_config/<config_id>/rebuild` POST endpoint that rebuilds just one config using the latest completed build version. It creates a new build artifact entry, runs the build in a background thread, and stores the config hash.

4. **Add "Rebuild" button to dashboard** — Add a rebuild button next to each build config in the builds page UI. Show build status feedback (building/completed/failed).

5. **Update the OTA update check endpoint** — Modify `/api/update_check` to also compare the config hash. If the version is the same but the config hash differs, return `update_available: True` so the launcher downloads the new exe.

6. **Update launcher.py to send config hash** — Modify the launcher's `check_for_update` to send a `config_hash` field (read from a local metadata file or embedded during build) so the server can compare it. Store the config hash in a sidecar file or embed it in the patched launcher source.

7. **Patch launcher source with config hash** — In `_patch_launcher_source`, inject the computed config hash as a constant (e.g. `CONFIG_HASH`) into the launcher source so the compiled exe knows its own config fingerprint.

8. **Test end-to-end** — Verify: (a) editing a config and rebuilding produces a new artifact with updated hash, (b) the update check endpoint correctly detects hash mismatch, (c) version-only updates still work, (d) "Build All" still works with hashes, (e) the rebuild button works for a single config.

## Relevant files
- `license_server/server.py:100-138`
- `license_server/server.py:886-1105`
- `license_server/server.py:1290-1342`
- `license_server/server.py:1500-1610`
- `license_server/server.py:1662-1736`
- `launcher.py:22,788-835,811-870`
- `license_server/templates/builds.html`