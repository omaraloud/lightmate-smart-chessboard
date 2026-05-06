import unittest

import chess

from chessboard_app.leds import (
    DotStarLedController,
    DisabledLedController,
    EXTRA_COLOR,
    LedSettings,
    MemoryLedController,
    SHARED_LED_COLOR,
    WARM_GLOW_COLOR,
)
from led_mapping import SQUARE_TO_LED, SQUARE_TO_LED_CORNERS


def marker_led(square):
    return min(SQUARE_TO_LED[square])


class FakePixels:
    def __init__(self, count=81):
        self.values = [(0, 0, 0)] * count
        self.show_count = 0
        self.brightness = 1

    def __setitem__(self, index, value):
        self.values[index] = value

    def fill(self, value):
        self.values = [value] * len(self.values)

    def show(self):
        self.show_count += 1


class LedTest(unittest.TestCase):
    def test_disabled_controller_reports_state(self):
        leds = DisabledLedController()

        leds.apply_settings(LedSettings(enabled=True, brightness=0.4))

        self.assertEqual(leds.status(), {
            "available": False,
            "enabled": True,
            "brightness": 0.4,
            "mode": "disabled",
            "testPattern": "idle",
        })

    def test_disabled_controller_records_test_pattern(self):
        leds = DisabledLedController()

        leds.run_test("border")

        self.assertEqual(leds.status()["testPattern"], "border")
        with self.assertRaises(ValueError):
            leds.run_test("unknown")


