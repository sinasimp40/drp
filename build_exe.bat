@echo off
title Roblox Launcher - Build
color 06

echo.
echo   =============================================
echo        ROBLOX PORTABLE LAUNCHER - BUILD
echo   =============================================
echo.

echo [1/6] Checking Python...
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

echo [2/6] Installing dependencies...
pip install PyQt5 Pillow pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

echo [3/6] Setting launcher name...
echo.
echo   What should the launcher be called?
echo.
echo   This will be shown on the splash screen
echo   and used as the .exe filename.
echo.
echo   Example: DENFI ROBLOX
echo   Example: MY LAUNCHER
echo   Example: PORTABLE RBLX
echo.
set /p APP_NAME_INPUT="   Enter launcher name: "

if "%APP_NAME_INPUT%"=="" (
    echo [ERROR] No name entered!
    pause
    exit /b 1
)

echo.
echo   Launcher name: %APP_NAME_INPUT%
echo.

echo [4/6] Setting Roblox files path...
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

python build_config.py "%ROBLOX_PATH%" "%APP_NAME_INPUT%" > _build_output.tmp 2>&1
if errorlevel 1 (
    type _build_output.tmp
    del _build_output.tmp >nul 2>&1
    echo [ERROR] Failed to save config.
    pause
    exit /b 1
)

for /f "tokens=2 delims==" %%a in ('findstr "EXE_NAME=" _build_output.tmp') do set EXE_NAME=%%a
type _build_output.tmp
del _build_output.tmp >nul 2>&1

if "%EXE_NAME%"=="" set EXE_NAME=DenfiRoblox

echo [OK] Config saved into launcher.
echo.

echo [5/6] Checking for icon...
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

echo [6/6] Building %EXE_NAME%.exe ...
echo.

set ADDDATA=
if exist "splash_logo.png" set ADDDATA=--add-data "splash_logo.png;."

if exist "icon.ico" (
    echo [*] Building with custom icon
    pyinstaller --onefile --windowed --name "%EXE_NAME%" --icon=icon.ico --add-data "icon.ico;." %ADDDATA% launcher.py
) else (
    echo [*] Building without icon
    pyinstaller --onefile --windowed --name "%EXE_NAME%" %ADDDATA% launcher.py
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
echo   Launcher name: %APP_NAME_INPUT%
echo   Your file:     dist\%EXE_NAME%.exe
echo   Roblox path:   %ROBLOX_PATH%
echo.
echo   The .exe will NOT ask for any path or name.
echo   It goes straight to: splash - sync - launch
echo.
echo   To change settings, just run this build script again.
echo.
pause
