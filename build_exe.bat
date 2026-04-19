@echo off
title Roblox Launcher - Build
color 06

echo.
echo   =============================================
echo        ROBLOX PORTABLE LAUNCHER - BUILD
echo   =============================================
echo.

echo [*] Cleaning previous build files...
if exist "build" rmdir /s /q "build" >nul 2>&1
if exist "dist" rmdir /s /q "dist" >nul 2>&1
if exist "*.spec" del /f /q *.spec >nul 2>&1
echo [OK] Clean slate.
echo.

echo [1/8] Checking Python...
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

echo [2/8] Installing dependencies...
pip install PyQt5 Pillow pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

echo [3/8] Setting launcher name...
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

echo [4/8] Setting Roblox files path...
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

echo [5/8] Setting license server...
echo.
echo   Enter the license server URL for online validation.
echo   Leave blank to disable license checking.
echo.
echo   Example: http://144.31.48.238:3842
echo.
set /p LICENSE_URL="   Enter license server URL (or press Enter to skip): "

if "%LICENSE_URL%"=="" (
    echo   [*] License checking disabled
    set LICENSE_URL=
    set LICENSE_SECRET=
    goto skip_secret
) else (
    echo   License server: %LICENSE_URL%
)
echo.

echo [6/8] Setting license secret...
echo.
echo   Enter the shared secret for license authentication.
echo   This MUST match the secret on your license server.
echo   Default: DENFI_LICENSE_SECRET_KEY_2024
echo.
set /p LICENSE_SECRET="   Enter shared secret (or press Enter for default): "

if "%LICENSE_SECRET%"=="" (
    set LICENSE_SECRET=DENFI_LICENSE_SECRET_KEY_2024
    echo   [*] Using default secret
) else (
    echo   [*] Custom secret set
)
echo.

:skip_secret

python build_config.py "%ROBLOX_PATH%" "%APP_NAME_INPUT%" "%LICENSE_URL%" "%LICENSE_SECRET%" > _build_output.tmp 2>&1
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

echo [7/8] Checking for icon...
echo.
echo   Supported image formats:
echo   .ico .png .jpg .jpeg .bmp .webp .tiff .gif
echo.

echo [*] Converting icon from source image...
python convert_icon.py
echo.

echo [8/8] Building %EXE_NAME%.exe ...
echo.

set ADDDATA=
if exist "splash_logo.png" set ADDDATA=--add-data "splash_logo.png;."
if exist "Roblox2017.ttf" set ADDDATA=%ADDDATA% --add-data "Roblox2017.ttf;."

if exist "icon.ico" (
    echo [*] Building with custom icon
    pyinstaller --onefile --windowed --clean --name "%EXE_NAME%" --icon=icon.ico --add-data "icon.ico;." %ADDDATA% launcher.py
) else (
    echo [*] Building without icon
    pyinstaller --onefile --windowed --clean --name "%EXE_NAME%" %ADDDATA% launcher.py
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
if not "%LICENSE_URL%"=="" echo   License server: %LICENSE_URL%
echo.
echo   The .exe will NOT ask for any path or name.
echo   It goes straight to: splash - sync - launch
echo.
echo   To change settings, just run this build script again.
echo.
pause
