# Denfi Roblox - Portable Launcher

## Overview
A desktop GUI application (Python/PyQt5) called "Denfi Roblox" that runs Roblox from a portable folder. No Roblox installation on the system needed — just put the files next to the launcher and click Launch.

## How It Works
The launcher automatically looks for a `RobloxFiles` folder sitting right next to the .exe:

```
SomeFolder\
  DenfiRoblox.exe        <- The launcher
  icon.ico               <- Your custom icon (optional)
  RobloxFiles\           <- Roblox files go here
    RobloxPlayerBeta.exe
    *.dll files
    (all other Roblox files)
  Cache\                 <- Auto-created, keeps Roblox data portable
  Logs\                  <- Auto-created, launch logs
```

When you click "Launch Roblox", it:
1. Runs RobloxPlayerBeta.exe from the RobloxFiles folder
2. Redirects Roblox's AppData to the Cache folder (so nothing gets installed on the PC)
3. Logs each launch to the Logs folder

## Files
- **launcher.py** — Main application (PyQt5 GUI)
- **build_exe.bat** — Windows script to compile into DenfiRoblox.exe
- **requirements.txt** — Python dependencies
- **icon.ico** — Place your custom .ico file here for the app icon

## Building the EXE on Windows
1. Install Python from python.org (check "Add to PATH")
2. Place icon.ico next to launcher.py (optional)
3. Run `build_exe.bat`
4. Get your `DenfiRoblox.exe` from the `dist\` folder

## Tech Stack
- Python 3.11, PyQt5, PyInstaller
