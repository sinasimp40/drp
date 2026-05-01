---
title: Fix OTA update DLL error — stop auto-restart after update
---
# Fix OTA Update DLL Error

## What & Why
After an OTA update downloads and installs, the launcher tries to auto-restart the new .exe immediately. On Windows, PyInstaller .exe files extract DLLs (like python311.dll) to a `_MEI` temp folder. When the old process exits, Windows may still hold file locks on those DLLs for several seconds. The new .exe then fails with "Failed to load Python DLL" because it can't access or overwrite the locked temp folder. No amount of cleanup retries in the .bat script reliably fixes this because Windows controls when it releases DLL locks.

The fix: stop auto-restarting after update. Instead, the .bat script only swaps the file (no `start` command), and the launcher shows a user-friendly message before exiting: "Update installed successfully! Please reopen the app." This guarantees the old _MEI folder is fully released before the new .exe ever runs.

## Done looks like
- After OTA download completes, the launcher shows a dialog: "Update v{version} installed! Please reopen the app to use the new version."
- The .bat swap script waits for the old process to exit, replaces the .exe, cleans up _MEI folders, but does NOT launch the new .exe
- User clicks OK on the dialog, app closes cleanly
- User reopens the app manually — no DLL error, new version runs perfectly
- The splash screen still shows "Installing update..." progress during the swap

## Out of scope
- Changing PyInstaller build settings (runtime-tmpdir etc.)
- Silent background updates that apply on next natural restart

## Tasks
1. **Remove auto-restart from .bat script** — Remove the `start "" "{current_exe}"` line from the swap .bat so it only waits for the process to exit, swaps the file, and cleans up temp folders without relaunching.

2. **Show update-complete dialog** — After `apply_update_and_restart` succeeds, instead of showing "Restarting..." on the splash, show a QMessageBox dialog telling the user the update is installed and they need to reopen the app, then exit cleanly.

## Relevant files
- `launcher.py:841-919`
- `launcher.py:1285-1298`