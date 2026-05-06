from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Sequence

import chess

from chessboard_app.orientation import orient_square
from led_mapping import LED_GRID, SQUARE_TO_LED


SETUP_BREATH_PERIOD = 32
SETUP_PATTERN_PERIOD = 48
MISSING_COLOR = (6, 14, 200)
EXTRA_COLOR = (80, 0, 0)
EXTRA_DIM_COLOR = (40, 0, 0)
CORRECT_SETUP_COLOR = (0, 45, 140)
WARM_GLOW_COLOR = (12, 90, 220)
WHITE_PIECE_COLOR = (220, 0, 180)
BLACK_PIECE_COLOR = (0, 120, 0)
SHARED_LED_COLOR = (0, 0, 160)
WHITE_PLACED_COLOR = (180, 100, 150)
BLACK_PLACED_COLOR = WHITE_PLACED_COLOR
LEGAL_SOURCE_COLOR = WHITE_PIECE_COLOR
DESTINATION_COLOR = (120, 0, 0)
LEGAL_TARGET_COLOR = DESTINATION_COLOR
MOVE_COLOR = DESTINATION_COLOR
READY_COLOR = (0, 120, 40)
CLEAR_FRAME_REPEATS = 3


@dataclass(frozen=True)
class LedSettings:
    enabled: bool = False
    brightness: float = 0.1
    orientation: str = "white"


class DisabledLedController:
    def __init__(self):
        self.settings = LedSettings()
        self.test_pattern = "idle"

    def apply_settings(self, settings: LedSettings) -> None:
        self.settings = settings

    def run_test(self, pattern: str) -> None:
        if pattern not in {"all", "border", "square", "idle"}:
            raise ValueError("unknown LED test pattern")
        self.test_pattern = pattern

    def clear(self) -> None:
        self.test_pattern = "idle"

    def show_legal_targets(self, board: chess.Board, from_square: str) -> None:
        self.test_pattern = "legal-targets"

    def show_move(self, uci: str) -> None:
        self.test_pattern = "move"

    def show_setup_guidance(
        self,
        missing_squares: Sequence[str],
        extra_squares: Sequence[str],
        frame: int = 0,
        occupied_squares: Sequence[str] | None = None,
        expected_board: chess.Board | None = None,
        expected_player_color: str | None = None,
    ) -> None:
        self.test_pattern = "setup"

    def show_ready_animation(self, delay: float = 0.008) -> None:
        self.test_pattern = "ready"

    def status(self) -> dict[str, object]:
        return {
            "available": False,
            "enabled": self.settings.enabled,
            "brightness": self.settings.brightness,
            "mode": "disabled",
            "testPattern": self.test_pattern,
        }


class MemoryLedController(DisabledLedController):
    def __init__(self):
        super().__init__()
        self.mode = "idle"
        self.highlighted_squares: list[str] = []
        self.extra_squares: list[str] = []
        self.setup_frame = 0

    def clear(self) -> None:
        self.mode = "idle"
        self.highlighted_squares = []
        self.extra_squares = []

    def run_test(self, pattern: str) -> None:
        super().run_test(pattern)
        self.mode = pattern
        self.highlighted_squares = []
        self.extra_squares = []

    def show_legal_targets(self, board: chess.Board, from_square: str) -> None:
        self.mode = "legal-targets"
        self.extra_squares = []
        source = chess.parse_square(from_square)
        self.highlighted_squares = [
            chess.square_name(move.to_square)
            for move in board.legal_moves
            if move.from_square == source
        ]

    def show_move(self, uci: str) -> None:
        self.mode = "move"
        self.extra_squares = []
        self.highlighted_squares = [uci[:2], uci[2:4]]

    def show_setup_guidance(
        self,
        missing_squares: Sequence[str],
        extra_squares: Sequence[str],
        frame: int = 0,
        occupied_squares: Sequence[str] | None = None,
        expected_board: chess.Board | None = None,
        expected_player_color: str | None = None,
    ) -> None:
        self.mode = "setup"
        self.highlighted_squares = list(missing_squares)
        self.extra_squares = list(extra_squares)
        self.setup_frame = frame

    def show_ready_animation(self, delay: float = 0.008) -> None:
        self.mode = "ready"
        self.highlighted_squares = []
        self.extra_squares = []

    def status(self) -> dict[str, object]:
        return {
            "available": True,
            "enabled": self.settings.enabled,
            "brightness": self.settings.brightness,
            "mode": self.mode,
            "testPattern": self.test_pattern,
            "highlightedSquares": self.highlighted_squares,
            "extraSquares": self.extra_squares,
        }


