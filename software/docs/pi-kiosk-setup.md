# Pi Kiosk Setup

This makes the Pi boot straight into the chessboard screen.

## Install Dependencies

From the Pi:

```bash
cd ~/Desktop/chess-board
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install Chromium if it is not already installed:

```bash
sudo apt update
sudo apt install -y chromium-browser
```

On newer Raspberry Pi OS images the package may be named:

```bash
sudo apt install -y chromium
```

If the executable is `/usr/bin/chromium` instead of `/usr/bin/chromium-browser`, edit `deploy/systemd/chessboard-kiosk.service`.

## Enable Boot To Screen

```bash
cd ~/Desktop/chess-board
chmod +x deploy/install_services.sh
./deploy/install_services.sh
```

Reboot test:

```bash
sudo reboot
```

The Pi should open Chromium directly to:

```text
http://127.0.0.1:8000
```

The screen uses a setup gate:

1. If Wi-Fi is missing, it shows only Wi-Fi setup.
2. If Wi-Fi works but Lichess is not connected, it shows only Lichess login.
3. After both are done, it shows the normal chessboard UI.

## First-Time Wi-Fi Setup

If the Pi has no saved Wi-Fi connection, it starts a setup hotspot.

Connect a phone or laptop to:

```text
SSID: ChessBoard-Setup
Password: chessboard
```

The Wi-Fi setup screen scans nearby Wi-Fi networks directly on the Pi. Select the network, type the password, then choose `Send Wi-Fi To Board`.

Then open:

```text
http://10.42.0.1:8000
```

NetworkManager saves the connection, so the Pi should reconnect after reboot.

## Lichess Token Setup

From the Home tab, scan the Lichess QR code or open:

```text
Connect Lichess from phone
```

This opens a Pi URL on the phone, redirects to Lichess, asks the user to approve `board:play`, and then redirects back to the Pi. The Pi saves the token automatically.

The manual token form remains as a fallback, but normal users should not need it.

The token is saved only on the Pi in the local config file. The browser UI never receives the stored token back.

## Starting Games

After Wi-Fi and Lichess are connected, open the Play tab.

Initial supported actions:

- Play Friend 3+2
- Play AI 3+2
- Random 3+2 seek
- Create friend link/open challenge
- Daily Puzzle
- Tactics/new puzzle

Lichess Board API restrictions still apply. For physical boards, Lichess supports rapid, classical, and correspondence normally. Blitz is allowed for direct challenges, AI games, and bulk pairing-style flows.

## Five Button Navigation

Map the physical buttons to keyboard events:

- Up button: `ArrowUp`
- Down button: `ArrowDown`
- Left button: `ArrowLeft`
- Right button: `ArrowRight`
- Select button: `Enter`

The web UI is built so these five inputs can move between tabs, move between controls, and activate the selected item.

## Useful Commands

Check backend logs:

```bash
journalctl -u chessboard.service -f
```

Check kiosk logs:

```bash
journalctl -u chessboard-kiosk.service -f
```

Stop kiosk temporarily:

```bash
sudo systemctl stop chessboard-kiosk.service
```

Disable kiosk boot:

```bash
sudo systemctl disable chessboard-kiosk.service
```

## Updating Code

After pulling new code on the Pi:

```bash
cd ~/Desktop/chess-board
git pull
./deploy/install_services.sh
```

If only Python files changed, rebooting or restarting `chessboard.service` is enough. If service files or dependencies changed, run the install script.
