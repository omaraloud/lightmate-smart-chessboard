import unittest

from sensor_mapping import square_names, validate_sensor_map


class SensorMappingTest(unittest.TestCase):
    def test_square_names_are_board_order_top_left_to_bottom_right(self):
        self.assertEqual(square_names(), [
            "a8", "b8", "c8", "d8", "e8", "f8", "g8", "h8",
            "a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7",
            "a6", "b6", "c6", "d6", "e6", "f6", "g6", "h6",
            "a5", "b5", "c5", "d5", "e5", "f5", "g5", "h5",
            "a4", "b4", "c4", "d4", "e4", "f4", "g4", "h4",
            "a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3",
            "a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2",
            "a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1",
        ])

    def test_validate_sensor_map_accepts_64_unique_chip_pin_pairs(self):
        sensor_map = {}
        squares = square_names()
        for chip in ("U66", "U67", "U68", "U69"):
            for pin in range(16):
                sensor_map[squares[len(sensor_map)]] = (chip, pin)

        validate_sensor_map(sensor_map)

    def test_validate_sensor_map_rejects_duplicate_chip_pin_pairs(self):
        sensor_map = {}
        squares = square_names()
        for chip in ("U66", "U67", "U68", "U69"):
            for pin in range(16):
                sensor_map[squares[len(sensor_map)]] = (chip, pin)
        sensor_map["h1"] = ("U66", 0)

        with self.assertRaises(ValueError):
            validate_sensor_map(sensor_map)


if __name__ == "__main__":
    unittest.main()
