import unittest

import chess

from chessboard_app.leds import MemoryLedController
from chessboard_app.sensors import expected_occupancy_from_board
from play_local_computer import LocalComputerGame, choose_computer_move


class LocalComputerGameTest(unittest.TestCase):
    def test_choose_computer_move_returns_legal_move(self):
        board = chess.Board()

        move = choose_computer_move(board)

        self.assertIn(move, board.legal_moves)

    def test_player_move_then_computer_move_updates_board_and_lights_reply(self):
        leds = MemoryLedController()
        game = LocalComputerGame(
            leds=leds,
            choose_reply=lambda board: chess.Move.from_uci("e7e5"),
            printer=None,
        )
        before = expected_occupancy_from_board(game.board)
        moved = game.board.copy()
        moved.push(chess.Move.from_uci("e2e4"))
        after = expected_occupancy_from_board(moved)

        result = game.accept_player_position(before, after)

        self.assertEqual(result, "computer_move")
        self.assertEqual(game.pending_computer_move, "e7e5")
        self.assertEqual(leds.highlighted_squares, ["e7", "e5"])
        self.assertEqual(game.board.peek().uci(), "e7e5")

    def test_lifted_piece_lights_legal_targets(self):
        leds = MemoryLedController()
        game = LocalComputerGame(leds=leds, printer=None)
        game.last_occupancy = {square: False for square in expected_occupancy_from_board(game.board)}
        occupancy = expected_occupancy_from_board(game.board)
        occupancy["e2"] = False

        result = game.handle_snapshot(occupancy)

        self.assertEqual(result, "piece_lifted")
        self.assertEqual(game.pending_before["e2"], True)
        self.assertEqual(leds.highlighted_squares, ["e3", "e4"])

    def test_unsynced_board_does_not_start_move_detection(self):
        leds = MemoryLedController()
        game = LocalComputerGame(leds=leds, printer=None)
        occupancy = {square: False for square in expected_occupancy_from_board(game.board)}

        result = game.handle_snapshot(occupancy)

        self.assertEqual(result, "sync_required")
        self.assertIsNone(game.pending_before)
        self.assertEqual(leds.mode, "setup")
        self.assertIn("a1", leds.highlighted_squares)
        self.assertIn("a1", game.sync_message())

    def test_synced_board_reports_ready_once(self):
        leds = MemoryLedController()
        game = LocalComputerGame(leds=leds, printer=None)

        result = game.handle_snapshot(expected_occupancy_from_board(game.board))

        self.assertEqual(result, "synced")
        self.assertEqual(game.sync_message(), "Board synced. Make your move.")
        self.assertEqual(leds.mode, "ready")

    def test_confirms_computer_move_when_physical_board_matches(self):
        leds = MemoryLedController()
        game = LocalComputerGame(
            leds=leds,
            choose_reply=lambda board: chess.Move.from_uci("e7e5"),
            printer=None,
        )
        before = expected_occupancy_from_board(game.board)
        player_board = game.board.copy()
        player_board.push(chess.Move.from_uci("e2e4"))
        game.accept_player_position(before, expected_occupancy_from_board(player_board))

        result = game.handle_snapshot(expected_occupancy_from_board(game.board))

        self.assertEqual(result, "computer_move_confirmed")
        self.assertIsNone(game.pending_computer_move)
        self.assertEqual(leds.highlighted_squares, [])

    def test_pass_mode_allows_sparse_board_move_without_full_setup(self):
        leds = MemoryLedController()
        game = LocalComputerGame(
            leds=leds,
            choose_reply=lambda board: chess.Move.from_uci("e7e5"),
            printer=None,
            pass_mode=True,
        )
        empty = {square: False for square in expected_occupancy_from_board(game.board)}
        with_e2 = dict(empty)
        with_e2["e2"] = True
        with_e4 = dict(empty)
        with_e4["e4"] = True

        self.assertEqual(game.handle_snapshot(empty), "idle")
        self.assertEqual(game.handle_snapshot(with_e2), "idle")
        self.assertEqual(game.handle_snapshot(empty), "piece_lifted")
        self.assertEqual(leds.highlighted_squares, ["e3", "e4"])

        result = game.handle_snapshot(with_e4)

        self.assertEqual(result, "computer_move")
        self.assertEqual(game.board.move_stack[-2].uci(), "e2e4")
        self.assertEqual(game.board.move_stack[-1].uci(), "e7e5")
        self.assertIsNone(game.pending_computer_move)
        self.assertEqual(leds.highlighted_squares, ["e7", "e5"])

    def test_pass_mode_rejects_illegal_sparse_move(self):
        leds = MemoryLedController()
        game = LocalComputerGame(leds=leds, printer=None, pass_mode=True)
        empty = {square: False for square in expected_occupancy_from_board(game.board)}
        with_e2 = dict(empty)
        with_e2["e2"] = True
        with_e5 = dict(empty)
        with_e5["e5"] = True

        game.handle_snapshot(empty)
        game.handle_snapshot(with_e2)
        game.handle_snapshot(empty)

        result = game.handle_snapshot(with_e5)

        self.assertEqual(result, "illegal")
        self.assertEqual(len(game.board.move_stack), 0)


if __name__ == "__main__":
    unittest.main()
