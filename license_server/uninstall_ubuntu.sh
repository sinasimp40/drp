#!/usr/bin/env bash
set -e
SERVICE_NAME="license-server"

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Run as root: sudo bash uninstall_ubuntu.sh"
    exit 1
fi

echo "Stopping and removing $SERVICE_NAME..."
systemctl stop $SERVICE_NAME 2>/dev/null || true
systemctl disable $SERVICE_NAME 2>/dev/null || true
rm -f /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload

echo "Service removed. Database, builds, venv, and logs are kept."
echo "To delete data manually:"
echo "  rm -rf $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/{venv,licenses.db,builds}"
echo "  rm -f /var/log/${SERVICE_NAME}.log"
