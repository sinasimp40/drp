@echo off
title DENFI ROBLOX - Build
color 06

echo.
echo   =============================================
echo        DENFI ROBLOX PORTABLE - BUILD
echo   =============================================
echo.

echo [1/5] Checking Python...
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

echo [2/5] Installing dependencies...
pip install PyQt5 Pillow pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

echo [3/5] Setting Roblox files path...
echo.
echo   Where are your Roblox files located?
echo.
echo   Example: C:\Users\YourName\Desktop\RobloxFiles
echo   This folder should contain RobloxPlayerBeta.exe
echo.
set /p ROBLOX_PATH="   Enter full path: "

if "%ROBLOX_PATH%"=="" (
    echo [ERROR] No path entered!
    pause
    exit /b 1
)

echo.
echo   Path set to: %ROBLOX_PATH%
echo.

python build_config.py "%ROBLOX_PATH%"
if errorlevel 1 (
    echo [ERROR] Failed to save path.
    pause
    exit /b 1
)
echo [OK] Path saved into launcher.
echo.

echo [4/5] Checking for icon...
echo.
echo   Supported image formats:
echo   .ico .png .jpg .jpeg .bmp .webp .tiff .gif
echo.

if exist "icon.ico" (
    echo [OK] icon.ico found - using it directly
) else (
    echo [*] No icon.ico found - checking for other images...
    python convert_icon.py
)
echo.

echo [5/5] Building DenfiRoblox.exe ...
echo.

set ADDDATA=
if exist "splash_logo.png" set ADDDATA=--add-data "splash_logo.png;."

if exist "icon.ico" (
    echo [*] Building with custom icon
    pyinstaller --onefile --windowed --name "DenfiRoblox" --icon=icon.ico --add-data "icon.ico;." %ADDDATA% launcher.py
) else (
    echo [*] Building without icon
    pyinstaller --onefile --windowed --name "DenfiRoblox" %ADDDATA% launcher.py
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
echo   Roblox path: %ROBLOX_PATH%
echo.
echo   The .exe will NOT ask for any path.
echo   It goes straight to: splash - sync - launch - close
echo.
echo   To change the path, just run this build script again.
echo.
pause
