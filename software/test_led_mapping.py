import unittest

from led_mapping import LED_GRID, SQUARE_TO_LED, SQUARE_TO_LED_CORNERS


def physical_numbers(square):
    return tuple(led + 1 for led in SQUARE_TO_LED[square])


class LedMappingTest(unittest.TestCase):
    def test_led_grid_has_all_81_corner_leds(self):
        flattened = [led for row in LED_GRID for led in row]

        self.assertEqual(len(flattened), 81)
        self.assertEqual(sorted(flattened), list(range(81)))

    def test_verified_square_corner_leds_use_physical_numbering_pattern(self):
        self.assertEqual(physical_numbers("h1"), (1, 2, 17, 18))
        self.assertEqual(physical_numbers("a1"), (8, 9, 10, 11))
        self.assertEqual(physical_numbers("h2"), (17, 18, 26, 27))
        self.assertEqual(physical_numbers("g2"), (16, 17, 25, 26))
        self.assertEqual(physical_numbers("h8"), (71, 72, 80, 81))
        self.assertEqual(physical_numbers("a8"), (64, 65, 73, 74))

    def test_ordered_square_corners_follow_physical_circle(self):
        self.assertEqual(tuple(led + 1 for led in SQUARE_TO_LED_CORNERS["h8"]), (81, 80, 71, 72))
        self.assertEqual(tuple(led + 1 for led in SQUARE_TO_LED_CORNERS["h2"]), (27, 26, 17, 18))


if __name__ == "__main__":
    unittest.main()
