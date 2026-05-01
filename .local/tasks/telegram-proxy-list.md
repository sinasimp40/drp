# Telegram Backup Proxy List with Auto-Fallback

  ## What & Why
  Replace the single Telegram backup proxy field with an editable **list** of proxies (HTTP, HTTPS, SOCKS4, SOCKS5/SOCKS5h). When a backup is sent, the system tries each proxy in order until one succeeds. Proxies that fail with a real network/proxy error are automatically removed from the list; proxies that succeed stay. This lets the user paste a batch of free public proxies and have the backup self-heal without manual maintenance, which is the only practical way to reach `api.telegram.org` from a Russian server.

  ## Done looks like
  - The Backups page has a multi-line **Proxy List** editor (one URL per line) plus a **Direct connection first** toggle.
  - Pasting 20 proxies and clicking **Send Backup Now** results in the file being delivered through the first working proxy; non-working proxies disappear from the list automatically.
  - The Recent Attempts table records which proxy succeeded and which proxies were evicted (and why) for each backup.
  - Telegram-side errors (HTTP 401 invalid token, 413 file too big, 429 rate limit) **do not** evict the proxy that surfaced them.
  - Two backup attempts running at the same time (e.g. user clicks Send Backup Now while the scheduler fires) cannot resurrect a removed proxy or overwrite each other's edits to the list.
  - A scheduled backup with a list of dead proxies completes within a bounded time (no 50-minute hangs) and reports a clean summary.
  - The existing single `proxy_url` value is migrated into the new list on first load with no user action.

  ## Out of scope
  - Automatic proxy discovery / scraping public proxy sites.
  - Proxy "cooldown" / temporary disable with retry-later (the user explicitly wants immediate eviction on failure).
  - Per-proxy authentication management UI beyond `user:pass@host:port` in the URL.
  - Streaming uploads to reduce memory usage for very large database files (the licenses DB is small; revisit only if it grows past a few MB).
  - Replacing PySocks or rewriting the SOCKS handler.

  ## Steps

  1. **Settings model & migration**
     Replace the single `proxy_url` in `backup_settings.json` with `proxy_list` (ordered array of strings) and a `try_direct_first` boolean. On first load, if legacy `proxy_url` exists and is non-empty, prepend it to `proxy_list` and clear the old field. Update `public_view` to expose the list (with each URL masked for display) without leaking credentials in the unmasked field.

  2. **Failure classification helper**
     Add a private helper in `telegram_backup.py` that runs one send attempt and returns a structured result: `(outcome, message)` where outcome is one of `success`, `evict_proxy` (network/SOCKS/connect/TLS/timeout/proxy-407/proxy-502 / mid-stream connection drop), `telegram_error` (any HTTP response containing a parseable Telegram JSON body, including 401/413/429), or `bad_input` (missing token or chat id). This is the single source of truth for "should we delete this proxy".

  3. **Bounded sequential attempt loop**
     Refactor `run_backup` so the entire iteration over the proxy list is performed inside one acquisition of the existing `_lock`. The loop respects a `try_direct_first` flag (one direct attempt before the list when enabled), iterates the list in order, stops on the first `success` or `telegram_error`, removes proxies whose outcome is `evict_proxy`, and enforces an overall cap (e.g. at most 8 proxy attempts and 120 seconds total wall clock per backup) so the scheduler is never blocked indefinitely. Use a short connect timeout (≈5s) for each attempt and the existing 60s read timeout for the upload itself.

  4. **Persistence semantics**
     Eviction edits to `proxy_list` are written back to disk inside the same locked block that performed the attempts, so a concurrent attempt cannot overwrite the edited list. Keep `save_settings` exactly as-is at the file-system level (it already writes atomically via `os.replace`); the change is only in the call ordering.

  5. **History enrichment**
     Each history entry records which proxy was used (masked), how many proxies were evicted in that run, and a short reason per eviction (e.g. "timeout", "connection refused", "SOCKS handshake failed"). The existing 10-entry rolling buffer is unchanged.

  6. **Apply the same pipeline to `send_message`**
     The Test Connection button currently calls `send_message` with a single proxy. Route it through the same list-walking helper so testing the configuration reflects what a real backup will do, and so a successful test shows the user which proxy actually worked.

  7. **Backups page UI**
     Replace the single Proxy URL input with: a multi-line textarea for the proxy list (one URL per line, no masking inside the textarea since the page is admin-only and masking breaks editing), a "Direct connection first" checkbox bound to `try_direct_first`, and a small read-only summary panel showing the current count and last-used proxy from history. Keep the bot token / chat ID / caption prefix fields and their existing masking unchanged.

  8. **Save handler validation**
     In `/backups/save`, parse the textarea by lines, trim whitespace, drop empty lines and duplicates, validate each line has a recognised scheme (`http`, `https`, `socks4`, `socks5`, `socks5h`), and reject the save with a clear flash message if any line is invalid. Cap the list at a reasonable maximum (e.g. 200 entries) to bound scheduler runtime.

  9. **Empty-list behaviour**
     If the list is empty and `try_direct_first` is false, `run_backup` returns failure immediately with a clear "No proxies configured and direct connection disabled" message rather than appearing to hang.

  ## Relevant files
  - `license_server/telegram_backup.py`
  - `license_server/server.py:2780-2870`
  - `license_server/templates/backups.html`
  - `license_server/backup_settings.json`
  