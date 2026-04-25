# License Server - Setup Guide

Follow these steps one by one in Command Prompt on your Windows server.


## Step 1: Install Python

Download Python from https://python.org/downloads

IMPORTANT: Use the **full Windows installer** (the file ending in `.exe`).
Do NOT use the "Windows embeddable package" zip — it is missing modules
that the build engine needs, and your built launchers will fail with
"Server unreachable: No module named '_socket'".

During install, check the box that says "Add Python to PATH".

After install, open Command Prompt and type:
```
python --version
```
You should see something like "Python 3.11.x". If you get an error, restart your PC and try again.


## Step 2: Create folder and copy files

Create a folder on your server:
```
mkdir C:\LicenseServer
```

Copy these files into `C:\LicenseServer`:
- `server.py`
- The `templates` folder (with all the .html files inside it)

Your folder should look like this:
```
C:\LicenseServer\
    server.py
    templates\
        base.html
        create.html
        dashboard.html
        history.html
        login.html
```


## Step 3: Install Flask

Type this and press Enter:
```
pip install flask
```

Wait for it to finish.

If you also want to **build launcher .exe files** on this server (using the admin Builds page), install these too:
```
pip install PyQt5 Pillow requests pyinstaller
```


## Step 4: Open the firewall port

Type this and press Enter:
```
netsh advfirewall firewall add rule name="License Server" dir=in action=allow protocol=TCP localport=3842
```

You should see "Ok."


## Step 5: Set your passwords AND start the server (one line)

Replace the word `admin` below with whatever you want to use, and
replace `dprs.b-cdn.net` with your actual CDN/public domain, then
copy the whole line, paste it into the Command Prompt (after you have
`cd`'d into the license_server folder — see Step 6), and press Enter:

```
cmd /v:on /c "set "X=admin" && set "LICENSE_ADMIN_PASSWORD=!X!" && set "LICENSE_SHARED_SECRET=!X!" && set "BUNDLE_AUTOMATION_TOKEN=!X!" && set "LICENSE_PORT=3842" && set "ADMIN_TRUST_PROXY=1" && set "ADMIN_PUBLIC_HOST=dprs.b-cdn.net" && python server.py"
```

That uses `admin` for all three (admin password, shared secret, and
bundle token), sets the port to 3842, enables CDN/proxy trust, sets
your public host, and starts the server — all in one shot.

NOTE: The `cmd /v:on /c` prefix and the `!X!` (instead of `%X%`) are
required. Without them, Windows expands `%X%` BEFORE `set X=admin`
runs, so the password ends up empty and login fails.

IMPORTANT: Whatever value you pick for the shared secret must match
what you entered when building the launcher .exe — otherwise the
launchers will be rejected. So either keep `admin` here AND when
you build the launcher, or change both to the same value.

WHAT IS BUNDLE_AUTOMATION_TOKEN?
It is the password the server uses to talk to itself when you click
the "Update Roblox bundle now" button on the admin page. Without it,
the button will fail with "Builder config error". Pick any long random
string (the example above works fine). You only need to remember it
if you ever run bundle_automation\build_and_upload.py by hand.

WHAT IS ADMIN_TRUST_PROXY and ADMIN_PUBLIC_HOST?
Set ADMIN_TRUST_PROXY=1 when your server sits behind a CDN or reverse
proxy (BunnyCDN, Cloudflare, nginx, etc.). This tells the server to
trust forwarded headers from the proxy instead of the raw connection IP.
Set ADMIN_PUBLIC_HOST to your public domain (e.g. dprs.b-cdn.net) so
the server accepts form submissions that come through your CDN. Without
these two settings, edit/delete/save actions in the admin panel will be
rejected with "Cross-origin request rejected" when accessed via CDN.


## Step 6: Go to the folder and start the server

First go to the folder:
```
cd C:\LicenseServer
```
(press Enter)

Then paste the one-liner from Step 5 and press Enter. You should see:
```
License server starting on port 3842
Dashboard: http://0.0.0.0:3842/
```

Now open your browser and go to: http://YOUR_SERVER_IP:3842

Log in with the password you set in Step 5.

IMPORTANT: Use http:// NOT https://


## Step 8: Make it run forever (optional)

If you close the Command Prompt window, the server stops.
To make it run as a Windows service that auto-starts:

Download nssm from https://nssm.cc/release/nssm-2.24.zip

Extract it, then type each line ONE AT A TIME:

First, find where Python is installed:
```
where python
```
(note the path it shows, like C:\Python311\python.exe)

Then type these one by one (replace the Python path if yours is different):

```
C:\nssm\nssm-2.24\win64\nssm.exe install LicenseServer "C:\Python311\python.exe" "C:\LicenseServer\server.py"
```
(press Enter)

```
C:\nssm\nssm-2.24\win64\nssm.exe set LicenseServer AppDirectory "C:\LicenseServer"
```
(press Enter)

```
C:\nssm\nssm-2.24\win64\nssm.exe set LicenseServer AppEnvironmentExtra "LICENSE_ADMIN_PASSWORD=admin" "LICENSE_SHARED_SECRET=DENFI_LICENSE_SECRET_KEY_2024" "LICENSE_PORT=3842" "BUNDLE_AUTOMATION_TOKEN=denfi_bundle_secret_2026" "ADMIN_TRUST_PROXY=1" "ADMIN_PUBLIC_HOST=dprs.b-cdn.net"
```
(press Enter)

```
C:\nssm\nssm-2.24\win64\nssm.exe start LicenseServer
```
(press Enter)

Done! The server will now auto-start every time your server boots up.


## How it works

1. You create a key in the dashboard — it starts as **Pending**
2. User enters the key in the launcher — key becomes **Active** and countdown starts
3. Dashboard shows real-time: Online/Offline, time remaining, last IP
4. When time runs out — key becomes **Expired**, user's license file is auto-deleted
5. You can **Revoke** a key anytime — user gets kicked within 15 seconds


## Security

- Change the default admin password to something strong
- The shared secret must be the same on both server and launcher
- Back up `licenses.db` regularly (this file stores all your license data)