class DotStarLedController(MemoryLedController):
    def __init__(self, pixels, count: int = 81):
        super().__init__()
        self.pixels = pixels
        self.count = count

    @classmethod
    def create(cls, count: int = 81) -> DotStarLedController:
        import board as circuit_board  # type: ignore
        import adafruit_dotstar as dotstar  # type: ignore

        pixels = dotstar.DotStar(
            circuit_board.SCK,
            circuit_board.MOSI,
            count,
            brightness=0.1,
            auto_write=False,
        )
        return cls(pixels, count=count)

    def apply_settings(self, settings: LedSettings) -> None:
        super().apply_settings(settings)
        self.pixels.brightness = settings.brightness
        if not settings.enabled:
            self.clear()

    def clear(self) -> None:
        super().clear()
        self._clear_pixels()

    def _clear_pixels(self, repeats: int = CLEAR_FRAME_REPEATS) -> None:
        self.pixels.fill((0, 0, 0))
        for _ in range(repeats):
            self.pixels.show()

    def run_test(self, pattern: str) -> None:
        super().run_test(pattern)
        if not self.settings.enabled:
            self.clear()
            return
        if pattern == "idle":
            self.clear()
        elif pattern == "all":
            self._light_indexes(range(self.count), EXTRA_COLOR)
        elif pattern == "border":
            border = set()
            for row in (0, 8):
                border.update(range(row * 9, row * 9 + 9))
            for row in range(9):
                border.add(row * 9)
                border.add(row * 9 + 8)
            self._light_indexes(border, (0, 80, 30))
        elif pattern == "square":
            self._light_squares(["e4", "d4", "e5", "d5"], (80, 60, 0))

    def show_legal_targets(self, board: chess.Board, from_square: str) -> None:
        super().show_legal_targets(board, from_square)
        if self.settings.enabled:
            self.pixels.fill((0, 0, 0))
            self._set_square_color(self.highlighted_squares, DESTINATION_COLOR)
            self._set_square_color([from_square], LEGAL_SOURCE_COLOR)
            self.pixels.show()

    def show_move(self, uci: str) -> None:
        super().show_move(uci)
        if self.settings.enabled:
            self.pixels.fill((0, 0, 0))
            self._set_square_color([uci[:2]], LEGAL_SOURCE_COLOR)
            self._set_square_color([uci[2:4]], DESTINATION_COLOR)
            self.pixels.show()

    def show_setup_guidance(
        self,
        missing_squares: Sequence[str],
        extra_squares: Sequence[str],
        frame: int = 0,
        occupied_squares: Sequence[str] | None = None,
        expected_board: chess.Board | None = None,
        expected_player_color: str | None = None,
    ) -> None:
        super().show_setup_guidance(
            missing_squares,
            extra_squares,
            frame,
            occupied_squares,
            expected_board,
            expected_player_color,
        )
        if not self.settings.enabled:
            self.clear()
            return

        self.pixels.fill((0, 0, 0))
        self._set_setup_expected_squares(
            occupied_squares or [],
            missing_squares,
            expected_board,
            expected_player_color,
        )
        self._set_square_color(extra_squares, EXTRA_COLOR)
        self.pixels.show()

    def show_ready_animation(self, delay: float = 0.008) -> None:
        super().show_ready_animation(delay)
        if not self.settings.enabled:
            self.clear()
            return
        for index in range(self.count):
            self.pixels.fill((0, 0, 0))
            for tail_offset, level in enumerate((1.0, 0.45, 0.18)):
                tail_index = index - tail_offset
                if 0 <= tail_index < self.count:
                    self.pixels[tail_index] = _scale_color(READY_COLOR, level)
            self.pixels.show()
            if delay:
                time.sleep(delay)
        self.pixels.fill((0, 0, 0))
        self.pixels.show()

    def _light_squares(self, squares: Sequence[str], color: tuple[int, int, int]) -> None:
        indexes = []
        for square in squares:
            indexes.extend(SQUARE_TO_LED.get(self._physical_square(square), []))
        self._light_indexes(indexes, color)

    def _set_square_color(self, squares: Sequence[str], color: tuple[int, int, int]) -> None:
        for square in squares:
            for index in SQUARE_TO_LED.get(self._physical_square(square), []):
                if 0 <= index < self.count:
                    self.pixels[index] = color

    def _set_square_markers(self, squares: Sequence[str], color: tuple[int, int, int]) -> None:
        for square in squares:
            index = _square_marker(self._physical_square(square))
            if index is not None and 0 <= index < self.count:
                self.pixels[index] = color

    def _set_correct_setup_squares(
        self,
        occupied_squares: Sequence[str],
        expected_board: chess.Board | None,
    ) -> None:
        if expected_board is None:
            return
        expected = {
            chess.square_name(square)
            for square in expected_board.piece_map().keys()
        }
        for square in occupied_squares:
            if square not in expected:
                continue
            color = _expected_placed_color(expected_board, square)
            self._set_square_color([square], color or CORRECT_SETUP_COLOR)

    def _set_setup_expected_squares(
        self,
        occupied_squares: Sequence[str],
        missing_squares: Sequence[str],
        expected_board: chess.Board | None,
        expected_player_color: str | None = None,
    ) -> None:
        colors_by_led: dict[int, list[tuple[int, int, int]]] = {}
        expected = set()
        if expected_board is not None:
            expected = {
                chess.square_name(square)
                for square in expected_board.piece_map().keys()
            }

        for square in occupied_squares:
            if square not in expected:
                continue
            color = _expected_placed_color(expected_board, square) or CORRECT_SETUP_COLOR
            self._queue_square_led_colors(colors_by_led, square, color)

        for square in missing_squares:
            color = _expected_piece_color(expected_board, square, expected_player_color)
            if color is None:
                color = WARM_GLOW_COLOR
            self._queue_square_led_colors(colors_by_led, square, color)

        for index, colors in colors_by_led.items():
            self.pixels[index] = _merged_led_color(colors)

    def _set_missing_setup_squares(
        self,
        missing_squares: Sequence[str],
        expected_board: chess.Board | None,
        expected_player_color: str | None = None,
    ) -> None:
        for square in missing_squares:
            color = _expected_piece_color(expected_board, square, expected_player_color)
            if color is None:
                color = WARM_GLOW_COLOR
            self._set_square_color([square], color)

    def _set_expected_piece_squares(
        self,
        occupied_squares: Sequence[str],
        expected_board: chess.Board | None,
        expected_player_color: str | None = None,
    ) -> None:
        led_colors: dict[int, list[tuple[int, int, int]]] = {}
        for square in occupied_squares:
            color = _expected_piece_color(expected_board, square, expected_player_color)
            if color is None:
                color = _scale_color(WARM_GLOW_COLOR, 0.5)
            self._queue_square_led_colors(led_colors, square, color)
        for index, colors in led_colors.items():
            self.pixels[index] = _merged_led_color(colors)

    def _queue_square_led_colors(
        self,
        led_colors: dict[int, list[tuple[int, int, int]]],
        square: str,
        color: tuple[int, int, int],
    ) -> None:
        for index in SQUARE_TO_LED.get(self._physical_square(square), []):
            if 0 <= index < self.count:
                led_colors.setdefault(index, []).append(color)

    def _physical_square(self, square: str) -> str:
        return orient_square(square, getattr(self.settings, "orientation", "white"))

    def _light_indexes(self, indexes, color: tuple[int, int, int]) -> None:
        self.pixels.fill((0, 0, 0))
        for index in indexes:
            if 0 <= index < self.count:
                self.pixels[index] = color
        self.pixels.show()


