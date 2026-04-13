@echo off
title Building Denfi Roblox Launcher
color 0A

echo ============================================
echo   DENFI ROBLOX - Building Launcher EXE
echo ============================================
echo.

echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please download Python from https://python.org
    echo Make sure to check "Add Python to PATH" during install.
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

echo [3/3] Building EXE...
echo.

REM Check if user has a custom icon
if exist "icon.ico" (
    echo [*] Custom icon found! Using icon.ico
    pyinstaller --onefile --windowed --name "DenfiRoblox" --icon=icon.ico --add-data "icon.ico;." launcher.py
) else (
    echo [*] No icon.ico found - building without custom icon
    echo [*] To add your icon: place an "icon.ico" file next to this script
    echo     and run this build again.
    pyinstaller --onefile --windowed --name "DenfiRoblox" launcher.py
)

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   BUILD COMPLETE!
echo ============================================
echo.
echo Your launcher is at: dist\DenfiRoblox.exe
echo.
echo HOW TO USE:
echo 1. Copy DenfiRoblox.exe to any folder
echo 2. Run it once - it creates a "RobloxFiles" folder
echo 3. Copy your Roblox files into RobloxFiles\
echo    (from %%LOCALAPPDATA%%\Roblox\Versions\[hash]\)
echo 4. Click "Launch Roblox" in the launcher!
echo.
echo CUSTOM ICON:
echo   Place "icon.ico" next to DenfiRoblox.exe
echo   The launcher will use it automatically.
echo.
pause
