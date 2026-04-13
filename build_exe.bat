@echo off
title Building Roblox Portable Launcher EXE
color 0A

echo ============================================
echo   Building Roblox Portable Launcher .EXE
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

echo [2/3] Installing dependencies...
pip install PyQt5 pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.

echo [3/3] Building EXE...
pyinstaller --onefile --windowed --name "RobloxPortableLauncher" --icon=NONE launcher.py
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   BUILD COMPLETE!
echo ============================================
echo.
echo Your EXE is at: dist\RobloxPortableLauncher.exe
echo.
echo You can copy that file anywhere and run it!
echo.
pause
