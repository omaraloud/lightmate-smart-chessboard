import unittest

from chessboard_app.dpad import QWIIC_DPAD, decode_buttons, key_for_button


class DpadTest(unittest.TestCase):
    def test_mapping_matches_calibrated_values(self):
        self.assertEqual(QWIIC_DPAD["address"], 0x20)
        self.assertEqual(QWIIC_DPAD["buttons"]["up"], {"register": 0x00, "bit": 0, "active": "cleared"})
        self.assertEqual(QWIIC_DPAD["buttons"]["select"], {"register": 0x00, "bit": 4, "active": "cleared"})

    def test_decode_buttons_for_active_low_bits(self):
        registers = {0x00: 0b11101110}

        pressed = decode_buttons(registers)

        self.assertEqual(pressed, {"up", "select"})

    def test_button_to_keyboard_mapping(self):
        self.assertEqual(key_for_button("up"), "KEY_UP")
        self.assertEqual(key_for_button("down"), "KEY_DOWN")
        self.assertEqual(key_for_button("left"), "KEY_LEFT")
        self.assertEqual(key_for_button("right"), "KEY_RIGHT")
        self.assertEqual(key_for_button("select"), "KEY_ENTER")


if __name__ == "__main__":
    unittest.main()
