CHIP_ADDRESSES = {
    "U66": 0x20,
    "U67": 0x24,
    "U68": 0x22,
    "U69": 0x26,
}

PIN_COUNT_PER_CHIP = 16


def square_names():
    """Return chess squares in physical calibration order: a8 to h1."""
    return [
        f"{file_name}{rank}"
        for rank in range(8, 0, -1)
        for file_name in "abcdefgh"
    ]


def validate_sensor_map(sensor_map):
    expected_squares = set(square_names())
    actual_squares = set(sensor_map)
    if actual_squares != expected_squares:
        missing = sorted(expected_squares - actual_squares)
        extra = sorted(actual_squares - expected_squares)
        raise ValueError(f"sensor map squares are incomplete: missing={missing}, extra={extra}")

    used = set()
    for square, chip_pin in sensor_map.items():
        chip, pin = chip_pin
        if chip not in CHIP_ADDRESSES:
            raise ValueError(f"{square} uses unknown chip {chip!r}")
        if not isinstance(pin, int) or not 0 <= pin < PIN_COUNT_PER_CHIP:
            raise ValueError(f"{square} uses invalid pin {pin!r}")
        if chip_pin in used:
            raise ValueError(f"duplicate sensor chip/pin assignment: {chip_pin!r}")
        used.add(chip_pin)


SENSOR_MAP = {
    "a8": ("U69", 7),
    "b8": ("U69", 6),
    "c8": ("U69", 5),
    "d8": ("U69", 4),
    "e8": ("U69", 3),
    "f8": ("U69", 2),
    "g8": ("U69", 1),
    "h8": ("U69", 0),
    "a7": ("U69", 8),
    "b7": ("U69", 9),
    "c7": ("U69", 10),
    "d7": ("U69", 11),
    "e7": ("U69", 12),
    "f7": ("U69", 13),
    "g7": ("U69", 14),
    "h7": ("U69", 15),
    "a6": ("U68", 7),
    "b6": ("U68", 6),
    "c6": ("U68", 5),
    "d6": ("U68", 4),
    "e6": ("U68", 3),
    "f6": ("U68", 2),
    "g6": ("U68", 1),
    "h6": ("U68", 0),
    "a5": ("U68", 8),
    "b5": ("U68", 9),
    "c5": ("U68", 10),
    "d5": ("U68", 11),
    "e5": ("U68", 12),
    "f5": ("U68", 13),
    "g5": ("U68", 14),
    "h5": ("U68", 15),
    "a4": ("U67", 7),
    "b4": ("U67", 6),
    "c4": ("U67", 5),
    "d4": ("U67", 4),
    "e4": ("U67", 3),
    "f4": ("U67", 2),
    "g4": ("U67", 1),
    "h4": ("U67", 0),
    "a3": ("U67", 8),
    "b3": ("U67", 9),
    "c3": ("U67", 10),
    "d3": ("U67", 11),
    "e3": ("U67", 12),
    "f3": ("U67", 13),
    "g3": ("U67", 14),
    "h3": ("U67", 15),
    "a2": ("U66", 7),
    "b2": ("U66", 6),
    "c2": ("U66", 5),
    "d2": ("U66", 4),
    "e2": ("U66", 3),
    "f2": ("U66", 2),
    "g2": ("U66", 1),
    "h2": ("U66", 0),
    "a1": ("U66", 8),
    "b1": ("U66", 9),
    "c1": ("U66", 10),
    "d1": ("U66", 11),
    "e1": ("U66", 12),
    "f1": ("U66", 13),
    "g1": ("U66", 14),
    "h1": ("U66", 15),
}

validate_sensor_map(SENSOR_MAP)
