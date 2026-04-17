#!/usr/bin/env bash
set -e

SERVICE_NAME="license-server"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_USER="${SUDO_USER:-$(whoami)}"

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Run as root: sudo bash install_ubuntu.sh"
    exit 1
fi

echo "=========================================="
echo " Denfi License Server installer (Ubuntu)"
echo "=========================================="
echo ""

read -rp "Port to run on [3842]: " INPUT_PORT
PORT="${INPUT_PORT:-${PORT:-3842}}"

read -rp "Admin password [admin]: " INPUT_PASS
ADMIN_PASSWORD="${INPUT_PASS:-${LICENSE_ADMIN_PASSWORD:-admin}}"

read -rp "Shared license secret [DENFI_LICENSE_SECRET_KEY_2024]: " INPUT_SECRET
LICENSE_SECRET="${INPUT_SECRET:-${LICENSE_SHARED_SECRET:-DENFI_LICENSE_SECRET_KEY_2024}}"

echo ""
echo "------------------------------------------"
echo " Install dir : $SCRIPT_DIR"
echo " Run as user : $SERVICE_USER"
echo " Port        : $PORT"
echo " Admin pass  : $ADMIN_PASSWORD"
echo " Shared key  : $LICENSE_SECRET"
echo "------------------------------------------"
read -rp "Continue with install? [Y/n]: " CONFIRM
case "${CONFIRM:-Y}" in
    [yY]|[yY][eE][sS]) ;;
    *) echo "Aborted."; exit 1 ;;
esac

echo "[1/6] Updating apt and installing system packages..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv ufw

echo "[2/6] Creating Python virtual environment..."
cd "$SCRIPT_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
chown -R "$SERVICE_USER":"$SERVICE_USER" venv

echo "[3/6] Installing Python requirements..."
sudo -u "$SERVICE_USER" ./venv/bin/pip install --upgrade pip
sudo -u "$SERVICE_USER" ./venv/bin/pip install -r requirements.txt
sudo -u "$SERVICE_USER" ./venv/bin/pip install eventlet gunicorn

echo "[4/6] Opening firewall port $PORT (ufw)..."
ufw allow "$PORT"/tcp || true

echo "[5/6] Creating systemd service: $SERVICE_NAME"
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Denfi License Server (Flask)
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$SCRIPT_DIR
Environment=PORT=$PORT
Environment=LICENSE_ADMIN_PASSWORD=$ADMIN_PASSWORD
Environment=LICENSE_SHARED_SECRET=$LICENSE_SECRET
Environment=PYTHONUNBUFFERED=1
ExecStart=$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/server.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/${SERVICE_NAME}.log
StandardError=append:/var/log/${SERVICE_NAME}.log

[Install]
WantedBy=multi-user.target
EOF

touch /var/log/${SERVICE_NAME}.log
chown "$SERVICE_USER":"$SERVICE_USER" /var/log/${SERVICE_NAME}.log

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo "[6/6] Done. Waiting 3s and checking status..."
sleep 3
systemctl --no-pager status ${SERVICE_NAME} || true

PUBLIC_IP="$(curl -s --max-time 3 ifconfig.me || echo 'YOUR_SERVER_IP')"

echo ""
echo "=========================================="
echo " Install complete."
echo "=========================================="
echo " URL         : http://${PUBLIC_IP}:${PORT}/"
echo " Admin login : admin / $ADMIN_PASSWORD"
echo ""
echo " Useful commands:"
echo "   sudo systemctl status  $SERVICE_NAME"
echo "   sudo systemctl restart $SERVICE_NAME"
echo "   sudo systemctl stop    $SERVICE_NAME"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo "   tail -f /var/log/${SERVICE_NAME}.log"
echo ""
echo " To change admin password / secret, edit:"
echo "   /etc/systemd/system/${SERVICE_NAME}.service"
echo " then: sudo systemctl daemon-reload && sudo systemctl restart $SERVICE_NAME"
echo "=========================================="
