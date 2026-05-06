import argparse
import json
import time
from urllib import request as urllib_request

from chessboard_app.dpad import QWIIC_DPAD, decode_buttons, key_for_button


def open_bus(bus_number):
    try:
        from smbus2 import SMBus
    except ImportError:
        from smbus import SMBus  # type: ignore
    return SMBus(bus_number)


def create_keyboard():
    from evdev import UInput, ecodes

    capabilities = {
        ecodes.EV_KEY: [
            ecodes.KEY_UP,
            ecodes.KEY_DOWN,
            ecodes.KEY_LEFT,
            ecodes.KEY_RIGHT,
            ecodes.KEY_ENTER,
        ]
    }
    return UInput(capabilities, name="chessboard-dpad")


def read_registers(bus, mapping):
    registers = {}
    address = mapping["address"]
    for info in mapping["buttons"].values():
        register = info["register"]
        if register not in registers:
            registers[register] = bus.read_byte_data(address, register)
    return registers


def emit_key(ui, key_name):
    from evdev import ecodes

    code = getattr(ecodes, key_name)
    ui.write(ecodes.EV_KEY, code, 1)
    ui.syn()
    ui.write(ecodes.EV_KEY, code, 0)
    ui.syn()


def post_command(url, command):
    data = json.dumps({"command": command}).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    urllib_request.urlopen(req, timeout=1).read()


def main():
    parser = argparse.ArgumentParser(description="Turn the calibrated d-pad into keyboard navigation.")
    parser.add_argument("--bus", type=int, default=1)
    parser.add_argument("--poll-delay", type=float, default=0.05)
    parser.add_argument("--repeat-delay", type=float, default=0.25)
    parser.add_argument("--debug", action="store_true", help="Print register reads and detected buttons.")
    parser.add_argument("--mode", choices=["http", "keyboard"], default="http")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/input")
    args = parser.parse_args()

    last_pressed = set()
    last_emit = {}

    keyboard = create_keyboard() if args.mode == "keyboard" else None
    try:
        with open_bus(args.bus) as bus:
            print(f"D-pad bridge running in {args.mode} mode.")
            while True:
                registers = read_registers(bus, QWIIC_DPAD)
                pressed = decode_buttons(registers)
                if args.debug:
                    register_text = " ".join(f"0x{register:02X}=0b{value:08b}" for register, value in sorted(registers.items()))
                    print(f"{register_text} pressed={sorted(pressed)}", flush=True)
                now = time.monotonic()
                for button in sorted(pressed):
                    elapsed = now - last_emit.get(button, 0)
                    if button not in last_pressed or elapsed >= args.repeat_delay:
                        if args.debug:
                            print(f"emit {button}", flush=True)
                        if args.mode == "keyboard":
                            emit_key(keyboard, key_for_button(button))
                        else:
                            try:
                                post_command(args.url, button)
                            except Exception as exc:
                                if args.debug:
                                    print(f"post failed: {exc}", flush=True)
                        last_emit[button] = now
                last_pressed = pressed
                time.sleep(args.poll_delay)
    finally:
        if keyboard is not None:
            keyboard.close()


if __name__ == "__main__":
    main()
