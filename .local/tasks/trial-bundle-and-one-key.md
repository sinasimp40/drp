# Trial Downloads Bundle Like Premium

## What & Why
Earlier the launcher was changed so trial builds would refuse to
download the Roblox bundle from the license server and instead hard-fail
with "Roblox is not installed on this PC" if the user had no system
Roblox. The user wants this rolled back: trial builds should behave
identically to premium for Roblox file handling — try to find a system
Roblox install first, and if none is found, download the bundle from
the license server. After the bundle is installed locally, the
existing `purge_appdata_roblox_versions()` runs and wipes the entire
`%LOCALAPPDATA%\Roblox*` folder (and any sibling Roblox-named
folders), so the user's pre-existing Roblox install can't fight the
launcher's multi-instance / multi-account flow.

The trial license/key behavior is NOT changing. Trial keys still mint
on first run on each fresh machine (same as today), still get capped
by the existing `trial_max_per_subnet` setting, still get IP-pinned
via `registered_ip`. Only the Roblox-files path changes.

## Done looks like
- A trial .exe runs on a PC with no Roblox installed → launcher
  downloads the Roblox bundle from the license server (same flow
  as premium), extracts it, deletes any pre-existing
  `%LOCALAPPDATA%\Roblox*` folders, then launches.
- A trial .exe runs on a PC with Roblox already installed → launcher
  syncs from the system Roblox install (same as premium), then
  the bundle path also runs the AppData purge after install. The
  "Roblox is not installed on this PC" hard-fail message is gone.
- Premium continues to work exactly as it does today — no behavior
  change for premium.
- Trial license issuance is unchanged: still one key per first-run
  machine, still subject to `trial_max_per_subnet`, still IP-pinned.

## Out of scope
- Trial license/key behavior (no change — explicitly preserved).
- Server-side bundle endpoints (already accept trial-signed
  requests via `@require_trial_signed_request`, no edits needed).
- The `purge_appdata_roblox_versions()` implementation itself
  (already wipes the entire `%LOCALAPPDATA%\Roblox` folder and
  sibling Roblox-named folders — verified, no change needed).

## Steps
1. **Remove the trial-only branch in the boot sequence** so trial
   falls through to the same "find system Roblox → otherwise download
   bundle → purge AppData" path that premium uses. The existing
   premium path already calls `download_and_extract_roblox_bundle()`
   which already calls `purge_appdata_roblox_versions()` after a
   successful install, so no new purge call is needed — we just need
   to stop short-circuiting that path for trials.

2. **Drop the matching `IS_TRIAL` guard at the sync step** that
   skipped the file-sync stage for trials, so trial uses the same
   sync logic premium does.

3. **Drop the cosmetic `IS_TRIAL` guard in the path-resolution
   helper** that picked a different folder layout for trial. After
   this, `IS_TRIAL` only affects license/key behavior, not Roblox
   file behavior.

4. **Quick smoke test**: build a trial .exe, run it on a PC with no
   Roblox install, confirm the bundle downloads, AppData\Roblox is
   wiped, and the launcher launches successfully. Then run it on a
   PC that has Roblox installed and confirm the system-sync path is
   used and AppData purge still runs after.

## Relevant files
- `launcher.py:130-145,2840-2960`
