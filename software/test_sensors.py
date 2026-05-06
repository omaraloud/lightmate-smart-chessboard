import unittest

import chess

from chessboard_app.sensors import SensorSnapshot, StaticSensorReader, UnavailableSensorReader, diff_occupancy, expected_occupancy_from_board


class SensorsTest(unittest.TestCase):
    def test_expected_occupancy_from_starting_board(self):
        occupancy = expected_occupancy_from_board(chess.Board())

        self.assertTrue(occupancy["a1"])
        self.assertTrue(occupancy["e8"])
        self.assertFalse(occupancy["e4"])
        self.assertEqual(sum(occupancy.values()), 32)

    def test_sensor_snapshot_requires_all_64_squares(self):
        with self.assertRaises(ValueError):
            SensorSnapshot({"a1": True})

    def test_diff_occupancy_reports_missing_and_extra_pieces(self):
        expected = {square: False for square in chess.SQUARE_NAMES}
        actual = dict(expected)
        expected["e2"] = True
        actual["e4"] = True

        diff = diff_occupancy(expected, actual)

        self.assertEqual(diff["missing"], ["e2"])
        self.assertEqual(diff["extra"], ["e4"])
        self.assertFalse(diff["matches"])

    def test_static_sensor_reader_details_include_chip_pin_mapping(self):
        details = StaticSensorReader().details()

        self.assertEqual(details["a8"]["chip"], "U69")
        self.assertEqual(details["a8"]["pin"], 7)
        self.assertEqual(details["a8"]["active"], False)

    def test_unavailable_sensor_reader_reports_error_and_empty_board(self):
        reader = UnavailableSensorReader("No I2C device at address: 0x20")

        self.assertEqual(sum(reader.read().as_dict().values()), 0)
        self.assertEqual(reader.status(), "unavailable")
        self.assertIn("0x20", reader.error)
        self.assertEqual(reader.details()["a8"]["error"], "No I2C device at address: 0x20")


if __name__ == "__main__":
    unittest.main()
