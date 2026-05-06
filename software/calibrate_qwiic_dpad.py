import argparse
import time


BUTTONS = ["up", "down", "left", "right", "select"]
DEFAULT_BUS = 1


def changed_registers(before, after):
    return {
        register: (before[register], after[register])
        for register in sorted(before)
        if register in after and before[register] != after[register]
    }


def first_changed_bit(changes):
    for register, (before, after) in sorted(changes.items()):
        changed = before ^ after
        for bit in range(8):
            if changed & (1 << bit):
                direction = "set" if after & (1 << bit) else "cleared"
                return register, bit, direction
    return None


def open_bus(bus_number):
    try:
        from smbus2 import SMBus
    except ImportError:
        from smbus import SMBus  # type: ignore
    return SMBus(bus_number)


def scan_addresses(bus):
    found = []
    for address in range(0x03, 0x78):
        try:
            bus.read_byte(address)
        except OSError:
            continue
        found.append(address)
    return found


def read_register(bus, address, register):
    try:
        return bus.read_byte_data(address, register)
    except OSError:
        return None


def dump_registers(bus, address, registers):
    values = {}
    for register in registers:
        value = read_register(bus, address, register)
        if value is not None:
            values[register] = value
    return values


def stable_dump(bus, address, registers, samples, delay):
    snapshots = []
    for _ in range(samples):
        snapshots.append(dump_registers(bus, address, registers))
        time.sleep(delay)
    if not snapshots:
        return {}

    stable = {}
    common_registers = set(snapshots[0])
    for snapshot in snapshots[1:]:
        common_registers &= set(snapshot)
    for register in common_registers:
        values = {snapshot[register] for snapshot in snapshots}
        if len(values) == 1:
            stable[register] = values.pop()
    return stable


def print_addresses(addresses):
    if not addresses:
        print("No I2C devices found.")
        return
    print("I2C devices found:")
    for address in addresses:
        print(f"  0x{address:02X}")


def choose_address(addresses, requested):
    if requested is not None:
        return requested
    if len(addresses) == 1:
        return addresses[0]

    print()
    print("Enter the Qwiic directional pad I2C address.")
    print("Tip: your MCP23017 sensors are likely 0x20, 0x22, 0x24, 0x26, so choose the other address.")
    while True:
        raw = input("Address hex, for example 0x3F: ").strip()
        try:
            return int(raw, 16)
        except ValueError:
            print("Invalid address.")


def calibrate_button(bus, address, registers, button):
    print()
    input(f"Release all buttons, then press Enter to capture baseline for {button}.")
    baseline = stable_dump(bus, address, registers, samples=3, delay=0.03)

    print(f"Hold {button.upper()} now. Keep holding until it records.")
    while True:
        current = stable_dump(bus, address, registers, samples=2, delay=0.03)
        changes = changed_registers(baseline, current)
        changed_bit = first_changed_bit(changes)
        if changed_bit:
            register, bit, direction = changed_bit
            print(f"{button} -> register 0x{register:02X}, bit {bit}, {direction}")
            input("Release the button, then press Enter.")
            return {
                "register": register,
                "bit": bit,
                "active": direction,
            }
        time.sleep(0.05)


def print_mapping(address, mapping):
    print()
    print("Paste this into your config/code:")
    print("QWIIC_DPAD = {")
    print(f'    "address": 0x{address:02X},')
    print('    "buttons": {')
    for button in BUTTONS:
        item = mapping[button]
        print(
            f'        "{button}": {{"register": 0x{item["register"]:02X}, '
            f'"bit": {item["bit"]}, "active": "{item["active"]}"}},'
        )
    print("    },")
    print("}")


def main():
    parser = argparse.ArgumentParser(description="Calibrate SparkFun Qwiic Directional Pad button registers.")
    parser.add_argument("--bus", type=int, default=DEFAULT_BUS, help="I2C bus number. Raspberry Pi default is 1.")
    parser.add_argument("--address", type=lambda value: int(value, 16), help="I2C address, for example 0x3F.")
    parser.add_argument(
        "--registers",
        default="0x00-0x0F",
        help="Register range to watch, for example 0x00-0x0F or 0x00-0xFF.",
    )
    args = parser.parse_args()

    start_raw, end_raw = args.registers.split("-", 1)
    registers = range(int(start_raw, 16), int(end_raw, 16) + 1)

    with open_bus(args.bus) as bus:
        addresses = scan_addresses(bus)
        print_addresses(addresses)
        address = choose_address(addresses, args.address)
        print(f"Using I2C address 0x{address:02X}")

        mapping = {}
        for button in BUTTONS:
            mapping[button] = calibrate_button(bus, address, registers, button)

    print_mapping(address, mapping)


if __name__ == "__main__":
    main()
