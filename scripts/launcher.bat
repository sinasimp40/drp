@echo off
title Roblox Portable Launcher
color 0B

echo ============================================
echo       ROBLOX PORTABLE LAUNCHER
echo ============================================
echo.

set SCRIPT_DIR=%~dp0
set ROBLOX_DIR=%SCRIPT_DIR%RobloxFiles
set LOG_DIR=%SCRIPT_DIR%Logs
set CACHE_DIR=%SCRIPT_DIR%Cache

if "%~1"=="" (
    set ROBLOX_FOLDER=%ROBLOX_DIR%
) else (
    set ROBLOX_FOLDER=%~1
)

echo [*] Looking for Roblox files in:
echo     %ROBLOX_FOLDER%
echo.

if not exist "%ROBLOX_FOLDER%" (
    echo [ERROR] Folder not found: %ROBLOX_FOLDER%
    echo.
    echo Please run SetupPortableFolder.bat first to create
    echo the folder structure, then copy your Roblox files.
    echo.
    pause
    exit /b 1
)

set ROBLOX_EXE=%ROBLOX_FOLDER%\RobloxPlayerBeta.exe

if not exist "%ROBLOX_EXE%" (
    echo [ERROR] RobloxPlayerBeta.exe not found in:
    echo     %ROBLOX_FOLDER%
    echo.
    echo Please copy your Roblox files to that folder.
    echo You can find them at:
    echo %%LOCALAPPDATA%%\Roblox\Versions\[version-hash]\
    echo.
    echo Files needed:
    echo  - RobloxPlayerBeta.exe
    echo  - All .dll files
    echo  - All other Roblox files
    echo.
    pause
    exit /b 1
)

echo [OK] Found Roblox at: %ROBLOX_EXE%
echo.

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"

set ROBLOX_APPDATA_ORIGINAL=%LOCALAPPDATA%\Roblox
set TIMESTAMP=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

echo [*] Redirecting Roblox data to portable cache...
echo [*] Cache folder: %CACHE_DIR%
echo.

set ROBLOX_APPDATA=%CACHE_DIR%\AppData
if not exist "%ROBLOX_APPDATA%" mkdir "%ROBLOX_APPDATA%"

echo [*] Launching Roblox...
echo [*] Time: %DATE% %TIME%
echo.

set "LOCALAPPDATA=%CACHE_DIR%\AppData"

start "" "%ROBLOX_EXE%" %*

echo.
echo [OK] Roblox launched successfully!
echo [*]  Log saved to: %LOG_DIR%\launch_%TIMESTAMP%.log
echo.

echo Launch Time: %DATE% %TIME% > "%LOG_DIR%\launch_%TIMESTAMP%.log"
echo Executable: %ROBLOX_EXE% >> "%LOG_DIR%\launch_%TIMESTAMP%.log"
echo Arguments: %* >> "%LOG_DIR%\launch_%TIMESTAMP%.log"

timeout /t 3 >nul
exit /b 0
