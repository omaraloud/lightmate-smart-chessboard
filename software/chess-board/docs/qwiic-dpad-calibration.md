# Qwiic Directional Pad Calibration

SparkFun Qwiic Directional Pad is an I2C device. On Raspberry Pi, Qwiic normally uses:

- SDA: GPIO2
- SCL: GPIO3
- 3.3V
- GND

It does not use one GPIO per button unless you wire interrupt pins separately.

## Install Dependency

```bash
cd ~/Desktop/chess-board
source .venv/bin/activate
pip install -r requirements.txt
```

Make sure I2C is enabled:

```bash
sudo raspi-config
```

Then enable Interface Options > I2C.

## Run Calibration

```bash
python3 calibrate_qwiic_dpad.py
```

The script will:

1. Scan I2C bus 1.
2. Print all detected addresses.
3. Ask which address is the Qwiic directional pad.
4. Ask you to press:
   - up
   - down
   - left
   - right
   - select
5. Print a `QWIIC_DPAD` mapping.

Your MCP23017 sensor chips are likely:

```text
0x20
0x22
0x24
0x26
```

So the directional pad should usually be a different address.

If no button change is detected, try a larger register range:

```bash
python3 calibrate_qwiic_dpad.py --registers 0x00-0xFF
```

If you already know the address:

```bash
python3 calibrate_qwiic_dpad.py --address 0x3F
```

## Installed Mapping

The current installed mapping is:

```python
QWIIC_DPAD = {
    "address": 0x20,
    "buttons": {
        "up": {"register": 0x00, "bit": 0, "active": "cleared"},
        "down": {"register": 0x00, "bit": 1, "active": "cleared"},
        "left": {"register": 0x00, "bit": 3, "active": "cleared"},
        "right": {"register": 0x00, "bit": 2, "active": "cleared"},
        "select": {"register": 0x00, "bit": 4, "active": "cleared"},
    },
}
```

## Keyboard Bridge

The d-pad drives the kiosk browser by posting commands to the local web app:

```bash
sudo .venv/bin/python dpad_keyboard.py --mode http --url http://127.0.0.1:8000/api/input
```

Installed service:

```bash
sudo systemctl restart chessboard-dpad.service
journalctl -u chessboard-dpad.service -f
```

If you need to debug the raw button reads:

```bash
sudo .venv/bin/python dpad_keyboard.py --debug
```
