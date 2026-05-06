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

KEY_BY_BUTTON = {
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
    "select": "KEY_ENTER",
}


def decode_buttons(registers, mapping=QWIIC_DPAD):
    pressed = set()
    for button, info in mapping["buttons"].items():
        value = registers.get(info["register"])
        if value is None:
            continue
        bit_is_set = bool(value & (1 << info["bit"]))
        if info["active"] == "cleared" and not bit_is_set:
            pressed.add(button)
        elif info["active"] == "set" and bit_is_set:
            pressed.add(button)
    return pressed


def key_for_button(button):
    return KEY_BY_BUTTON[button]
