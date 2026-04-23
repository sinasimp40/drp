@echo off
setlocal enabledelayedexpansion
set "X=admin"
set "LICENSE_ADMIN_PASSWORD=!X!"
set "LICENSE_SHARED_SECRET=!X!"
set "BUNDLE_AUTOMATION_TOKEN=!X!"
set "LICENSE_PORT=3842"
python server.py
