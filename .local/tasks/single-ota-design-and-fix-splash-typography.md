# Single OTA Design + Fix Splash Typography

## What & Why
Two related visual problems with the launcher:

1. **Two different preloading screens.** When an OTA update happens, a
   separate `UpdateProgressDialog` pops up with a different design than
   the main splash. The user wants only ONE design — the existing
   Horizon splash — used for both startup AND for OTA updates. The
   splash already has a status row + "00 / 100" counter at the bottom;
   reuse that to report download/install progress.

2. **Built `.exe` splash does not match `/splash_preview`.** The HTML
   mockup looks clean and well-proportioned, but the Qt-rendered splash
   in the actual launcher looks cramped and the DENFI font looks wrong.
   Two root causes were identified:
   - The orange block is 290px wide in Qt but 240px in the mockup, so
     the right column is 50px narrower and the title autofit shrinks
     the text more than designed.
   - The mockup uses Inter weight 900 @ 42pt, but Inter is not
     installed on Windows by default, so the launcher falls back to a
     different family that doesn't match the design.

## Done looks like
- During an OTA update, the launcher shows the same Horizon splash that
  appears at startup. The status row at the bottom reads e.g.
  `● downloading update v1.2.5  14.0 / 36.8 MB`, then
  `● installing v1.2.5`, then `● restarting into v1.2.5`. The "00 / 100"
  counter on the right tracks the download percent.
- There is no second window or extra dialog during the update — the
  splash is the one and only preloading surface.
- The built launcher's splash matches `/splash_preview?app_name=DENFI%20ROBLOX`:
  same proportions, same DENFI weight/size, same ROBLOX size, same
  vertical rhythm.
- An expert reviewer (architect) signs off on the visual + code quality
  before completion.

## Out of scope
- Any changes to license/heartbeat/update networking logic.
- Any new design directions — we are matching the existing Horizon
  preview, not redesigning it.
- Mac/Linux font fallbacks beyond what is needed for the architect to
  verify the rendering server-side.

## Steps
1. **Bundle Inter font.** Download Inter-Black.ttf (or the variable
   font) and place it next to the Roblox font in the project so the
   build script ships it inside the `.exe`. Wire it into the existing
   font-loading helper so it registers with QFontDatabase the same way
   the Roblox font does.

2. **Fix splash proportions.** Change the orange block width to match
   the mockup (240px), restore DENFI to ~42pt and ROBLOX to ~38pt, and
   apply the mockup's letter-spacing. Verify by rendering headlessly
   and comparing side-by-side with the `/splash_preview` HTML.

3. **Remove the separate update dialog.** Delete `UpdateProgressDialog`
   and rewrite the OTA section of `main()` so the existing splash is
   never hidden during an update. Pipe download/install/restart phases
   into the splash's existing `set_progress(value, msg)` API so the
   status row + "00 / 100" counter shows the update progress.

4. **Update PyInstaller spec / build script.** Make sure the new
   Inter font file gets bundled into the frozen `.exe` (added to
   datas/binaries the same way Roblox2017.ttf is).

5. **Architect review.** After steps 1-4, render the splash headlessly
   in three states (startup, mid-OTA-download, post-install restart)
   and ask the architect to compare against `/splash_preview` and
   review the OTA flow code for correctness, race conditions and
   visual fidelity. Apply any blocking feedback.

## Relevant files
- `launcher.py:608-810`
- `launcher.py:1469-1750`
- `launcher.py:2160-2231`
- `license_server/templates/splash_preview.html:374-525`
- `license_server/static/fonts/Roblox2017.ttf`
- `build_exe.bat`
