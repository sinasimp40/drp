# License Server Deployment Guide

## Quick Setup on RDP Server (144.31.48.238)

### 1. Install Python
Download Python 3.11+ from https://python.org
Check "Add Python to PATH" during install.

### 2. Copy Files
Copy the entire `license_server/` folder to your RDP server.

### 3. Install Dependencies
```
cd license_server
pip install flask
```

### 4. Configure
Edit `server.py` and change these values:
- `ADMIN_PASSWORD` - Set a strong admin password (line near top)
- `SHARED_SECRET` - Must match the launcher's secret (keep both the same)

Or set environment variables:
```
set LICENSE_ADMIN_PASSWORD=YourStrongPassword
set LICENSE_PORT=3842
```

### 5. Run
```
python server.py
```

Server will start on port 3842 by default.
Dashboard: http://144.31.48.238:3842/

### 6. Run as Background Service (Optional)
To keep the server running after you close the terminal:

**Using nssm (recommended for Windows):**
1. Download nssm from https://nssm.cc
2. Run: `nssm install LicenseServer`
3. Set path to Python and script
4. Start the service

**Using Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "At startup"
4. Action: Start a program
5. Program: `python`
6. Arguments: `server.py`
7. Start in: `C:\path\to\license_server`

### 7. Firewall
Make sure port 3842 is open in Windows Firewall:
```
netsh advfirewall firewall add rule name="License Server" dir=in action=allow protocol=TCP localport=3842
```

## Admin Dashboard

- Login at http://144.31.48.238:3842/
- Default password: `admin` (change this!)
- Create keys with custom duration
- Monitor who's online
- Revoke/delete keys instantly
- View full license history

## Security Notes

- Change the default admin password immediately
- The shared secret in `server.py` must match the one in `launcher.py`
- Both are set during the build process via `build_exe.bat`
- The database file `licenses.db` is created automatically
- Back up `licenses.db` regularly to preserve license data
