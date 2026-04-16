---
title: Fix WebSocket error on Windows server
---
# Fix WebSocket Error on Windows Server

## What & Why
The Flask-SocketIO WebSocket transport causes `write() before start_response` errors on Windows with Werkzeug's dev server. The Builds page still works via polling fallback, but the errors are noisy and confusing. Fix so the server runs cleanly on Windows.

## Done looks like
- No more `AssertionError: write() before start_response` errors in the server console on Windows
- Build progress and OTA status still update in real-time on the Builds page
- Server starts cleanly without WebSocket-related errors

## Out of scope
- Switching to a production WSGI server (gunicorn/eventlet) — this server runs on Windows RDP with the dev server

## Tasks
1. **Disable WebSocket transport on the server side** — Configure Flask-SocketIO to use HTTP long-polling only (no WebSocket upgrade attempts). This avoids the Werkzeug incompatibility while keeping real-time push via long-polling, which is functionally equivalent for this use case.
2. **Update the client-side SocketIO config** — In `builds.html`, set the Socket.IO client to use polling transport only, matching the server config.
3. **Verify the Builds page still shows real-time progress** — Confirm OTA status and build progress sections still load and update correctly.

## Relevant files
- `license_server/server.py:45-51`
- `license_server/templates/builds.html:175-196`