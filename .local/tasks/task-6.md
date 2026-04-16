---
title: Parallel builds, admin redesign, OTA fix, remove server source
---
# Parallel Builds, Admin Redesign, and OTA Fix

## What & Why
Four issues need fixing:

1. **OTA update swap is broken** — The .bat swap script runs after process exit but fails silently. The downloaded update stays in `_update/` folder and never replaces the current .exe. Fix: eliminate the .bat entirely — on Windows you CAN rename a running .exe, so do the swap inside the Python process before exiting (rename current→.bak, copy new→current name, show dialog, exit).

2. **Parallel builds** — Currently builds run sequentially in a single thread. With 5+ configs this takes 15-25 minutes. Use a thread pool (ThreadPoolExecutor) to build multiple configs in parallel, with a configurable concurrency limit (e.g. 3 at a time to avoid overloading the machine).

3. **Remove Server Source card** — Remove the "Server Source" upload section from the Builds page (keep the endpoints in case needed later, just remove the UI card).

4. **Admin panel design refresh** — The current design is too dark and hard to read. Brighten the admin panel with a modern dark theme: lighter card backgrounds, better contrast for text and labels, clearer visual hierarchy, and a more polished overall look while keeping the orange accent color.

## Done looks like
- OTA updates successfully replace the current .exe — no `_update/` folder leftover, no DLL errors, user reopens to find the new version
- Building 5+ configs uses parallel threads, completing significantly faster
- Server Source card is removed from the Builds page
- Admin panel has a refreshed, more readable dark theme with better contrast

## Out of scope
- Changing the orange brand color
- Adding new admin pages or features
- Changing the launcher's splash screen design

## Tasks
1. **Fix OTA update swap** — Replace the .bat-based swap with in-process file swap: rename running .exe to .bak, copy downloaded exe to current name, clean up `_update/` folder, show "Update installed, please reopen" dialog, exit. Add startup cleanup to delete leftover .bak files on next launch.

2. **Add parallel builds with ThreadPoolExecutor** — Change `_run_build_all` to use `concurrent.futures.ThreadPoolExecutor` with max 3 workers. Each config builds in its own thread. Progress tracking and status updates remain per-config. Handle partial failures gracefully.

3. **Remove Server Source UI card** — Remove the Server Source card div and the `loadServerInfo()` JavaScript function from builds.html. Keep the API endpoints intact.

4. **Refresh admin panel design** — Update base.html CSS: lighten card backgrounds (#111→#161616), lighten table/form backgrounds, improve text contrast, add subtle card shadows, refine badge colors for better readability, slightly brighten border colors. Make the dashboard feel more spacious and modern.

## Relevant files
- `launcher.py:779-891`
- `license_server/server.py:1073-1107`
- `license_server/templates/builds.html:29-46,395-414`
- `license_server/templates/base.html:7-231`