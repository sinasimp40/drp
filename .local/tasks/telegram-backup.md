# Telegram Backup of license.db

## What & Why
Add a way for the admin to automatically send the `license.db` file to a Telegram chat/channel on a configurable schedule. This gives the operator off-server backups of the licenses database without manual SCP/RDP, and lets them store it in a private Telegram channel they control.

## Done looks like
- A new "Backups" page in the admin sidebar (under existing nav).
- The page has a small form to enter and save:
  - Telegram **Bot Token**
  - Telegram **Chat ID** (channel or user ID)
  - **Schedule**: simple options — Off / Every N hours / Daily at HH:MM (server local time) / Weekly on day at HH:MM
  - Optional caption prefix (e.g. "DPRS prod backup")
- A "Test connection" button that sends a small text message to the configured chat and reports success/failure inline.
- A "Send backup now" button that uploads the current `license.db` immediately and shows the result.
- A small history list (last 10 attempts) with timestamp, type (manual/scheduled), status, and error message if any.
- Settings persist across server restarts.
- A background scheduler inside the Flask process actually delivers the file at the configured time, with retry-once on failure and clear log output.
- Sensitive values (bot token) are write-only in the UI: shown as masked once saved, with a "Replace" affordance.

## Out of scope
- Multiple destinations / multiple bots.
- Encryption of the .db before upload (operator's Telegram channel privacy is assumed sufficient).
- Restoring from a Telegram-stored backup (download/restore flow).
- Cron-style expressions; we only need the simple schedule presets above.
- Rotating/pruning old backups in Telegram.

## Steps
1. **Persistent settings store** — Add a small JSON-on-disk settings store (next to `licenses.db`) that holds bot token, chat ID, schedule config, caption prefix, and the recent-attempts history. Provide load/save helpers used by the rest of the feature.

2. **Telegram sender** — Implement a helper that uploads a file to Telegram via the Bot API `sendDocument` endpoint using only the standard library (urllib + multipart) so no new dependency is required, plus a `sendMessage` helper for the test button. Centralize error handling and timeouts.

3. **Background scheduler** — Add a daemon thread started at app boot that wakes once a minute, reads the saved schedule, and triggers the sender when the next-due time has passed. Update `last_run_at` and append to the attempts history on each run. Survive transient failures and log clearly.

4. **Routes** — Add admin-protected routes: GET `/backups` (render page), POST `/backups/save` (update settings), POST `/backups/test` (send test message), POST `/backups/run-now` (send file immediately). All return JSON for AJAX or redirect for non-JS. Mask the bot token when sending the page context to the template.

5. **Backups page UI** — New template that matches the existing Sidebar SaaS look (design tokens already in `base.html`): one card for credentials, one for schedule, one for actions (Test / Send now), and one for history. Add a sidebar nav entry pointing to `/backups`.

## Relevant files
- `license_server/server.py`
- `license_server/templates/base.html`
- `license_server/templates/dashboard.html`
- `license_server/requirements.txt`
