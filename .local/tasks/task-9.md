---
title: Bigger GIF logo + heartbeat grace period
---
# Bigger GIF logo + heartbeat grace period

  ## What & Why
  Two improvements:
  1. The splash screen GIF logo is currently constrained to 100x100 and looks too small. It should fill the available width between the splash borders and the title text — roughly the same width as the red box the user drew (~400-480px wide), while keeping aspect ratio so it doesn't stretch.
  2. The heartbeat grace period is too aggressive (3 failures x 10s = 30 seconds). Increase to 18 failures (~3 minutes) so brief network hiccups don't kill Roblox and lock the user out. The heartbeat still checks every 10 seconds.

  ## Done looks like
  - GIF logo fills the horizontal space between the splash edges (with some padding), centered above the title. Aspect ratio preserved — no stretching.
  - If the GIF is naturally wider than tall (like the "PLEASE WAIT" GIF), it will appear as a wide banner-style logo instead of a tiny square.
  - PNG logos also scale to the same larger area.
  - LICENSE_OFFLINE_GRACE changed from 3 to 18 in launcher.py.
  - Server code unchanged for heartbeat (already fine).

  ## Out of scope
  - Changing the heartbeat check interval (stays at 10 seconds).
  - Changing the splash screen dimensions or layout of other elements.
  - Animated GIF on the server admin panel.

  ## Tasks
  1. In launcher.py, change the logo sizing from a 100x100 square constraint to a wider bounding box — max width ~480px (splash width 560 minus 80px padding) and max height ~100px. Both _setup_logo (QMovie for GIF) and _draw_static_logo (QPixmap for PNG) must use this wider bounding box with KeepAspectRatio.
  2. Adjust LOGO_Y if needed so the logo is vertically centered in the space above the title (title_y=140).
  3. Change LICENSE_OFFLINE_GRACE from 3 to 18 in launcher.py.
  4. Verify server starts without errors.

  ## Relevant files
  - `launcher.py:18`
  - `launcher.py:28-30`
  - `launcher.py:420-470`
  - `launcher.py:540-555`