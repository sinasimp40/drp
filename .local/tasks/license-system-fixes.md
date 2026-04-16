# License System Bug Fixes & IP Binding

## What & Why
Fix multiple bugs in the license validation system (both server and launcher) and add IP-based license binding to prevent license sharing. Users are reporting: licenses showing expired when they have time left, Roblox auto-closing unexpectedly, and the launcher re-asking for a license key when opening a second instance quickly.

## Done looks like
- Active licenses with remaining time no longer get falsely reported as expired
- The heartbeat system reliably keeps Roblox running for the full license duration without unexpected closures
- IP binding: when a license is first activated, the client IP is recorded. If a different IP tries to use that license, it gets suspended automatically and the launcher shows "License suspended — contact the developer"
- Admin dashboard has an "Unsuspend" button for suspended licenses, which clears the registered IP so the user can re-activate from a new IP (one-time re-registration with the new IP)
- Suspended licenses appear properly in the dashboard and history pages with a "Suspended" badge
- Opening a second launcher instance quickly no longer re-prompts for the license key (race condition fixed)
- Splash screen loads without unnecessary delays on fast double-launches

## Out of scope
- Changing the overall license key format or encryption scheme
- Adding new license duration types or pricing logic
- Redesigning the admin dashboard UI beyond what's needed for suspended licenses

## Tasks
1. **Fix the "already activated" validate/heartbeat flow** — The `/api/validate` endpoint rejects active licenses with "License already activated", and the launcher falls back to heartbeat. But the heartbeat response should also return `remaining_seconds` and `remaining_text` to the launcher. Ensure the validate endpoint for active licenses properly falls back to heartbeat behavior (check remaining time, update heartbeat, return valid if time remains) instead of rejecting outright. This is the root cause of false "expired" reports.

2. **Fix heartbeat watchdog killing Roblox prematurely** — The launcher's `start_license_watchdog` treats ANY non-network heartbeat failure as fatal and immediately kills Roblox + shows lock screen. Add retry logic: require multiple consecutive non-network failures (not just one) before killing Roblox. Also ensure the error message distinguishes between truly expired licenses vs temporary server glitches.

3. **Add IP binding to the license server** — Add a `registered_ip` column to the licenses database table. On first activation (pending → active), save the client IP as `registered_ip`. On every heartbeat, compare the current IP against `registered_ip`. If they differ, set the license status to `suspended`. Add a new `suspended` status throughout the server (validate, heartbeat, dashboard, history endpoints). Return a specific error message: "License suspended — IP changed. Contact the developer."

4. **Add unsuspend functionality to the admin dashboard** — Add an "Unsuspend" button on the dashboard and history pages for suspended licenses. When clicked, clear the `registered_ip` and set status back to `pending` so the license can be re-activated from a new IP. The next activation locks the new IP. Show the registered IP in the dashboard so the admin can see which IP was originally bound.

5. **Handle suspended status in the launcher** — When the launcher receives a "suspended" error from validate or heartbeat, show a specific lock screen message: "License suspended — contact the developer" instead of the generic "License expired" message. Do not delete the local license file for suspended licenses (so the user doesn't have to re-enter the key after getting unsuspended).

6. **Fix the multi-instance race condition in the launcher** — When the launcher finds a saved license key and validate returns "License already activated", it should seamlessly use heartbeat without any user-visible delay or dialog. Add a short mutex/lock file check so a second launcher instance launched within seconds of the first doesn't re-trigger the license prompt. Also prevent the license dialog from appearing when a valid `.license_key` file exists and the heartbeat succeeds.

7. **Optimize splash screen loading for fast double-launches** — Cache the splash pixmap creation so it doesn't block the UI thread. Pre-check the license file existence before building the full splash screen to avoid showing the splash and then immediately popping a license dialog.

## Relevant files
- `license_server/server.py`
- `license_server/templates/dashboard.html`
- `license_server/templates/history.html`
- `license_server/templates/base.html`
- `license_server/templates/create.html`
- `license_server/templates/login.html`
- `launcher.py`
- `launcher.py:811-853`
- `launcher.py:872-912`
- `launcher.py:915-1153`
- `license_server/server.py:164-244`
- `license_server/server.py:247-312`
- `license_server/server.py:343-420`
