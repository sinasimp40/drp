---
title: Stop builds from knocking the license server offline
---
# Stop Builds From Knocking The License Server Offline

## What & Why
When the license server is doing a build (PyInstaller bundling a launcher
.exe), the server lags badly and connected launchers sometimes get hit
with an HTTP 403 "Request expired" auth error. Root cause from a code
review:

- The server is being served by Werkzeug's dev server
  (`socketio.run(app, ..., allow_unsafe_werkzeug=True)`), which is not
  built for production load.
- Builds run **in the same process** as the API. Up to 3 PyInstaller
  subprocesses run in parallel, each streaming stdout line-by-line and
  emitting a SocketIO `build_progress` event + a SQLite write on every
  changed percent. That CPU + IO pressure backs up incoming HTTP
  requests.
- When a launcher's signed request waits long enough in the queue, the
  signature timestamp is now > 5 minutes old, and the server returns a
  403 even though the signature is fine.
- The launcher treats every 403 as a hard auth failure, so a transient
  "Request expired" looks to the user like the launcher is broken.

## Done looks like
- Running a build no longer freezes/lags the server. Connected launchers
  keep validating successfully throughout the build.
- Launchers no longer surface a 403 to the user during heavy server
  load — transient "Request expired" / "Replay detected" / "Invalid
  signature" responses are retried once with a fresh signature before
  failing.
- The web app is served by a real production WSGI server (waitress is
  the simplest cross-platform fit), not Werkzeug's dev server.
- Build progress updates do not flood SocketIO or SQLite — they are
  throttled to at most a few times per second per build.
- Default build concurrency drops from 3 to 1 (still configurable via
  env var) so builds can't completely starve the API.

## Out of scope
- Moving builds to a separate process / job queue (Celery / RQ). That's
  the right long-term answer but is a much bigger change. We'll get
  most of the relief from the items above; if needed, file a follow-up.
- Changing the auth scheme or the 5-minute timestamp tolerance.
- Replacing SQLite with Postgres.
- Hardening default `SHARED_SECRET` / `ADMIN_PASSWORD` (separate
  hardening task).

## Steps
1. **Switch the web server to waitress.** Replace the
   `socketio.run(... allow_unsafe_werkzeug=True)` call with a
   production server (waitress, threads ~16). Keep SocketIO working in
   threading mode using long-polling so no Redis/sticky-session setup
   is required. Add `waitress` to `requirements.txt` and verify the
   workflow command still boots cleanly.

2. **Tame the build noise.** In the build runner, throttle
   `socketio.emit('build_progress', ...)` to at most one emit per
   second per artifact (or whenever the percent crosses a 5% bucket,
   whichever comes second). Batch the SQLite progress writes the same
   way. Lower the default `max_workers` for parallel builds from 3 to
   1, exposed via an env var (e.g. `LICENSE_BUILD_CONCURRENCY`) so it
   can be raised on beefier machines.

3. **Make the launcher tolerate transient 403s.** In
   `validate_license()` / `check_for_update()` / the heartbeat
   watchdog, when the server returns 403 with one of `Request
   expired`, `Replay detected`, `Invalid signature`, or
   `Missing authentication headers`, retry once after a short delay
   with a freshly-generated timestamp + nonce + signature. Only
   surface the 403 to the user if the retry also fails. Hard-fail
   reasons (`expired`, `revoked`, `deleted`, `not found`,
   `suspended`) keep the existing immediate-fail behavior.

4. **Smoke-test under load.** Trigger a build (or a few) and, from
   another terminal, hammer `/api/validate` with the existing signed
   request flow. Confirm: no 403s, response times stay reasonable,
   build still completes, dashboard SocketIO updates still arrive
   (just less often).

## Relevant files
- `license_server/server.py:34-66`
- `license_server/server.py:202-263`
- `license_server/server.py:1408-1716`
- `license_server/server.py:3095-3105`
- `license_server/requirements.txt`
- `launcher.py:1136-1208`
- `launcher.py:1807-1869`