# License Server — Setup Guide

Step-by-step instructions for installing and running the DENFI license server
on a fresh Windows machine (RDP / VPS / your own PC).

If you're on Linux, the steps are the same — just use `sudo apt install python3 python3-pip` instead of the Windows installer.

---

## What you need before you start

- A Windows machine you can leave running 24/7 (RDP, VPS, or your own PC)
- Administrator access on that machine
- Internet connection
- Roughly 10 minutes

---

## Step 1 — Install Python

1. Go to https://www.python.org/downloads/
2. Download **Python 3.11** (or newer — 3.12, 3.13 are fine).
3. Run the installer.
4. **VERY IMPORTANT:** On the first installer screen, tick the box that says **"Add Python to PATH"** at the bottom. If you forget this, nothing else will work.
5. Click **Install Now** and wait for it to finish.

**Verify it worked.** Open a new PowerShell or Command Prompt window and type:

```
python --version
```

You should see something like `Python 3.11.x`. If you see "command not found", Python wasn't added to PATH — uninstall and reinstall, ticking the box.

---

## Step 2 — Copy the `license_server` folder to your machine

Put the entire `license_server` folder anywhere you like, for example:

```
C:\license_server
```

Avoid paths with spaces or non-English characters (e.g. don't use `C:\Users\Иван\Рабочий стол\`).

---

## Step 3 — Install the Python packages the server needs

Open PowerShell or Command Prompt **inside the `license_server` folder**.
(Easy way: open the folder in File Explorer, hold **Shift**, right-click an empty area, choose **Open PowerShell window here**.)

Then run:

```
pip install -r requirements.txt
```

This installs:

- **flask** — the web framework that runs the admin panel
- **flask-socketio** — live updates on the Builds page
- **Pillow** — image handling for the launcher icons
- **pyinstaller** — compiles the launcher `.exe` files for your users

Wait until it finishes. You'll see "Successfully installed ..." at the end.

---

## Step 4 — Set your admin password (recommended, but optional)

By default the admin login is:

- **Username:** `admin`
- **Password:** `admin`

**You should change this before going live.** To set your own password, open PowerShell as Administrator and run:

```
setx LICENSE_ADMIN_PASSWORD "YOUR_STRONG_PASSWORD_HERE"
```

Then **close and reopen** PowerShell so the new password is picked up.

You can also set:

- `LICENSE_SHARED_SECRET` — the secret used to sign license tokens. Change this once and never change it again, otherwise all existing licenses break.
- `FLASK_SECRET_KEY` — optional. Used for admin sessions. If unset, a random one is generated each time the server starts (which logs admins out on every restart).

---

## Step 5 — Start the server

In the same PowerShell window, inside the `license_server` folder, run:

```
python server.py
```

You should see something like:

```
* Running on http://0.0.0.0:5000
```

The admin panel is now live at **http://localhost:5000** on the server itself, and at **http://YOUR_SERVER_IP:5000** from anywhere on the internet.

Log in with `admin` / `admin` (or whatever password you set in Step 4).

To stop the server, press **Ctrl + C** in the PowerShell window.

---

## Step 6 — Make sure port 5000 is open

If users can't reach the server from outside:

1. Open **Windows Defender Firewall** → **Advanced settings**.
2. **Inbound Rules** → **New Rule** → **Port** → **TCP** → **Specific local ports: 5000** → **Allow** → tick all profiles → name it "License Server".

If you're on a VPS (Hostinger, AWS, etc.), also open port 5000 in the provider's control panel / security group.

---

## Step 7 — Keep the server running 24/7 (optional but recommended)

If you just close the PowerShell window, the server stops. To keep it running after you log out of RDP:

**Easy option — NSSM (free):**

1. Download NSSM from https://nssm.cc/download
2. Extract `nssm.exe` somewhere (e.g. `C:\nssm\nssm.exe`)
3. Open PowerShell as Administrator and run:
   ```
   C:\nssm\nssm.exe install LicenseServer
   ```
4. In the dialog:
   - **Path:** `C:\Python311\python.exe` (your Python install path)
   - **Startup directory:** `C:\license_server`
   - **Arguments:** `server.py`
5. Click **Install service**.
6. Start it: `nssm start LicenseServer`

Now the server starts automatically with Windows and runs even when no one is logged in.

To stop it: `nssm stop LicenseServer`. To remove it: `nssm remove LicenseServer`.

---

## Step 8 — First-time admin checklist

Once the server is running and you can log in, do these in order:

1. **Change the admin password** (if you didn't set the env var in Step 4) — currently no in-app change, so use Step 4's `setx` method.
2. **Upload `launcher.py`** on the **Server Files** page so the build engine has the source code.
3. **Create a build config** on the **Builds** page (app name, icon, Roblox path, etc.) for each customer.
4. **Build version 1.0.0** so there's an initial `.exe` to give to customers.
5. **Configure Telegram backups** on the **Backups** page (bot token + chat ID + schedule). This is your safety net if the server dies.
6. **Create your first license key** on the **Dashboard**.

---

## Troubleshooting

**`pip` is not recognized**
Python wasn't added to PATH. Reinstall Python and tick the box in Step 1.

**`ModuleNotFoundError: No module named 'flask'`**
You skipped Step 3. Run `pip install -r requirements.txt` inside the `license_server` folder.

**Server starts but users can't connect**
- Firewall is blocking port 5000 → see Step 6.
- VPS provider has port 5000 closed → open it in their dashboard.
- You're testing from inside the server itself — try from another machine.

**`Address already in use` on port 5000**
Another program (or another copy of the server) is using port 5000. Either stop it, or run on a different port:
```
set PORT=5001
python server.py
```

**Admin panel works but launcher updates are slow for customers in another country**
Read **DEPLOY.md** in this folder — it shows how to switch Windows from CUBIC to CTCP for much faster long-distance downloads. Free, 2 minutes, no reboot.

**Forgot admin password**
Set it again with `setx LICENSE_ADMIN_PASSWORD "newpassword"` in PowerShell (Admin), close and reopen PowerShell, restart the server.

---

## Files in this folder

| File | What it does |
|---|---|
| `server.py` | The main Flask server + admin panel + build engine. This is what you run. |
| `telegram_backup.py` | Sends `licenses.db` backups to your Telegram chat on a schedule. |
| `requirements.txt` | List of Python packages to install (used by `pip install -r`). |
| `licenses.db` | SQLite database — all your license keys, history, build configs. **Back this up.** |
| `templates/` | HTML pages for the admin panel. |
| `static/` | CSS, icons, fonts for the admin panel. |
| `build_icons/` | Icons uploaded for build configs. |
| `splash_logo.png` / `splash_logo.gif` | Logos shown on the launcher splash screen. |
| `Roblox2017.ttf` | Font baked into the launcher splash screen. |
| `DEPLOY.md` | Optional: speed up the server for international customers. |
| `SETUP.md` | This file. |

---

## What to back up

If your server dies, you only need these to recover:

- `licenses.db` (your entire database — most important)
- `backup_settings.json` (Telegram backup config — only exists after you set it up)
- The `build_icons/` folder (your customer icons)

The Telegram backup feature already handles `licenses.db` automatically once you set it up in Step 8 — that's why it's worth doing.

Everything else can be re-downloaded from your source / git repo.