def _scale_color(color: tuple[int, int, int], scale: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel * scale))) for channel in color)


def _merged_led_color(colors: Sequence[tuple[int, int, int]]) -> tuple[int, int, int]:
    unique_colors = set(colors)
    if len(unique_colors) <= 1:
        return colors[0]
    return SHARED_LED_COLOR


def _expected_piece_color(
    expected_board: chess.Board | None,
    square: str,
    expected_player_color: str | None = None,
) -> tuple[int, int, int] | None:
    if expected_board is None:
        return None
    piece = expected_board.piece_at(chess.parse_square(square))
    if piece is None:
        return None
    if expected_player_color == "black":
        return WHITE_PIECE_COLOR if piece.color == chess.BLACK else BLACK_PIECE_COLOR
    return WHITE_PIECE_COLOR if piece.color == chess.WHITE else BLACK_PIECE_COLOR


def _expected_placed_color(
    expected_board: chess.Board | None,
    square: str,
) -> tuple[int, int, int] | None:
    if expected_board is None:
        return None
    piece = expected_board.piece_at(chess.parse_square(square))
    if piece is None:
        return None
    return WHITE_PLACED_COLOR if piece.color == chess.WHITE else BLACK_PLACED_COLOR


def _square_marker(square: str) -> int | None:
    indexes = SQUARE_TO_LED.get(square, [])
    if not indexes:
        return None
    return min(indexes)
