#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

.venv/bin/python3 -m pip install -r requirements.txt

sudo cp deploy/systemd/chessboard-hotspot.service /etc/systemd/system/chessboard-hotspot.service
sudo cp deploy/systemd/chessboard.service /etc/systemd/system/chessboard.service
sudo cp deploy/systemd/chessboard-portal.service /etc/systemd/system/chessboard-portal.service
sudo cp deploy/systemd/chessboard-dpad.service /etc/systemd/system/chessboard-dpad.service
sudo cp deploy/systemd/chessboard-kiosk.service /etc/systemd/system/chessboard-kiosk.service
sudo mkdir -p /etc/NetworkManager/dnsmasq-shared.d
sudo cp deploy/networkmanager/chessboard-captive-portal.conf /etc/NetworkManager/dnsmasq-shared.d/chessboard-captive-portal.conf
sudo systemctl daemon-reload
sudo modprobe uinput || true
if ! grep -q '^uinput$' /etc/modules; then
  echo uinput | sudo tee -a /etc/modules >/dev/null
fi
sudo systemctl enable chessboard-hotspot.service chessboard.service chessboard-portal.service chessboard-dpad.service chessboard-kiosk.service
sudo systemctl reload NetworkManager || sudo systemctl restart NetworkManager || true
sudo systemctl restart chessboard-hotspot.service
sudo systemctl restart chessboard.service
sudo systemctl restart chessboard-portal.service
sudo systemctl restart chessboard-dpad.service
sudo systemctl restart chessboard-kiosk.service

echo "Chessboard services installed and restarted."
