# DENFI Bundle Builder (RDP automation)

Unattended Roblox bundle builder. Runs on a Windows RDP server on a
schedule, downloads the latest Roblox player, zips it, uploads it to the
license server as the new active bundle, then cleans up.

## What it does (per run)

1. Asks the license server: "what version-string is your current bundle for?"
2. Asks Roblox: "what version-string is the latest WindowsPlayer?"
3. If they match → exit (nothing to do).
4. Else: download the Roblox bootstrapper, run it (no login required —
   login is only needed to JOIN a game, not to install), find the new
   `%LOCALAPPDATA%\Roblox\Versions\version-XXXX` folder, zip it, POST
   it to `/api/admin/upload_bundle` with the bot token. The server
   prunes oldest bundles past `BUNDLE_RETENTION_COUNT` (default 3).
5. Uninstall Roblox + wipe `LocalAppData\Roblox*` and
   `Program Files*\Roblox*` so the RDP stays clean between runs.

Every launcher heartbeat picks up the new bundle on the next launch.
No client-side action required.

## One-time server setup

On the license server (Linux or Windows), set two env vars:

```
BUNDLE_AUTOMATION_TOKEN=<long random string — generate with `openssl rand -hex 32`>
BUNDLE_RETENTION_COUNT=3      # optional, default 3
```

Restart the license server.

## One-time RDP setup

1. Install Python 3.10+ (no extra pip packages needed).
2. Copy this `bundle_automation/` folder to the RDP, e.g.
   `C:\denfi\bundle_automation\`.
3. Add a Windows Defender folder exclusion for the workdir (so it
   doesn't quarantine the Roblox installer mid-run):
   `%TEMP%\denfi_bundle_*` and `C:\denfi\bundle_automation\logs`.
4. Set the same env vars on the RDP user account:
   ```
   setx LICENSE_SERVER_URL https://your-license-server.example.com
   setx BUNDLE_AUTOMATION_TOKEN <same value as on the server>
   ```
   (`setx` makes them persistent. Open a fresh shell to see them.)
5. Test it once interactively:
   ```
   python C:\denfi\bundle_automation\build_and_upload.py
   ```
   Watch the log under `bundle_automation\logs\build_*.log`. First run
   should download Roblox (~3 min), zip (~1 min), upload (~30 s),
   uninstall (~1 min). End result: new bundle visible on the bundles
   page in the admin panel.
6. Schedule it. Open Task Scheduler:
   - Action: `Start a program`
   - Program: `python.exe`
   - Arguments: `C:\denfi\bundle_automation\build_and_upload.py`
   - Trigger: Daily at e.g. 03:00
   - "Run whether user is logged in or not"
   - "Run with highest privileges" (so the uninstall step can hit
     Program Files entries if any)

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success (uploaded a new bundle OR no update was needed) |
| 1 | Network / Roblox CDN failure |
| 2 | Install failure (bootstrapper ran but no version folder appeared) |
| 3 | Server upload rejected |
| 4 | Missing required environment variable |
| 5 | Unexpected error (full traceback in the log file) |

## Manual one-shot use

If the operator wants to push a new bundle right now without waiting
for the schedule, just run the script — it's idempotent. If a bundle
for the latest Roblox version already exists, it exits 0 immediately.

## Debugging

Set `BUNDLE_BUILD_KEEP_TEMP=1` to skip cleanup of the workdir; useful
for inspecting what got downloaded/zipped if something goes sideways.

The full log of every run (including stack traces) is written to
`bundle_automation\logs\build_<timestamp>.log`.
