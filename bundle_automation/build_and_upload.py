"""Unattended Roblox bundle builder for the DENFI license server.

Runs on a Windows RDP machine via Task Scheduler (recommended: nightly).
End-to-end flow:

    1. Ask the license server for the current bundle's note (which holds
       the Roblox version-string of the last build).
    2. Ask Roblox what the latest WindowsPlayer version-string is.
    3. If they match, exit cleanly — nothing to do.
    4. Otherwise:
         a. Wipe any leftover %LOCALAPPDATA%\\Roblox so we know the version
            folder we end up with is the one we just installed.
         b. Download RobloxPlayerLauncher.exe and run it. The bootstrapper
            unpacks the player into %LOCALAPPDATA%\\Roblox\\Versions\\version-XXXX
            without needing a Roblox login (login is only required to
            actually JOIN a game, not to install).
         c. Locate the freshly-created version-XXX folder, sanity-check
            that RobloxPlayerBeta.exe is inside.
         d. Zip the *contents* of that folder (flat layout — matches the
            launcher's extract code, which strips a single top-level dir
            if present, but flat is the unambiguous case).
         e. POST the zip to /api/admin/upload_bundle with the bot token.
            The server picks the next integer version, prunes the oldest
            bundles past BUNDLE_RETENTION_COUNT, and from then on every
            launcher heartbeat picks it up automatically.
         f. Uninstall Roblox and wipe LOCALAPPDATA\\Roblox* +
            ProgramFiles*\\Roblox* so the RDP doesn't accumulate state
            between runs.

Required environment variables (set them once on the RDP user account
or pass them via the Task Scheduler action):

    LICENSE_SERVER_URL          e.g. https://your-license-server.example.com
    BUNDLE_AUTOMATION_TOKEN     same value as on the server

Optional:

    BUNDLE_BUILD_LOG_DIR        default: <script dir>\\logs
    BUNDLE_BUILD_KEEP_TEMP      "1" to skip cleanup for debugging

Exit codes:
    0   success (uploaded a new bundle OR no update was needed)
    1   network / Roblox CDN failure
    2   install failure (bootstrapper ran but no version folder appeared)
    3   server upload rejected
    4   missing required environment variable
    5   unexpected error (full traceback in the log file)
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile

# Python's bundled SSL doesn't trust anything by default on a fresh Windows
# install, so urlopen() against roblox.com fails with
# "CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate".
# truststore makes Python use Windows' system CA store instead, which is
# what the OS uses everywhere else and is always up to date. Falls back to
# certifi if truststore isn't installed; falls back to the default context
# if neither is available so the script never crashes at import time.
try:
    import truststore  # type: ignore
    truststore.inject_into_ssl()
except ImportError:
    try:
        import certifi  # type: ignore
        ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())  # type: ignore[attr-defined]
    except ImportError:
        pass

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LICENSE_SERVER_URL = os.environ.get("LICENSE_SERVER_URL", "").rstrip("/")
BUNDLE_AUTOMATION_TOKEN = os.environ.get("BUNDLE_AUTOMATION_TOKEN", "").strip()
KEEP_TEMP = os.environ.get("BUNDLE_BUILD_KEEP_TEMP", "").strip() == "1"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.environ.get("BUNDLE_BUILD_LOG_DIR", "").strip() or os.path.join(SCRIPT_DIR, "logs")

# Roblox endpoints. The deployment endpoint returns the current
# WindowsPlayer version string ("version-abc123def..."). The setup CDN
# serves the raw package zips for that version — no bootstrapper, no
# player executable is ever run, so Hyperion's VM detection never fires.
ROBLOX_VERSION_URL = "https://clientsettingscdn.roblox.com/v2/client-version/WindowsPlayer"
ROBLOX_SETUP_CDN = "https://setup.rbxcdn.com"

# Where each package gets extracted inside the version folder. This mapping
# is the same one the Roblox bootstrapper (and open-source clones like
# Bloxstrap) use internally. Packages not in this table are skipped —
# that's how we avoid pulling Studio / WebView2 installer junk.
ROBLOX_PACKAGE_DIRS = {
    "RobloxApp.zip": "",
    "WebView2.zip": "",
    "WebView2RuntimeInstaller.zip": "WebView2RuntimeInstaller",
    "shaders.zip": "shaders",
    "ssl.zip": "ssl",
    "content-avatar.zip": "content/avatar",
    "content-configs.zip": "content/configs",
    "content-fonts.zip": "content/fonts",
    "content-sky.zip": "content/sky",
    "content-sounds.zip": "content/sounds",
    "content-textures2.zip": "content/textures",
    "content-textures3.zip": "PlatformContent/pc/textures",
    "content-models.zip": "content/models",
    "content-platform-fonts.zip": "PlatformContent/pc/fonts",
    "content-platform-dictionaries.zip": "PlatformContent/pc/shared_compression_dictionaries",
    "content-terrain.zip": "PlatformContent/pc/terrain",
    "extracontent-luapackages.zip": "ExtraContent/LuaPackages",
    "extracontent-translations.zip": "ExtraContent/translations",
    "extracontent-models.zip": "ExtraContent/models",
    "extracontent-textures.zip": "ExtraContent/textures",
    "extracontent-places.zip": "ExtraContent/places",
}

# AppSettings.xml tells RobloxPlayerBeta.exe where the content folder is.
# The bootstrapper writes this at the end of install; since we skip the
# bootstrapper we write it ourselves.
ROBLOX_APP_SETTINGS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\r\n'
    '<Settings>\r\n'
    '\t<ContentFolder>content</ContentFolder>\r\n'
    '\t<BaseUrl>http://www.roblox.com</BaseUrl>\r\n'
    '</Settings>\r\n'
)

HTTP_TIMEOUT = 120  # seconds
INSTALL_TIMEOUT = 600  # bootstrapper can take a while on a slow link
UPLOAD_TIMEOUT = 1200  # zips are 150-200 MB — give the upload room

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_LINES: list[str] = []
_LOG_FILE: str | None = None


def _log_setup() -> None:
    global _LOG_FILE
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    _LOG_FILE = os.path.join(LOG_DIR, f"build_{ts}.log")


def log(msg: str) -> None:
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    _LOG_LINES.append(line)
    if _LOG_FILE:
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


def die(code: int, msg: str) -> "None":
    log(f"FATAL: {msg}")
    sys.exit(code)


# ---------------------------------------------------------------------------
# HTTP helpers (use the system urllib so there are zero pip dependencies on
# the RDP — install Python and that's it)
# ---------------------------------------------------------------------------


def _http_get_json(url: str, headers: dict | None = None, timeout: int = HTTP_TIMEOUT) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_download(url: str, dest: str, timeout: int = HTTP_TIMEOUT) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "DenfiBundleBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out, length=1024 * 1024)


# ---------------------------------------------------------------------------
# Roblox detection
# ---------------------------------------------------------------------------


def get_latest_roblox_version() -> str:
    """Return the current WindowsPlayer version string ('version-...')."""
    log(f"Querying Roblox: {ROBLOX_VERSION_URL}")
    data = _http_get_json(ROBLOX_VERSION_URL)
    # Response shape: {"version": "version-abc123def...", "clientVersionUpload": "..."}
    ver = (data.get("clientVersionUpload") or data.get("version") or "").strip()
    if not ver.startswith("version-"):
        raise RuntimeError(f"unexpected Roblox version response: {data!r}")
    return ver


def find_installed_version_folder() -> str | None:
    """Return the absolute path to the newest %LOCALAPPDATA%\\Roblox\\Versions\\version-* folder."""
    local = os.environ.get("LOCALAPPDATA", "")
    if not local:
        return None
    versions = os.path.join(local, "Roblox", "Versions")
    if not os.path.isdir(versions):
        return None
    candidates = []
    for name in os.listdir(versions):
        if not name.lower().startswith("version-"):
            continue
        full = os.path.join(versions, name)
        if not os.path.isdir(full):
            continue
        if not os.path.isfile(os.path.join(full, "RobloxPlayerBeta.exe")):
            continue
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            continue
        candidates.append((mtime, full))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# ---------------------------------------------------------------------------
# Server API
# ---------------------------------------------------------------------------


def server_get_status() -> dict:
    url = f"{LICENSE_SERVER_URL}/api/admin/bundle_status"
    log(f"Server status: {url}")
    return _http_get_json(url, headers={"X-Bundle-Token": BUNDLE_AUTOMATION_TOKEN})


def server_upload_bundle(zip_path: str, version: int, note: str) -> dict:
    """Raw-binary POST to /api/admin/upload_bundle. Body is the zip bytes
    streamed straight off disk; metadata travels in headers. Avoids
    multipart parsing AND keeps memory flat -- no 'requests' dep needed,
    system Python is enough."""
    file_size = os.path.getsize(zip_path)
    url = f"{LICENSE_SERVER_URL}/api/admin/upload_bundle"
    log(f"Uploading bundle ({file_size/1048576:.1f} MB) -> {url}")

    fh = open(zip_path, "rb")
    try:
        req = urllib.request.Request(url, data=fh, method="POST")
        req.add_header("X-Bundle-Token", BUNDLE_AUTOMATION_TOKEN)
        req.add_header("X-Bundle-Version", str(version))
        req.add_header("X-Bundle-Note", note)
        req.add_header("Content-Type", "application/zip")
        req.add_header("Content-Length", str(file_size))
        try:
            with urllib.request.urlopen(req, timeout=UPLOAD_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"server returned HTTP {e.code}: {body_txt}") from None
    finally:
        fh.close()


# ---------------------------------------------------------------------------
# Roblox install / uninstall
# ---------------------------------------------------------------------------


def kill_roblox_processes() -> None:
    if sys.platform != "win32":
        return
    names = [
        "RobloxPlayerBeta.exe",
        "RobloxPlayerLauncher.exe",
        "RobloxCrashHandler.exe",
        "RobloxStudioBeta.exe",
    ]
    for n in names:
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", n],
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
        except Exception:
            pass


def wipe_roblox_state(label: str) -> None:
    """Best-effort wipe of every Roblox-named folder under LOCALAPPDATA and
    Program Files. Mirrors the launcher's own cleanup so behavior is
    consistent. Never raises — this is best-effort cleanup."""
    log(f"Wiping Roblox state ({label})...")
    kill_roblox_processes()
    time.sleep(1.0)

    # 1. Best-effort uninstall via registry uninstall string
    if sys.platform == "win32":
        try:
            import winreg  # type: ignore
            for root_key in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for sub in (
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
                ):
                    try:
                        with winreg.OpenKey(root_key, sub) as k:
                            i = 0
                            while True:
                                try:
                                    name = winreg.EnumKey(k, i)
                                except OSError:
                                    break
                                i += 1
                                try:
                                    with winreg.OpenKey(k, name) as kk:
                                        try:
                                            disp = winreg.QueryValueEx(kk, "DisplayName")[0]
                                        except OSError:
                                            continue
                                        if "roblox" not in str(disp).lower():
                                            continue
                                        try:
                                            unins = winreg.QueryValueEx(kk, "QuietUninstallString")[0]
                                        except OSError:
                                            try:
                                                unins = winreg.QueryValueEx(kk, "UninstallString")[0]
                                            except OSError:
                                                continue
                                        log(f"  uninstall: {disp}")
                                        try:
                                            subprocess.run(
                                                unins, shell=True, timeout=120,
                                                capture_output=True,
                                            )
                                        except Exception as e:
                                            log(f"    failed: {e}")
                                except OSError:
                                    continue
                    except OSError:
                        continue
        except ImportError:
            pass

    # 2. Folder wipe — LocalAppData and Program Files roots
    roots = []
    local = os.environ.get("LOCALAPPDATA", "")
    if local and os.path.isdir(local):
        roots.append(local)
    for env in ("ProgramFiles(x86)", "ProgramFiles", "ProgramW6432"):
        p = os.environ.get(env, "")
        if p and os.path.isdir(p) and p not in roots:
            roots.append(p)

    for root in roots:
        try:
            entries = os.listdir(root)
        except OSError:
            continue
        for name in entries:
            if "roblox" not in name.lower() and "bloxstrap" not in name.lower():
                continue
            full = os.path.join(root, name)
            for attempt in range(3):
                try:
                    if os.path.islink(full):
                        os.unlink(full)
                    elif os.path.isdir(full):
                        shutil.rmtree(full, ignore_errors=False)
                    else:
                        os.remove(full)
                    log(f"  removed: {full}")
                    break
                except Exception:
                    time.sleep(0.5 * (attempt + 1))


def _parse_pkg_manifest(text: str) -> list[str]:
    """rbxPkgManifest.txt format:
        line 0: "v0" (format version)
        then repeating groups of 4 lines:
            <package name>
            <md5>
            <compressed size>
            <uncompressed size>
    We only care about the package names."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    # Skip leading format-version line if present (v0 / v1 / ...).
    start = 1 if lines[0].lower().startswith("v") and not lines[0].endswith(".zip") else 0
    names: list[str] = []
    for i in range(start, len(lines), 4):
        name = lines[i]
        if name.endswith(".zip"):
            names.append(name)
    return names


