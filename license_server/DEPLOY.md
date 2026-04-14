# License Server Deployment Guide

## Quick Setup on Windows Server

### 1. Install Python
Download Python 3.11+ from https://python.org
Check "Add Python to PATH" during install.

### 2. Copy Files
Copy the entire `license_server/` folder to your server (e.g. `C:\LicenseServer`).

### 3. Install Dependencies
```
cd C:\LicenseServer
pip install flask
```

### 4. Configure Environment Variables
Set these before running the server (each on its own line):
```
set LICENSE_ADMIN_PASSWORD=YourStrongPassword
set LICENSE_SHARED_SECRET=YourSharedSecret
set LICENSE_PORT=3842
```

The shared secret must match what you entered during the launcher build.

### 5. Open Firewall
```
netsh advfirewall firewall add rule name="License Server" dir=in action=allow protocol=TCP localport=3842
```

### 6. Run
```
python server.py
```

### 7. Run as Background Service (Optional)
To keep the server running after you close the terminal:

**Using nssm (recommended for Windows):**
1. Download nssm from https://nssm.cc
2. Run: `nssm install LicenseServer "C:\Python311\python.exe" "C:\LicenseServer\server.py"`
3. Run: `nssm set LicenseServer AppDirectory "C:\LicenseServer"`
4. Run: `nssm set LicenseServer AppEnvironmentExtra "LICENSE_ADMIN_PASSWORD=YourPassword" "LICENSE_SHARED_SECRET=YourSecret" "LICENSE_PORT=3842"`
5. Run: `nssm start LicenseServer`

**Using Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "At startup"
4. Action: Start a program
5. Program: `python`
6. Arguments: `server.py`
7. Start in: `C:\LicenseServer`

## Admin Dashboard

- Login at your server URL
- Default password: `admin` (change this!)
- Create keys with custom duration (countdown starts only when key is activated)
- Monitor who's online in real-time
- Revoke/delete keys instantly
- View full license history with activation timestamps

## License Flow

1. You create a key in the dashboard — it starts as **Pending**
2. User enters the key in the launcher — key becomes **Active** and countdown starts
3. Dashboard shows real-time status: Online/Offline, time remaining, last IP
4. When time runs out — key becomes **Expired** and the `.license_key` file is auto-deleted
5. You can **Revoke** a key at any time — user gets kicked within 15 seconds

## Security Notes

- Change the default admin password immediately
- The shared secret must match on both server and launcher
- Access the dashboard via `http://` not `https://` (unless you set up SSL)
- Back up `licenses.db` regularly to preserve license data
