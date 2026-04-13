@echo off
title DENFI ROBLOX - Build
color 06

echo.
echo   =============================================
echo        DENFI ROBLOX PORTABLE - BUILD
echo   =============================================
echo.

echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo.
    echo Download Python from https://python.org
    echo IMPORTANT: Check "Add Python to PATH" during install!
    echo.
    pause
    exit /b 1
)
echo [OK] Python found.
echo.

echo [2/3] Installing dependencies...
pip install PyQt5 pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

echo [3/3] Building DenfiRoblox.exe ...
echo.

if exist "icon.ico" (
    echo [*] Custom icon found - using icon.ico
    pyinstaller --onefile --windowed --name "DenfiRoblox" --icon=icon.ico --add-data "icon.ico;." launcher.py
) else (
    echo [*] No icon.ico found - building without custom icon
    echo [*] TIP: Place "icon.ico" next to this script and rebuild
    pyinstaller --onefile --windowed --name "DenfiRoblox" launcher.py
)

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo   =============================================
echo        BUILD COMPLETE!
echo   =============================================
echo.
echo   Your launcher: dist\DenfiRoblox.exe
echo.
echo   FIRST RUN:
echo   The launcher will ask you where to store
echo   your Roblox files (custom folder or same folder).
echo   After that, it remembers your choice.
echo.
echo   EVERY LAUNCH:
echo   1. Shows splash screen
echo   2. Auto-syncs if Roblox updated
echo   3. Launches Roblox
echo   4. Closes itself
echo.
pause
