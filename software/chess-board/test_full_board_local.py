"""Local hardware test for the full 8x8 board.

Setup phase:
- Expected position is the normal chess starting position.
- Each missing expected piece shows a constant light-red marker on a single
  dedicated LED per square (the lowest index from that square's 4 corner
  LEDs), so shared corner LEDs do not bleed into neighboring squares.
- Detected magnets pulse a soft warm animation on their own marker LED.
- Extra magnets (where no piece is expected) show a constant warm orange
  marker on the same single-LED pattern.
- Empty squares with no magnet and no expected piece stay dark.
- When all expected pieces are detected, a short warm ready animation runs
  and the script enters play mode.

Play phase:
- Lift a piece: legal destination squares are highlighted using the full
  4-corner LED mapping.
- Place that piece on a legal destination: the move is committed, then a
  random legal computer reply is chosen and shown on the board (4-corner)
  for the user to physically perform.
- Once the user mirrors the computer move, the script returns to waiting
  for the user's next move.
"""

from __future__ import annotations

import argparse
import math
import random
import time
from typing import Mapping, Sequence

import chess

from chessboard_app.leds import DotStarLedController, LedSettings
from chessboard_app.move_detection import detect_move
from chessboard_app.sensors import (
    McpSensorReader,
    diff_occupancy,
    expected_occupancy_from_board,
)
from led_mapping import SQUARE_TO_LED


MISSING_COLOR = (200, 14, 6)
EXTRA_COLOR = (220, 90, 0)
WARM_GLOW_COLOR = (220, 90, 12)
LEGAL_TARGET_COLOR = (160, 140, 0)
COMPUTER_MOVE_COLOR = (0, 80, 180)
READY_COLOR = (0, 120, 40)


def square_marker_index(square: str) -> int | None:
    indexes = SQUARE_TO_LED.get(square, [])
    return min(indexes) if indexes else None


class WarmBoardController(DotStarLedController):
    """DotStar controller with bright warm setup, green ready, classic play colors."""

    def show_setup_guidance(
        self,
        missing_squares: Sequence[str],
        extra_squares: Sequence[str],
        frame: int = 0,
        occupied_squares: Sequence[str] | None = None,
    ) -> None:
        self.mode = "setup"
        self.highlighted_squares = list(missing_squares)
        self.extra_squares = list(extra_squares)
        self.setup_frame = frame
        if not self.settings.enabled:
            self.clear()
            return

        self.pixels.fill((0, 0, 0))
        phase = (frame % 32) / 32
        glow = 0.35 + 0.65 * ((1 - math.cos(phase * math.tau)) / 2)
        warm = _scale(WARM_GLOW_COLOR, glow)
        for square in occupied_squares or []:
            for index in SQUARE_TO_LED.get(square, []):
                if 0 <= index < self.count:
                    self.pixels[index] = warm
        for square in missing_squares:
            index = square_marker_index(square)
            if index is not None and 0 <= index < self.count:
                self.pixels[index] = MISSING_COLOR
        for square in extra_squares:
            index = square_marker_index(square)
            if index is not None and 0 <= index < self.count:
                self.pixels[index] = EXTRA_COLOR
        self.pixels.show()

    def show_ready_animation(self, delay: float = 0.012) -> None:
        self.mode = "ready"
        self.highlighted_squares = []
        self.extra_squares = []
        if not self.settings.enabled:
            self.clear()
            return
        for index in range(self.count):
            self.pixels.fill((0, 0, 0))
            for tail_offset, level in enumerate((1.0, 0.45, 0.18)):
                tail_index = index - tail_offset
                if 0 <= tail_index < self.count:
                    self.pixels[tail_index] = _scale(READY_COLOR, level)
            self.pixels.show()
            if delay:
                time.sleep(delay)
        self.pixels.fill((0, 0, 0))
        self.pixels.show()

    def show_legal_targets(self, board: chess.Board, from_square: str) -> None:
        super(DotStarLedController, self).show_legal_targets(board, from_square)
        if self.settings.enabled:
            self._light_squares(self.highlighted_squares, LEGAL_TARGET_COLOR)

    def show_move(self, uci: str) -> None:
        super(DotStarLedController, self).show_move(uci)
        if self.settings.enabled:
            self._light_squares(self.highlighted_squares, COMPUTER_MOVE_COLOR)


def _scale(color: tuple[int, int, int], scale: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel * scale))) for channel in color)


