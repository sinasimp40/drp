# Launcher Update Safety

## What & Why
The Windows launcher (`launcher.py`) currently has a "single-instance" check
that does not actually enforce single-instance, and an update step that
briefly leaves the executable in an unsafe state. If a user double-clicks
the launcher twice (or the auto-restart races with a manual launch) during
an update, two launchers can both try to swap `current.exe` at the same
time — risking a missing or half-written `.exe`, a stuck `.bak`, or a
silently-corrupted install.

This task closes that gap with a real cross-process lock and a dedicated
"update in progress" gate, and tightens the swap step so a failure can
always be rolled back to a working executable.

## Done looks like
- Starting the launcher while another copy is already running shows a
  short message ("Launcher is already running" or "Update in progress —
  please wait") and exits cleanly. It no longer silently runs a second
  copy.
- While an update is downloading or being applied, any other launcher
  instance refuses to enter the update flow and waits / exits with a
  clear status — no two instances ever try to swap the `.exe` at the
  same time.
- If the launcher is killed mid-update, the next launch automatically
  recovers: a leftover `current.exe.bak` is restored if `current.exe`
  is missing, and a stale "update in progress" marker (dead PID or
  expired heartbeat) is cleared so the user is not locked out forever.
- The update swap itself uses an atomic replace and, on any failure,
  guarantees that `current.exe` is never left missing.
- Everything is local to the launcher — no server changes are required
  for this task.

## Out of scope
- Server-side rollout coordination (e.g. "this build is required",
  min-version enforcement, staggered rollout windows). Useful but
  separate; can be a follow-up task if you want it later.
- Cooperative multi-machine coordination (today the lock only protects
  one PC at a time, which is the real problem; that is enough).
- Changes to the Roblox singleton mutex (`grab_roblox_mutex`) — that
  one is unrelated to update safety and already works.
- Cosmetic/UX redesign of the splash screen beyond the small "already
  running" / "update in progress" state messages.

## Steps
1. **Real single-instance mutex** — Replace the existing PID-file
   "advisory" lock with a real Windows named kernel mutex (created via
   `CreateMutexW`, held for the lifetime of the process, automatically
   released by the OS on crash). When acquisition fails because another
   instance owns it, the launcher exits cleanly with a brief splash
   message instead of continuing.

2. **Fix the silent-fallthrough bug at startup** — At the existing
   single-instance check, when the lock cannot be acquired the launcher
   must stop, not continue. Today it falls through and runs anyway.

3. **Dedicated "update in progress" gate** — Add a small state file
   (e.g. `APP_DIR/.update_state`) recording `{pid, started_at,
   last_heartbeat, target_version, phase}` where `phase` is one of
   `downloading | applying | restarting`. Acquire it before the
   download starts and keep it across the apply+restart. A second
   instance that sees a fresh marker exits with "Update in progress —
   please wait". A stale marker (PID gone OR heartbeat older than ~120s)
   is cleared automatically.

4. **Stop releasing the lock before respawn** — In
   `apply_update_and_restart`, the current code releases the singleton
   lock just before spawning the new exe. That reopens the race. Let
   the OS release the mutex when the old process exits, and have the
   freshly spawned child retry mutex acquisition for ~10s (with a
   `--post-update-restart` hint) to handle the brief overlap.

5. **Atomic swap with rollback** — Refactor the rename → copy sequence
   to use `os.replace` semantics and a clear staged flow:
   verify the downloaded file → atomically move `current.exe` to
   `current.exe.bak` → atomically move the new exe to `current.exe`. On
   any failure, if `current.exe` is missing but `current.exe.bak`
   exists, restore the backup before raising. Never leave the install
   without a working executable.

6. **Startup recovery** — Before doing anything else at startup, if
   `current.exe.bak` exists and `current.exe` does not, restore the
   backup. Also clear stale `.update_state` and stale `_update/` temp
   files that belong to dead PIDs. This is what lets users recover from
   a crash mid-update without manual intervention.

7. **Smoke test the new flow** — Manually verify: (a) launching twice
   in a row, second exits cleanly; (b) starting an update, launching a
   second copy mid-download, second exits with "update in progress";
   (c) killing the launcher mid-swap and relaunching restores the
   working `.exe`; (d) a normal successful update still restarts cleanly
   into the new version. No automated tests are required for this since
   the logic is OS-specific (Windows-only paths).

## Relevant files
- `launcher.py:370-414`
- `launcher.py:855-1024`
- `launcher.py:1455-1620`
