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


## Step 5: Set your passwords

Copy this whole line, paste it into the Command Prompt, then press Enter:

```
set LICENSE_ADMIN_PASSWORD=admin && set LICENSE_SHARED_SECRET=DENFI_LICENSE_SECRET_KEY_2024 && set LICENSE_PORT=3842 && set BUNDLE_AUTOMATION_TOKEN=denfi_bundle_secret_2026
```

That sets all four at once.

(If you'd rather do them one at a time, that also works — type each `set ...` line on its own and press Enter.)

IMPORTANT: The shared secret must match what you entered when building the launcher .exe

WHAT IS BUNDLE_AUTOMATION_TOKEN?
It is the password the server uses to talk to itself when you click
the "Update Roblox bundle now" button on the admin page. Without it,
the button will fail with "Builder config error". Pick any long random
string (the example above works fine). You only need to remember it
if you ever run bundle_automation\build_and_upload.py by hand.


## Step 6: Go to the folder

```
cd C:\LicenseServer
```
(press Enter)


## Step 7: Start the server

```
python server.py
```
(press Enter)

You should see:
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
C:\nssm\nssm-2.24\win64\nssm.exe set LicenseServer AppEnvironmentExtra "LICENSE_ADMIN_PASSWORD=admin" "LICENSE_SHARED_SECRET=DENFI_LICENSE_SECRET_KEY_2024" "LICENSE_PORT=3842" "BUNDLE_AUTOMATION_TOKEN=denfi_bundle_secret_2026"
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