class FullBoardSession:
    def __init__(self, leds: WarmBoardController) -> None:
        self.leds = leds
        self.board = chess.Board()
        self.synced = False
        self.setup_frame = 0
        self.last_occupancy: dict[str, bool] = {}
        self.pending_from: str | None = None
        self.pending_before: dict[str, bool] | None = None
        self.pending_computer_move: str | None = None

    def step(self, occupancy: Mapping[str, bool]) -> str:
        occupancy = dict(occupancy)
        expected = expected_occupancy_from_board(self.board)

        if self.pending_computer_move:
            if diff_occupancy(expected, occupancy)["matches"]:
                print(f"Computer move confirmed: {self.pending_computer_move}")
                self.pending_computer_move = None
                self.last_occupancy = occupancy
                self.leds.clear()
                if self.board.is_game_over():
                    print(f"Game over: {self.board.result()}")
                    return "game_over"
                return "your_turn"
            self.leds.show_move(self.pending_computer_move)
            return "awaiting_computer_move"

        if not self.synced:
            return self._handle_setup(expected, occupancy)

        return self._handle_play(expected, occupancy)

    def _handle_setup(
        self,
        expected: Mapping[str, bool],
        occupancy: Mapping[str, bool],
    ) -> str:
        sync = diff_occupancy(expected, occupancy)
        if sync["matches"]:
            self.synced = True
            self.last_occupancy = dict(occupancy)
            print("All pieces in place. Ready.")
            self.leds.show_ready_animation()
            self.leds.clear()
            return "synced"

        occupied = [square for square, present in occupancy.items() if present]
        self.leds.show_setup_guidance(
            sync["missing"],
            sync["extra"],
            self.setup_frame,
            occupied_squares=occupied,
        )
        self.setup_frame += 1
        return "setup"

    def _handle_play(
        self,
        expected: Mapping[str, bool],
        occupancy: Mapping[str, bool],
    ) -> str:
        if self.pending_from is None:
            lifted = [
                square
                for square, was_present in expected.items()
                if was_present and not occupancy.get(square, False)
            ]
            placed = [
                square
                for square, is_present in occupancy.items()
                if is_present and not expected.get(square, False)
            ]
            if not lifted and not placed:
                self.last_occupancy = dict(occupancy)
                return "idle"
            if len(lifted) == 1 and not placed:
                self.pending_from = lifted[0]
                self.pending_before = dict(expected)
                self.leds.show_legal_targets(self.board, lifted[0])
                self.last_occupancy = dict(occupancy)
                print(f"Lifted {lifted[0]}. Place on a lit square.")
                return "lifted"
            self.last_occupancy = dict(occupancy)
            return "transient"

        if occupancy.get(self.pending_from, False) and self.pending_before == occupancy:
            print(f"Piece returned to {self.pending_from}.")
            self.pending_from = None
            self.pending_before = None
            self.leds.clear()
            self.last_occupancy = dict(occupancy)
            return "cancelled"

        before = self.pending_before or expected
        placed_now = [
            square
            for square, is_present in occupancy.items()
            if is_present and not before.get(square, False)
        ]
        if not placed_now:
            self.last_occupancy = dict(occupancy)
            return "still_lifted"

        return self._commit_player_move(before, occupancy)

    def _commit_player_move(
        self,
        before: Mapping[str, bool],
        after: Mapping[str, bool],
    ) -> str:
        result = detect_move(self.board, before, after)
        if result.kind != "move" or result.uci is None:
            print(f"Move rejected: {result.kind} {result.reason or ''}".strip())
            self.pending_from = None
            self.pending_before = None
            self.synced = False
            self.leds.clear()
            return result.kind

        player_move = chess.Move.from_uci(result.uci)
        self.board.push(player_move)
        self.pending_from = None
        self.pending_before = None
        self.last_occupancy = dict(after)
        print(f"Your move: {player_move.uci()}")
        self.leds.clear()

        if self.board.is_game_over():
            print(f"Game over: {self.board.result()}")
            return "game_over"

        reply = random.choice(list(self.board.legal_moves))
        self.board.push(reply)
        self.pending_computer_move = reply.uci()
        print(f"Computer move: {reply.uci()}. Move the lit piece.")
        self.leds.show_move(reply.uci())
        return "computer_move"


def main() -> None:
    parser = argparse.ArgumentParser(description="Full 8x8 board local test: setup + play.")
    parser.add_argument("--brightness", type=float, default=0.1)
    parser.add_argument("--poll-seconds", type=float, default=0.05)
    args = parser.parse_args()

    sensors = McpSensorReader.create()
    leds = WarmBoardController.create()
    leds.apply_settings(LedSettings(enabled=True, brightness=args.brightness))

    session = FullBoardSession(leds)

    print("=== Full board local test ===")
    print("Set up the normal starting position. Missing pieces are red.")
    print("Detected magnets glow warm; extra magnets show as orange.")
    print("Once the position matches, play begins. Ctrl+C to stop.")
    print()
    print(session.board)

    try:
        while True:
            time.sleep(args.poll_seconds)
            occupancy = sensors.read().as_dict()
            session.step(occupancy)
    except KeyboardInterrupt:
        leds.clear()
        print("\nStopped.")


if __name__ == "__main__":
    main()
