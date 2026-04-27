---
title: Fix 'No module named _socket' error in built launchers
---
# Fix "No module named '_socket'" in built launcher

## What & Why
After rebuilding a launcher .exe and running it on a customer PC, the activation screen shows **"Server unreachable: No module named '_socket'"** — the launcher is unusable because it cannot reach the license server. Root cause: the PyInstaller build invocation in `license_server/server.py` does not declare any hidden imports, so on certain build-server Python installs (notably the **embeddable Python** zip distribution, or installs where antivirus has quarantined `_socket.pyd`), the `_socket` C-extension is silently omitted from the bundled .exe. Because the launcher uses `urllib.request.urlopen` (which depends on `_socket` and `_ssl`) for every license check, the launcher loses its ability to talk to the server even though it starts up fine.

The same class of problem can also strip `_ssl`, `_hashlib`, `_bz2`, `_lzma`, and a few others, so we should fix it generally rather than only for `_socket`.

We also want the build to **fail loudly with a clear error message** if the build-server's Python is missing `_socket`/`_ssl` BEFORE PyInstaller starts, so the operator immediately knows to fix their Python install instead of shipping a broken .exe to customers.

## Done looks like
- Newly built launchers can reach the license server. The "No module named '_socket'" error never appears again on a fresh build.
- HTTPS license-server URLs also work (so `_ssl` is bundled, not just `_socket`).
- If the operator's build-server Python is broken (missing `_socket` or `_ssl`), the **Builds** page shows a clear, actionable error like "Build server Python is missing `_socket`. Please reinstall full Python from python.org (do not use the embeddable distribution)." instead of producing a silently-broken .exe.
- `SETUP.md` mentions the embeddable-Python pitfall in one short note so future operators don't fall into it.

## Out of scope
- The `_MEI` cleanup warning. That is a separate, mostly-cosmetic issue already partially addressed in launcher.py via the detached-Roblox-process change. A dedicated follow-up for `_MEI` would switch builds from `--onefile` to `--onedir` or wrap the .exe in a small bootstrapper, neither of which is needed to fix the actual server-unreachable bug.
- Switching the launcher's HTTP client from `urllib` to `requests` (would also work, but is a larger change and still ultimately depends on `_socket`).
- Any change to the launcher's runtime behavior or update flow.

## Steps
1. **Add explicit hidden imports to the PyInstaller build command.** Extend the `cmd` list assembled around `license_server/server.py:1441` to include `--hidden-import` flags for `_socket`, `socket`, `ssl`, `_ssl`, `select`, `_hashlib`, `_bz2`, `_lzma`, and `encodings.idna`. These are the modules `urllib`/`http.client` pull in via TLS-capable connections; declaring them explicitly removes the dependency on PyInstaller's autodetection working perfectly on every operator's machine.

2. **Pre-build sanity check on the build-server Python.** Before invoking PyInstaller, run a quick `subprocess.run([sys.executable, "-c", "import _socket, _ssl, ssl, socket"])`. If it fails, abort the build for this config with a clear status message ("Build server Python is missing required modules: <name>. Reinstall Python from python.org — do not use the embeddable distribution.") and surface it to the Builds page through the existing build-progress / build-history channels.

3. **Document the embeddable-Python pitfall.** Add one short paragraph to `license_server/SETUP.md` Step 1 noting that the **full** Python installer from python.org must be used, not the "embeddable" zip, because the embeddable distribution is missing the modules PyInstaller needs to bundle.

4. **Manual verification on a fresh rebuild.** After the fix, the operator rebuilds one launcher config from the Builds page, copies the new .exe to a clean test machine, and confirms the activation screen successfully reaches the server (no "No module named '_socket'" error). This step is operator-side because PyInstaller runs only on Windows.

## Relevant files
- `license_server/server.py:1432-1499`
- `license_server/SETUP.md`
- `launcher.py:1001-1115`