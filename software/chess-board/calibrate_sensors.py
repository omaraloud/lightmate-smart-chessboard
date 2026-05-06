import argparse
import os
import sys
import time

from sensor_mapping import CHIP_ADDRESSES, PIN_COUNT_PER_CHIP, square_names


def import_circuitpython_board():
    """Avoid importing this repo's board.py when we need CircuitPython's board module."""
    here = os.path.abspath(os.path.dirname(__file__))
    cwd = os.path.abspath(os.getcwd())
    sys.path = [
        path
        for path in sys.path
        if os.path.abspath(path or cwd) != here
    ]
    import board  # type: ignore

    return board


def setup_pins():
    circuit_board = import_circuitpython_board()
    import busio  # type: ignore
    import digitalio  # type: ignore
    from adafruit_mcp230xx.mcp23017 import MCP23017  # type: ignore

    i2c = busio.I2C(circuit_board.SCL, circuit_board.SDA)
    pins = {}
    for chip, address in CHIP_ADDRESSES.items():
        mcp = MCP23017(i2c, address=address)
        for pin_num in range(PIN_COUNT_PER_CHIP):
            pin = mcp.get_pin(pin_num)
            pin.direction = digitalio.Direction.INPUT
            pin.pull = digitalio.Pull.UP
            pins[(chip, pin_num)] = pin
    return pins


def read_active_sensors(pins):
    return {
        chip_pin
        for chip_pin, pin in pins.items()
        if pin.value is False
    }


def single_added_sensor(baseline, active):
    added = active - baseline
    removed = baseline - active
    if len(added) == 1 and not removed:
        return next(iter(added))
    return None


def print_python_map(assignments):
    print()
    print("Paste this into sensor_mapping.py as SENSOR_MAP:")
    print("SENSOR_MAP = {")
    for square in square_names():
        chip, pin = assignments[square]
        print(f'    "{square}": ("{chip}", {pin}),')
    print("}")


def wait_for_no_active_sensors(pins, poll_delay):
    while True:
        time.sleep(poll_delay)
        active = read_active_sensors(pins)
        if not active:
            return
        print(f"Still active: {sorted(active)}. Remove all magnets/pieces.")


def wait_for_single_added_sensor(pins, baseline, poll_delay):
    while True:
        time.sleep(poll_delay)
        active = read_active_sensors(pins)
        chip_pin = single_added_sensor(baseline, active)
        if chip_pin is not None:
            return chip_pin

        added = sorted(active - baseline)
        removed = sorted(baseline - active)
        if removed:
            print(f"Detected removal {removed}; place a magnet on the prompted square.")
        elif len(added) > 1:
            print(f"Multiple sensors became active: {added}. Remove extras and try again.")


def main():
    parser = argparse.ArgumentParser(
        description="Calibrate 64 active-low MCP23017 chessboard sensors."
    )
    parser.add_argument(
        "--poll-delay",
        type=float,
        default=0.05,
        help="Seconds between sensor reads.",
    )
    args = parser.parse_args()

    pins = setup_pins()
    assignments = {}

    print("MCP23017 sensor calibration")
    print("For each prompted square:")
    print("1. Make sure the board is empty.")
    print("2. Place one magnet/piece on that square only.")
    print("3. Remove it when asked.")
    input("Press Enter when the board is empty.")
    wait_for_no_active_sensors(pins, args.poll_delay)

    try:
        for square in square_names():
            print()
            print(f"{square}: place one magnet/piece on this square now...")
            chip_pin = wait_for_single_added_sensor(pins, set(), args.poll_delay)
            assignments[square] = chip_pin
            print(f"{square} -> {chip_pin[0]} pin {chip_pin[1]}")

            print("Remove the magnet/piece.")
            wait_for_no_active_sensors(pins, args.poll_delay)
            input("Press Enter for the next square.")

        print_python_map(assignments)
    except KeyboardInterrupt:
        print()
        print("Stopped early.")
        if assignments:
            print_python_map(assignments)


if __name__ == "__main__":
    main()