def install_roblox(work_dir: str, version: str) -> None:
    """Fetch Roblox player files directly from setup.rbxcdn.com and
    assemble them into %LOCALAPPDATA%\\Roblox\\Versions\\<version>\\.

    This skips the RobloxPlayerLauncher bootstrapper entirely, which is
    the ONLY component that launches RobloxPlayerBeta.exe (and therefore
    the only thing that trips Hyperion's 'Virtual Machine detected'
    dialog). Since we never execute any Roblox binary on the VPS, the
    anti-cheat has nothing to block."""
    local = os.environ.get("LOCALAPPDATA", "")
    if not local:
        raise RuntimeError("LOCALAPPDATA env var not set — can't place version folder")
    dest_root = os.path.join(local, "Roblox", "Versions", version)
    os.makedirs(dest_root, exist_ok=True)

    # 1. Grab the manifest that lists every package for this version.
    manifest_url = f"{ROBLOX_SETUP_CDN}/{version}-rbxPkgManifest.txt"
    log(f"Fetching package manifest -> {manifest_url}")
    req = urllib.request.Request(manifest_url, headers={"User-Agent": "DenfiBundleBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        manifest_text = resp.read().decode("utf-8", "replace")
    all_pkgs = _parse_pkg_manifest(manifest_text)
    log(f"  manifest lists {len(all_pkgs)} packages")

    # 2. Figure out which ones we actually need (player-only; skip Studio).
    wanted = [p for p in all_pkgs if p in ROBLOX_PACKAGE_DIRS]
    missing_map = [p for p in all_pkgs if p not in ROBLOX_PACKAGE_DIRS
                   and not p.startswith("Roblox") and "Studio" not in p]
    if missing_map:
        # Harmless — just means Roblox added a new package since this
        # mapping was written. Log it so we can update the table later.
        log(f"  note: {len(missing_map)} manifest entries have no known extract dir "
            f"(first few: {missing_map[:3]}) — skipping them")

    # 3. Download + extract each package. Parallelised because we have
    #    ~22 small zips and serial downloads waste time on high-latency
    #    links. zipfile is thread-safe when each worker uses its own
    #    ZipFile object, which we do.
    total_files = 0
    total_bytes = 0

    def _fetch_pkg(pkg: str) -> tuple[str, int, int]:
        url = f"{ROBLOX_SETUP_CDN}/{version}-{pkg}"
        local_zip = os.path.join(work_dir, pkg)
        req2 = urllib.request.Request(url, headers={"User-Agent": "DenfiBundleBuilder/1.0"})
        with urllib.request.urlopen(req2, timeout=HTTP_TIMEOUT) as r, open(local_zip, "wb") as out:
            shutil.copyfileobj(r, out, length=1024 * 1024)
        subdir = ROBLOX_PACKAGE_DIRS[pkg]
        target = os.path.join(dest_root, subdir) if subdir else dest_root
        os.makedirs(target, exist_ok=True)
        fcount = 0
        fbytes = 0
        with zipfile.ZipFile(local_zip, "r") as zf:
            zf.extractall(target)
            for info in zf.infolist():
                if not info.is_dir():
                    fcount += 1
                    fbytes += info.file_size
        try:
            os.remove(local_zip)
        except OSError:
            pass
        return (pkg, fcount, fbytes)

    log(f"Downloading + extracting {len(wanted)} packages from {ROBLOX_SETUP_CDN}...")
    from concurrent.futures import ThreadPoolExecutor, as_completed
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_pkg, p): p for p in wanted}
        done = 0
        for fut in as_completed(futures):
            pkg = futures[fut]
            try:
                name, fc, fb = fut.result()
                total_files += fc
                total_bytes += fb
                done += 1
                log(f"  [{done}/{len(wanted)}] {name}: {fc} files, {fb/1048576:.1f} MB")
            except Exception as e:
                errors.append(f"{pkg}: {e}")
                log(f"  FAILED {pkg}: {e}")

    if errors:
        raise RuntimeError(f"{len(errors)} package(s) failed to download: {errors[0]}")

    # 4. Write AppSettings.xml (the bootstrapper's final step — Roblox
    #    refuses to start without it).
    settings_path = os.path.join(dest_root, "AppSettings.xml")
    with open(settings_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(ROBLOX_APP_SETTINGS_XML)

    # 5. Sanity check the result — the player exe MUST be there.
    if not os.path.isfile(os.path.join(dest_root, "RobloxPlayerBeta.exe")):
        raise RuntimeError(
            f"install finished but RobloxPlayerBeta.exe is missing from {dest_root} — "
            f"Roblox may have changed their CDN layout"
        )

    log(f"Install complete: {total_files} files, {total_bytes/1048576:.1f} MB in {dest_root}")


# ---------------------------------------------------------------------------
# Zip
# ---------------------------------------------------------------------------


def zip_version_folder(version_folder: str, out_zip: str) -> None:
    """Zip the *contents* of version-XXX/ at the root of the archive (flat
    layout — RobloxPlayerBeta.exe lives at the top level, no wrapper dir)."""
    log(f"Zipping {version_folder} -> {out_zip}")
    base = os.path.abspath(version_folder)
    file_count = 0
    total_bytes = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
        for root, dirs, files in os.walk(base):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, base).replace("\\", "/")
                try:
                    zf.write(full, arcname=rel)
                    file_count += 1
                    total_bytes += os.path.getsize(full)
                except OSError as e:
                    log(f"  skip {rel}: {e}")
    log(f"  zipped {file_count} files, {total_bytes/1048576:.1f} MB raw -> {os.path.getsize(out_zip)/1048576:.1f} MB compressed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    _log_setup()
    log(f"=== DENFI bundle builder starting (log: {_LOG_FILE}) ===")

    if not LICENSE_SERVER_URL:
        die(4, "LICENSE_SERVER_URL env var is required")
    if not BUNDLE_AUTOMATION_TOKEN:
        die(4, "BUNDLE_AUTOMATION_TOKEN env var is required")
    if sys.platform != "win32":
        log("WARNING: not running on Windows; install/uninstall steps will no-op")

    # Step 1+2: compare current vs latest.
    try:
        latest_ver = get_latest_roblox_version()
    except Exception as e:
        die(1, f"could not fetch Roblox latest version: {e}")
    log(f"Roblox latest WindowsPlayer: {latest_ver}")

    try:
        status = server_get_status()
    except Exception as e:
        die(1, f"could not query license server: {e}")
    current = status.get("current") or {}
    next_version = int(status.get("next_version") or 1)
    current_note = (current.get("note") or "").strip()
    log(f"Server current bundle: v{current.get('version')} note={current_note!r}; next_version={next_version}")

    if current_note == latest_ver:
        log(f"Server already has bundle for {latest_ver} — nothing to do.")
        # Distinct exit code so the caller (license_server) can show
        # "no update needed" instead of generic success.
        return 10

    # Step 3: clean slate before install so the version folder we end up with
    # is unambiguously the one we just installed (not some leftover).
    if sys.platform == "win32":
        wipe_roblox_state("pre-install")

    # Step 4: install
    work_dir = tempfile.mkdtemp(prefix="denfi_bundle_")
    log(f"Workdir: {work_dir}")
    try:
        install_roblox(work_dir, latest_ver)
        version_folder = find_installed_version_folder()
        if not version_folder:
            die(2, "install finished but no Roblox/Versions/version-* folder appeared")
        log(f"Installed: {version_folder}")

        # Sanity check: the folder we're about to zip MUST match the
        # latest version string we got from the CDN. If a stale
        # version-* leftover survived the pre-install wipe (or Roblox
        # silently installed something else), refuse to publish a
        # mislabelled bundle -- the operator can investigate the
        # leftover by hand.
        installed_basename = os.path.basename(version_folder.rstrip("\\/"))
        if installed_basename != latest_ver:
            die(2, f"installed folder {installed_basename!r} does not match "
                   f"latest CDN version {latest_ver!r} -- refusing to upload "
                   f"a mislabelled bundle")

        # Step 5: zip
        zip_path = os.path.join(work_dir, f"roblox_bundle_{latest_ver}.zip")
        zip_version_folder(version_folder, zip_path)

        # Step 6: upload
        try:
            result = server_upload_bundle(zip_path, version=next_version, note=latest_ver)
        except Exception as e:
            die(3, f"upload failed: {e}")
        if not result.get("ok"):
            die(3, f"server rejected upload: {result}")
        log(f"Upload OK: bundle_id={result.get('bundle_id')} v{result.get('version')} pruned={result.get('pruned')}")
    finally:
        # Step 7: post-install cleanup so the RDP doesn't accumulate state
        if sys.platform == "win32":
            wipe_roblox_state("post-install")
        if not KEEP_TEMP:
            shutil.rmtree(work_dir, ignore_errors=True)
        else:
            log(f"KEEP_TEMP=1 — leaving {work_dir} on disk for inspection")

    log("=== bundle builder finished ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        log("UNCAUGHT EXCEPTION:")
        for line in traceback.format_exc().splitlines():
            log("  " + line)
        sys.exit(5)
