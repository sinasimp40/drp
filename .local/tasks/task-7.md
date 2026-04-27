---
title: Trial downloads bundle like premium
---
# Trial Downloads Bundle + One-Key-Per-Trial

## What & Why
Two related changes to how custom trial builds behave:

1. **Revert trial-skip-bundle.** Earlier, trial builds were changed to
   refuse downloading the Roblox bundle and to hard-fail with
   "Roblox is not installed on this PC" if the user didn't already
   have Roblox. The user wants this rolled back: trial builds should
   download the same bundle premium does, and after the bundle is
   installed locally the launcher should wipe `%LOCALAPPDATA%\Roblox*`
   (the existing `purge_appdata_roblox_versions()` already does this —
   we just need the bundle path to actually run for trials so that
   purge gets triggered).

2. **One key per trial config.** Each custom trial config should mint
   exactly ONE license key, total. The first machine that runs the
   trial .exe claims it; every other download of that same trial
   .exe gets rejected with "This trial has already been claimed".
   If the admin wants to give another person a trial, they create a
   new trial config in the admin panel — that one mints its own
   single, separate key.

## Done looks like
- A user runs a trial .exe on a fresh PC with no Roblox installed →
  the launcher downloads the Roblox bundle from the license server
  (same flow as premium), extracts it, deletes any pre-existing
  `%LOCALAPPDATA%\Roblox*` folders, then launches.
- A user runs the same trial .exe on a second PC → the trial-register
  call returns "This trial has already been claimed" and the launcher
  shows a clear error. No second key is minted.
- Admin sees the trial config row on `/builds` showing its claim
  status (e.g. `1/1 claimed` → EXHAUSTED badge) so they know at a
  glance whether the trial is still consumable.
- Admin can create a brand-new trial config and that fresh config
  mints its own first key when the next person runs it.
- Existing per-subnet cap (`trial_max_per_subnet`) keeps working as
  a secondary defense for the rare admin who chooses to bump the
  total cap above 1 in the future.

## Out of scope
- No change to premium build behavior. Premium continues to embed a
  single key at build time and continues its existing IP-binding /
  re-registration / suspension flow.
- No change to the existing `purge_appdata_roblox_versions()`
  implementation — it already wipes the entire `%LOCALAPPDATA%\Roblox`
  folder (and any sibling Roblox-named folders). We're only changing
  WHEN it runs for trials (it'll now run after a trial bundle install,
  same as premium).
- No new background scheduler. The 24-hour trial-config purge keeps
  running on page-loads as it does today; an exhausted trial config
  gets cleaned up by the existing case (b) "all issued trials inactive"
  rule once its one license expires.

## Steps
1. **Launcher: revert trial-skip-bundle.** Remove the `IS_TRIAL` branch
   inside the boot sequence so trial falls through to the same
   "find system Roblox → otherwise download bundle → purge AppData"
   path that premium uses. Also drop the matching `IS_TRIAL` guard
   that skipped the sync step, and the cosmetic `IS_TRIAL` branch
   in the path-resolution helper that picked a different folder for
   trial. After this, `IS_TRIAL` should only affect license/key
   behavior, not Roblox file behavior.

2. **Server: enforce 1 key per trial config.** Add a new
   `trial_max_total INTEGER DEFAULT 1` column to `build_configs`
   via a safe `ALTER TABLE` migration in `init_db()`. In
   `api_trial_register`, before minting a key, count existing
   `licenses` rows where `parent_config_id = config.id AND is_trial = 1`
   (any status — active/expired/revoked all count). If the count is
   >= `trial_max_total`, reject with HTTP 410 and a clear
   "This trial has already been claimed" message. Run this check
   BEFORE the existing per-subnet cap so the global cap is the strict
   ceiling. Backfill `trial_max_total = 1` for existing trial configs
   on migration.

3. **Admin form: expose the cap (default 1).** Add a numeric
   "Max total claims" input to the create/edit build-config form,
   shown only when `is_trial` is checked. Default value `1`,
   min `1`, max `999`. Persist on create and update.

4. **Builds page: show claim counter.** On the build configs table,
   for each trial row, show a small `claimed / max_total` badge
   (e.g. `0/1`, `1/1 EXHAUSTED`). Query the count alongside the
   existing trial-config select.

5. **Launcher: friendlier "already claimed" UX.** When the trial
   register call returns 410 / "already claimed", the splash screen
   should show a clear message ("This trial has already been used.
   Please contact the admin for a new trial.") and exit cleanly,
   not crash or retry forever.

## Relevant files
- `launcher.py:85-90,130-145,225-345,2840-2960`
- `license_server/server.py:492-700,2735-2830,2912-2974,2618-2730`
- `license_server/templates/builds.html:195-245`