class MemoryLedControllerTest(unittest.TestCase):
    def test_highlights_legal_targets_for_lifted_piece(self):
        leds = MemoryLedController()
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_legal_targets(chess.Board(), "e2")

        self.assertEqual(leds.mode, "legal-targets")
        self.assertEqual(leds.highlighted_squares, ["e3", "e4"])

    def test_highlights_last_move_for_opponent_move_to_copy(self):
        leds = MemoryLedController()
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_move("e7e5")

        self.assertEqual(leds.mode, "move")
        self.assertEqual(leds.highlighted_squares, ["e7", "e5"])

    def test_setup_guidance_tracks_missing_and_extra_squares(self):
        leds = MemoryLedController()
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_setup_guidance(["e2", "d2", "c2"], ["e4"], frame=3)

        self.assertEqual(leds.mode, "setup")
        self.assertEqual(leds.highlighted_squares, ["e2", "d2", "c2"])
        self.assertEqual(leds.extra_squares, ["e4"])
        self.assertEqual(leds.setup_frame, 3)

    def test_dotstar_setup_guidance_lights_missing_extra_and_expected_occupied_squares(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        board = chess.Board()
        leds.show_setup_guidance(["a1"], ["h8"], frame=10, occupied_squares=["e2"], expected_board=board)

        lit = {index for index, value in enumerate(pixels.values) if value != (0, 0, 0)}
        expected_lit = set(SQUARE_TO_LED["a1"]) | set(SQUARE_TO_LED["h8"]) | set(SQUARE_TO_LED["e2"])
        self.assertEqual(lit, expected_lit)
        self.assertEqual([pixels.values[index] for index in SQUARE_TO_LED["h8"]], [EXTRA_COLOR] * 4)
        self.assertEqual(pixels.show_count, 1)

    def test_dotstar_setup_guidance_uses_warm_missing_color_without_expected_board(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_setup_guidance(["a1", "b1", "c1"], [], frame=0, occupied_squares=["h8"])

        for square in ["a1", "b1", "c1"]:
            self.assertEqual([pixels.values[index] for index in SQUARE_TO_LED[square]], [WARM_GLOW_COLOR] * 4)
        self.assertEqual(pixels.values[marker_led("h8")], (0, 0, 0))

    def test_dotstar_setup_lights_turn_off_when_square_is_no_longer_missing(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_setup_guidance(["a1", "b1"], [], frame=0)
        self.assertNotEqual(pixels.values[marker_led("a1")], (0, 0, 0))

        leds.show_setup_guidance(["b1"], [], frame=99)

        stale_only_a1 = set(SQUARE_TO_LED["a1"]) - set(SQUARE_TO_LED["b1"])
        for index in stale_only_a1:
            self.assertEqual(pixels.values[index], (0, 0, 0))
        self.assertNotEqual(pixels.values[marker_led("b1")], (0, 0, 0))

    def test_dotstar_setup_light_returns_when_magnet_is_removed_again(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_setup_guidance(["b1"], [], frame=5, occupied_squares=["h8"])
        stale_only_a1 = set(SQUARE_TO_LED["a1"]) - set(SQUARE_TO_LED["b1"])
        for index in stale_only_a1:
            self.assertEqual(pixels.values[index], (0, 0, 0))

        leds.show_setup_guidance(["a1", "b1"], [], frame=80, occupied_squares=["h8"])

        self.assertNotEqual(pixels.values[marker_led("a1")], (0, 0, 0))
        self.assertNotEqual(pixels.values[marker_led("b1")], (0, 0, 0))

    def test_shared_led_between_missing_and_occupied_square_gets_shared_color(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        shared = set(SQUARE_TO_LED["a1"]) & set(SQUARE_TO_LED["b1"])
        leds.show_setup_guidance(["b1"], [], frame=12, occupied_squares=["a1"], expected_board=chess.Board())

        self.assertTrue(shared)
        for index in shared:
            self.assertEqual(pixels.values[index], SHARED_LED_COLOR)

    def test_extra_square_lights_all_four_corners_red(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_setup_guidance([], ["e4"], frame=0, occupied_squares=["e4"])
        first_values = [pixels.values[index] for index in SQUARE_TO_LED["e4"]]
        leds.show_setup_guidance([], ["e4"], frame=6, occupied_squares=["e4"])
        second_values = [pixels.values[index] for index in SQUARE_TO_LED["e4"]]

        self.assertEqual(first_values, [EXTRA_COLOR] * 4)
        self.assertEqual(second_values, [EXTRA_COLOR] * 4)

    def test_setup_guidance_lights_expected_occupied_square(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_setup_guidance([], [], frame=0, occupied_squares=["e2"], expected_board=chess.Board())

        for index in SQUARE_TO_LED["e2"]:
            self.assertNotEqual(pixels.values[index], (0, 0, 0))

    def test_setup_guidance_is_stable_over_time_without_animation(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_setup_guidance([], [], frame=0, occupied_squares=["e2"], expected_board=chess.Board())
        first = list(pixels.values)
        leds.show_setup_guidance([], [], frame=16, occupied_squares=["e2"], expected_board=chess.Board())
        second = list(pixels.values)

        self.assertEqual(first, second)

    def test_setup_background_uses_warm_colors(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        for frame in [0, 64, 128]:
            leds.show_setup_guidance([], [], frame=frame, occupied_squares=["a1", "b1", "c1"])
            for red, green, blue in pixels.values:
                self.assertGreaterEqual(red + green, blue)

    def test_empty_last_row_does_not_animate(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_setup_guidance(["a1"], [], frame=8, occupied_squares=["e4"])

        last_row_squares = ["a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1"]
        last_row_marker_leds = {marker_led(square) for square in last_row_squares}
        animated_last_row = [
            index
            for index in last_row_marker_leds
            if pixels.values[index] != (0, 0, 0) and index != marker_led("a1")
        ]
        self.assertEqual(animated_last_row, [])

    def test_ready_animation_chases_first_to_last_led_and_clears(self):
        pixels = FakePixels()
        leds = DotStarLedController(pixels)
        leds.apply_settings(LedSettings(enabled=True, brightness=0.1))

        leds.show_ready_animation(delay=0)

        self.assertEqual(leds.mode, "ready")
        self.assertEqual(pixels.values, [(0, 0, 0)] * 81)
        self.assertGreaterEqual(pixels.show_count, 82)


if __name__ == "__main__":
    unittest.main()
