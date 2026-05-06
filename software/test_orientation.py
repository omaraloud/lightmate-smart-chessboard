import unittest

import chess

from chessboard_app.orientation import orient_occupancy, rotate_square_180


class OrientationTest(unittest.TestCase):
    def test_rotates_square_180_degrees(self):
        self.assertEqual(rotate_square_180("h1"), "a8")
        self.assertEqual(rotate_square_180("a8"), "h1")
        self.assertEqual(rotate_square_180("a1"), "h8")
        self.assertEqual(rotate_square_180("e2"), "d7")

        for square in chess.SQUARE_NAMES:
            self.assertEqual(rotate_square_180(rotate_square_180(square)), square)

    def test_black_orientation_maps_physical_h1_to_logical_a8(self):
        raw = {square: False for square in chess.SQUARE_NAMES}
        raw["h1"] = True

        oriented = orient_occupancy(raw, "black")

        self.assertTrue(oriented["a8"])
        self.assertFalse(oriented["h1"])

    def test_white_orientation_keeps_physical_square_names(self):
        raw = {square: False for square in chess.SQUARE_NAMES}
        raw["h1"] = True

        oriented = orient_occupancy(raw, "white")

        self.assertTrue(oriented["h1"])
        self.assertFalse(oriented["a8"])


if __name__ == "__main__":
    unittest.main()
