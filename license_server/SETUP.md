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

## Step 4 — Configure the server (password, shared key, port)

These are the three settings you should configure **before** starting the server for the first time. All of them are set as Windows environment variables.

### 4a. Set the admin password

By default, the admin login is **`admin` / `admin`** — anyone who finds your server URL can log in. **Change this immediately.**

Open **PowerShell as Administrator** (right-click PowerShell → Run as Administrator) and run:

```
setx LICENSE_ADMIN_PASSWORD "YourStrongPasswordHere123!"
```

Use a strong password — long, mixed case, numbers, symbols. There is no in-app password change yet, so this `setx` command is the only way to change it.

### 4b. Set the shared license-signing key

This is the secret the server uses to sign license tokens that the launcher checks. Pick a long random string and **never change it again** — if you change it later, every license you've ever issued will stop working.

```
setx LICENSE_SHARED_SECRET "PickALongRandomString_AtLeast32Chars_KeepSecret"
```

If you don't set this, the server uses a built-in default. That works, but anyone who has the source code knows what it is, so for production you should set your own.

### 4c. (Optional) Set the Flask session key

This keeps admins logged in across server restarts. Without it, every restart logs everyone out.

```
setx FLASK_SECRET_KEY "AnotherLongRandomString_DifferentFromTheOneAbove"
```

### 4d. (Optional) Choose a different port

The server runs on port **5000** by default. If port 5000 is already in use (or you want a different one), set:

```
setx PORT "8080"
```

Replace `8080` with whatever port you want. Common choices: `80` (standard HTTP, lets users skip typing the port), `8080`, `5000`.

> **Important:** After running any `setx` command, **close all PowerShell / Command Prompt windows and open a fresh one.** Environment variables only apply to new windows. If you skip this, the server will still use the old values.

### Verify your settings

In a fresh PowerShell window, type:

```
echo %LICENSE_ADMIN_PASSWORD%
echo %LICENSE_SHARED_SECRET%
echo %PORT%
```

(Or in PowerShell: `$env:LICENSE_ADMIN_PASSWORD`)

You should see the values you set. If you see blank lines, the variable wasn't saved or you didn't open a fresh window.

---

## Step 5 — Start the server

In a **fresh** PowerShell window (so it picks up the env vars from Step 4), navigate to the `license_server` folder and run:

```
python server.py
```

You should see something like:

```
* Running on http://0.0.0.0:5000
```

(or whatever port you chose in Step 4d).

The admin panel is now live at:

- **http://localhost:5000** when you're on the server itself
- **http://YOUR_SERVER_IP:5000** from anywhere on the internet (once the firewall is open — see Step 6)

Log in with username `admin` and the password you set in Step 4a.

To stop the server, press **Ctrl + C** in the PowerShell window.

---

## Step 6 — Open the port in the firewall

By default, Windows blocks incoming connections. Even if the server is running, no one outside the machine can reach it until you open the port.

### 6a. Open the port in Windows Firewall

1. Press **Win + R**, type `wf.msc`, press Enter. (This opens Windows Defender Firewall with Advanced Security.)
2. Click **Inbound Rules** (left sidebar) → **New Rule…** (right sidebar).
3. Choose **Port** → click **Next**.
4. Choose **TCP**, then **Specific local ports** and type **`5000`** (or whatever port you chose in Step 4d) → **Next**.
5. Choose **Allow the connection** → **Next**.
6. Tick **all three** boxes (Domain, Private, Public) → **Next**.
7. Name it **"License Server"** → **Finish**.

### 6b. Open the port at your VPS provider (if applicable)

If your server is a VPS (Hostinger, AWS, DigitalOcean, Vultr, Contabo, etc.), the provider also has its own firewall in front of your machine. You must open the port there too:

| Provider | Where to open the port |
|---|---|
| Hostinger | hPanel → VPS → Firewall → Add rule (TCP, port 5000) |
| AWS | EC2 → Security Groups → Inbound rules → Add rule |
| DigitalOcean | Networking → Firewalls → Edit rule |
| Vultr / Contabo | Settings → Firewall (usually open by default) |

If you're on a home internet connection (not a VPS), you'll also need to **port-forward** port 5000 in your home router and use your public IP — but I'd really recommend a VPS instead, home internet is not reliable enough for paying customers.

### 6c. Test that the port is open

From a **different machine** (not the server), open a browser and go to:

```
http://YOUR_SERVER_IP:5000
```

You should see the admin login page. If it times out or refuses connection, the firewall isn't open yet — go back through 6a and 6b.

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
