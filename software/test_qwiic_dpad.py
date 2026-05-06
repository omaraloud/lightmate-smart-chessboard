import unittest

from calibrate_qwiic_dpad import changed_registers, first_changed_bit


class QwiicDpadCalibrationTest(unittest.TestCase):
    def test_changed_registers_reports_only_differences(self):
        before = {0: 0xFF, 1: 0x00, 2: 0xAA}
        after = {0: 0xFE, 1: 0x00, 2: 0xAB}

        self.assertEqual(changed_registers(before, after), {0: (0xFF, 0xFE), 2: (0xAA, 0xAB)})

    def test_first_changed_bit_returns_register_bit_and_direction(self):
        self.assertEqual(first_changed_bit({3: (0xFF, 0xFB)}), (3, 2, "cleared"))
        self.assertEqual(first_changed_bit({3: (0xFB, 0xFF)}), (3, 2, "set"))


if __name__ == "__main__":
    unittest.main()
