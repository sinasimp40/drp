@echo off
title Roblox Portable - Folder Setup
color 0A

echo ============================================
echo   ROBLOX PORTABLE LAUNCHER - SETUP
echo ============================================
echo.
echo This script will create the portable folder structure.
echo.

set PORTABLE_DIR=%~dp0RobloxPortable

echo [1/3] Creating portable folder structure...
if not exist "%PORTABLE_DIR%" mkdir "%PORTABLE_DIR%"
if not exist "%PORTABLE_DIR%\RobloxFiles" mkdir "%PORTABLE_DIR%\RobloxFiles"
if not exist "%PORTABLE_DIR%\Logs" mkdir "%PORTABLE_DIR%\Logs"
if not exist "%PORTABLE_DIR%\Cache" mkdir "%PORTABLE_DIR%\Cache"

echo [2/3] Creating placeholder files...

echo This folder should contain your Roblox installation files. > "%PORTABLE_DIR%\RobloxFiles\PLACE_ROBLOX_HERE.txt"
echo. >> "%PORTABLE_DIR%\RobloxFiles\PLACE_ROBLOX_HERE.txt"
echo Copy the following from your Roblox installation: >> "%PORTABLE_DIR%\RobloxFiles\PLACE_ROBLOX_HERE.txt"
echo - RobloxPlayerBeta.exe (the main Roblox player) >> "%PORTABLE_DIR%\RobloxFiles\PLACE_ROBLOX_HERE.txt"
echo - All DLL files from the Roblox folder >> "%PORTABLE_DIR%\RobloxFiles\PLACE_ROBLOX_HERE.txt"
echo - All other files in the Roblox program folder >> "%PORTABLE_DIR%\RobloxFiles\PLACE_ROBLOX_HERE.txt"
echo. >> "%PORTABLE_DIR%\RobloxFiles\PLACE_ROBLOX_HERE.txt"
echo Default Roblox location: >> "%PORTABLE_DIR%\RobloxFiles\PLACE_ROBLOX_HERE.txt"
echo %%LOCALAPPDATA%%\Roblox\Versions\[version-hash]\ >> "%PORTABLE_DIR%\RobloxFiles\PLACE_ROBLOX_HERE.txt"

echo [3/3] Copying launcher script...
copy "%~dp0launcher.bat" "%PORTABLE_DIR%\Launch Roblox.bat" >nul 2>&1

echo.
echo ============================================
echo   SETUP COMPLETE!
echo ============================================
echo.
echo Portable folder created at:
echo %PORTABLE_DIR%
echo.
echo NEXT STEPS:
echo 1. Go to: %PORTABLE_DIR%\RobloxFiles\
echo 2. Copy ALL files from your Roblox installation there
echo    (usually in %%LOCALAPPDATA%%\Roblox\Versions\[hash]\)
echo 3. Run "Launch Roblox.bat" to start Roblox portably!
echo.
pause
