# Portable Roblox Launcher

## Overview
The Portable Roblox Launcher is a zero-interaction application designed to provide a seamless, portable Roblox experience. It automates license validation, OTA updates, Roblox synchronization, and login management, allowing multiple Roblox instances to run concurrently. The project aims to offer a robust and easily deployable solution for managing Roblox environments, particularly for setups requiring controlled access and updates.

Key capabilities include:
- Automatic license validation with an online server.
- Over-the-air (OTA) updates for the launcher itself.
- Custom branded splash screens.
- Automatic synchronization of Roblox game files.
- Clearing of login data for fresh sessions.
- Multi-instance support via mutex handling.
- Background process for mutex management and cleanup.

## User Preferences
I prefer simple language and direct instructions. I want the agent to prioritize high-level architectural tasks over granular code changes initially. When making significant changes, please ask for confirmation first. I prefer an iterative development approach, where features are implemented and tested in small, manageable steps. Do not make changes to files within the `license_server/templates/` folder without explicit instruction.

## System Architecture

### UI/UX
- **Splash Screen:** Custom-named splash screen (e.g., "DENFI ROBLOX PORTABLE") displaying a logo, custom name, "PORTABLE", a progress bar, and the Roblox version.
- **Admin Panel:** Features a persistent left sidebar and topbar shell (vanilla CSS, Lucide icons as SVG). The dashboard includes a 4-card KPI strip (Total / Online / Suspended / Expiring < 24h) and icon-button row actions.
- **Mobile Responsiveness:** For screens <900px, the sidebar collapses into a hamburger drawer, KPI strips stack, and tables scroll horizontally.
- **Update Progress Dialog:** A dedicated frameless `UpdateProgressDialog` with app name, target version, download progress (MB/total, percentage, `QProgressBar`), and a "Update in progress" warning.
- **Theme:** Uses a black background (#0a0a0a) with an orange accent (#ff6a00, lighter #ff8c33, darker #cc5500).

### Technical Implementations
- **Zero-Interaction Execution:** Double-click .exe to initiate all processes automatically.
- **Build Process:** A build script customizes the launcher with Roblox path, launcher name, and license server URL, baking these into the executable.
- **Roblox Synchronization:** Checks `%LOCALAPPDATA%\Roblox\Versions\` for the latest Roblox version, compares it with the portable folder using fingerprinting, and syncs automatically if updates are detected or on first run.
- **Login Management:** Deletes `%LOCALAPPDATA%\Roblox\rbx-storage.db` before and after launching Roblox to ensure fresh logins.
- **Multi-Instance Support:** Grabs the `ROBLOX_singletonEvent` mutex to allow multiple Roblox instances to coexist. The launcher stays running hidden in the background to hold the mutex.
- **License System:**
    - Server-side license management with an admin dashboard for key creation, monitoring, and revocation.
    - Keys start as **Pending** and activate upon first use, triggering a countdown.
    - **Embedded Key Mode:** Allows baking a license key directly into the EXE.
    - **Encrypted Key File:** `.license_key` file is XOR-encrypted and saved next to the EXE.
    - **Validation:** Validates with the server before launching and re-checks every 10 seconds.
    - **IP Binding:** Subnet-based IP binding (first 3 octets) to support diskless setups.
    - **Suspended State:** Licenses can be suspended by admin or automatically due to IP mismatch.
    - **Trial Mode:** Public download links mint a one-shot 24h-capped trial license (`/api/trial_register`, signed). Launcher reports a stable per-PC fingerprint (SHA-256 of MachineGuid + motherboard + disk serial) and the server creates an auto-block (`trial_blocks` table) keyed on both IP and machine_hash. The per-build **Trial duration** (Build config form, default 24h, hard-capped at 24h) is the single source of truth for both license lifetime AND link availability — `_auto_purge_inactive_trial_configs` case (c) deletes the trial config (page + EXE + icon) once `now - created_at > trial_duration_seconds`. The **Trial Blocks** admin page (Management group) holds only the **Default cooldown** (default 7 days, 0 = disable auto-blocks) and the manual block add/edit/delete UI. Each license row stores its `machine_hash`, surfaced as a column on the History page.
    - **Offline Grace:** Tolerates 3 consecutive server failures before locking.
    - **HMAC Signing:** Server signs responses with HMAC to prevent tampering.
- **OTA Update System:**
    - **Server-side Builds:** Admin configures per-user build configurations (app name, icon, Roblox path, embedded license).
    - **Build Engine:** Uses PyInstaller to create personalized `.exe` files, patching `launcher.py` with config values.
    - **Version Management:** Admin specifies version numbers (X.Y.Z) and triggers "Build All".
    - **Config-change Detection:** Uses `config_hash` to trigger updates even without a version bump if configurations change.
    - **Launcher OTA:** Launcher checks `/api/update_check` and downloads new `.exe` with progress shown.
    - **Self-Replace:** Uses a `.bat` script for atomic self-replacement on Windows.
    - **Download Tokens:** Short-lived tokens for update downloads.
    - **SHA-256 Verification:** Verifies downloaded binaries.
- **Multi-Instance Flow:** The launcher ensures fresh logins and mutex management for each Roblox instance.
- **Single-Instance Lock & Update Safety:**
    - Uses a Windows kernel mutex for one launcher per install.
    - `.update_state` JSON file manages update phases; heartbeats prevent stale locks.
    - Atomic update swap using `os.replace` with rollback capability.
    - Post-update restart mechanism with mutex re-acquisition.
    - Startup recovery from `.bak` file in case of mid-swap interruption.

### Feature Specifications
- **Telegram Backups:** Admin page `/backups` allows scheduling `licenses.db` backups to Telegram via `sendDocument` using a bot token and chat ID. Settings are stored in `license_server/backup_settings.json`.
- **License Statuses:** `pending`, `active`, `expired`, `revoked`, `deleted`, `suspended`.
- **OTA Database Tables:** `build_configs`, `builds`, `build_artifacts`, and `licenses.launcher_version` for tracking build and update states.
- **OTA API Endpoints:** A comprehensive set of endpoints for update checks, downloads, build triggers, status monitoring, artifact downloads, and progress reporting.

## External Dependencies
- **Python 3.11**
- **PyQt5:** For GUI elements (splash screen, update dialog).
- **Pillow:** Image processing (e.g., for icon conversion).
- **PyInstaller:** For packaging Python applications into standalone executables.
- **ctypes:** For Windows-specific API interactions (e.g., mutex handling).
- **Flask:** Web framework for the license server and admin dashboard.
- **Flask-SocketIO:** For real-time communication (e.g., build progress).
- **SQLite:** Database for license management (`licenses.db`).
- **HMAC-SHA256:** For signing API responses.
- **Telegram Bot API:** For sending backup documents to Telegram.