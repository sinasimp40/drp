---
title: Edit license time and note
---
# Edit License Time and Note

## What & Why
Today the admin can only set a license's duration and note when **creating** it. There's no way to extend a customer's remaining time or fix a typo in the note after the fact. This adds an in-place edit so admins can adjust both fields whenever needed, without touching the database manually.

## Done looks like
- Each license row in the dashboard has an **Edit** action (alongside Revoke / Delete).
- Clicking it opens a small modal showing:
  - Current status, current expiry, and current remaining time
  - A "Time" control with two modes:
    - **Extend by** — add N days/hours to the current expiry (positive or negative)
    - **Set remaining to** — replace the remaining time with N days/hours from now
  - A "Note" text field pre-filled with the existing note
- Saving updates the license immediately; the table refreshes to show the new expiry and note.
- Works for **active**, **pending**, and **expired** licenses:
  - Active → expiry changes; status stays active (or flips to expired if new time is in the past).
  - Pending → updates the stored `duration_seconds` so the new value applies on first activation; note also saves.
  - Expired → if the new expiry is in the future, the license is reactivated (status flips back to active) so a customer who paid late can be revived without a new key.
- A success toast / flash confirms the change and shows the new remaining time.
- Validation: refuses empty / non-numeric inputs; caps maximum extension at a sane value (e.g. 10 years) to prevent fat-finger mistakes.
- The change is logged the same way other admin actions are (so it shows up in any existing audit/history view).

## Out of scope
- Bulk edit of multiple licenses at once.
- Editing the license key itself, the registered IP, or the bound machine — only time and note.
- A full audit log UI (we only need the existing logging path; no new history page).
- Changing the OTA / build config tied to the license.

## Steps
1. **Backend edit endpoint** — Add an admin-protected POST route that accepts a license id, an edit mode (`extend` / `set`), an amount + unit (days/hours), and a note. Recompute `expires_at` and `duration_seconds` accordingly, handle the active/pending/expired cases described above, and persist.
2. **Dashboard UI** — Add an Edit button to each license row, wire up a small modal with the time mode toggle, amount + unit inputs, and note field. Pre-fill from the current row.
3. **AJAX wiring + feedback** — Submit via the existing AJAX pattern (`X-Requested-With: XMLHttpRequest` → JSON response), update the row in place, and show a success/error toast. Keep a graceful non-AJAX fallback that flashes + redirects.
4. **Validation + safety rails** — Reject empty/non-numeric input on both client and server; clamp the maximum extension; refuse to edit revoked/deleted licenses.
5. **Quick manual test pass** — Verify each case: extend active, shorten active into the past (auto-expire), edit pending duration, revive expired, edit note only, and invalid inputs.

## Relevant files
- `license_server/server.py:666-790`
- `license_server/server.py:300-395`
- `license_server/templates/dashboard.html`
- `license_server/templates/base.html`