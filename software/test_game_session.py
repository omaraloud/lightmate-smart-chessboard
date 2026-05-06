import unittest

import chess

from chessboard_app.game_session import GameSession, parse_clocks
from chessboard_app.sensors import expected_occupancy_from_board


class GameSessionTest(unittest.TestCase):
    def puzzle_payload(self):
        return {
            "game": {
                "id": "setupGame",
                "pgn": "e4 e5",
                "players": [
                    {"color": "white", "name": "White", "rating": 1500},
                    {"color": "black", "name": "Black", "rating": 1500},
                ],
            },
            "puzzle": {
                "id": "puzzle1",
                "rating": 1200,
                "themes": ["opening", "short"],
                "initialPly": 2,
                "solution": ["g1f3", "b8c6"],
            },
        }

    def test_loads_game_state_from_moves_and_clocks(self):
        session = GameSession()

        session.update_from_lichess_state({
            "id": "game1",
            "white": {"name": "alice", "rating": 1500},
            "black": {"name": "bob", "rating": 1600},
            "state": {"moves": "e2e4 e7e5", "wtime": 295000, "btime": 296000},
        })

        state = session.public_state()
        self.assertEqual(state["id"], "game1")
        expected = chess.Board()
        expected.push(chess.Move.from_uci("e2e4"))
        expected.push(chess.Move.from_uci("e7e5"))
        self.assertEqual(state["fen"], expected.fen())
        self.assertEqual(state["lastMove"], "e7e5")
        self.assertEqual(state["clock"]["whiteMs"], 295000)
        self.assertEqual(state["players"]["black"]["name"], "bob")
        self.assertEqual(state["pieces"]["e4"], "P")
        self.assertEqual(state["pieces"]["e5"], "p")

    def test_tracks_draw_offer_from_lichess_state(self):
        session = GameSession()

        session.update_from_lichess_state({
            "id": "game1",
            "state": {"moves": "e2e4", "wtime": 1000, "btime": 2000, "bdraw": True},
        })

        state = session.public_state()
        self.assertEqual(state["drawOffer"], "black")

    def test_tracks_game_winner_from_lichess_state(self):
        session = GameSession()

        session.update_from_lichess_state({
            "id": "game1",
            "state": {"moves": "e2e4 e7e5", "status": "mate", "winner": "black"},
        })

        state = session.public_state()
        self.assertEqual(state["status"], "mate")
        self.assertEqual(state["winner"], "black")

    def test_tracks_resignation_winner_from_lichess_state(self):
        session = GameSession()

        session.update_from_lichess_state({
            "id": "game1",
            "state": {"moves": "e2e4", "status": "resign", "winner": "white"},
        })

        state = session.public_state()
        self.assertEqual(state["status"], "resign")
        self.assertEqual(state["winner"], "white")

    def test_sync_status_reports_missing_and_extra_squares(self):
        session = GameSession()
        board = chess.Board()
        expected = expected_occupancy_from_board(board)
        actual = dict(expected)
        actual["e2"] = False
        actual["e4"] = True

        sync = session.sync_status(actual)

        self.assertFalse(sync["matches"])
        self.assertEqual(sync["missing"], ["e2"])
        self.assertEqual(sync["extra"], ["e4"])

    def test_detects_and_applies_physical_move(self):
        session = GameSession()
        before = expected_occupancy_from_board(session.board)
        after_board = session.board.copy()
        after_board.push(chess.Move.from_uci("e2e4"))
        after = expected_occupancy_from_board(after_board)

        result = session.detect_physical_move(before, after)

        self.assertEqual(result.kind, "move")
        self.assertEqual(result.uci, "e2e4")

    def test_tracks_synced_snapshot_and_applies_submitted_move(self):
        session = GameSession()
        before = expected_occupancy_from_board(session.board)
        after_board = session.board.copy()
        after_board.push(chess.Move.from_uci("e2e4"))
        after = expected_occupancy_from_board(after_board)

        session.mark_synced(before)
        result = session.detect_move_from_last_snapshot(after)
        session.apply_submitted_move(result.uci, after)

        self.assertEqual(result.uci, "e2e4")
        self.assertEqual(session.last_move, "e2e4")
        self.assertEqual(session.last_occupancy, after)
        self.assertEqual(session.board.peek(), chess.Move.from_uci("e2e4"))

    def test_copied_last_move_matches_only_until_board_is_marked_synced(self):
        session = GameSession()
        session.update_from_lichess_state({"state": {"moves": "e2e4 e7e5", "status": "started"}})
        physical_board = chess.Board()
        physical_board.push(chess.Move.from_uci("e2e4"))
        physical_board.push(chess.Move.from_uci("e7e5"))
        copied = expected_occupancy_from_board(physical_board)

        self.assertTrue(session.copied_last_move_matches(copied))

        session.mark_synced(session.expected_occupancy())

        self.assertFalse(session.copied_last_move_matches(copied))

    def test_loads_puzzle_position_and_public_piece_map(self):
        session = GameSession()

        session.load_puzzle(self.puzzle_payload())

        state = session.public_state()
        expected = chess.Board()
        expected.push(chess.Move.from_uci("e2e4"))
        expected.push(chess.Move.from_uci("e7e5"))
        self.assertEqual(state["mode"], "puzzle_setup")
        self.assertEqual(state["fen"], expected.fen())
        self.assertEqual(state["puzzle"]["id"], "puzzle1")
        self.assertEqual(state["puzzle"]["rating"], 1200)
        self.assertEqual(state["puzzle"]["solutionIndex"], 0)
        self.assertEqual(state["pieces"]["e4"], "P")
        self.assertEqual(state["pieces"]["e5"], "p")
        self.assertEqual(state["pieces"]["g1"], "N")

    def test_puzzle_accepts_correct_move_applies_reply_and_completes(self):
        session = GameSession()
        session.load_puzzle(self.puzzle_payload())
        before = expected_occupancy_from_board(session.board)
        after_board = session.board.copy()
        after_board.push(chess.Move.from_uci("g1f3"))
        after = expected_occupancy_from_board(after_board)

        session.start_puzzle(before)
        result = session.submit_puzzle_move(after)

        self.assertEqual(result["accepted"], True)
        self.assertEqual(result["move"], "g1f3")
        self.assertEqual(result["reply"], "b8c6")
        self.assertEqual(session.last_move, "b8c6")
        self.assertEqual(session.public_state()["puzzle"]["status"], "complete")
        self.assertEqual(session.public_state()["puzzle"]["solutionIndex"], 2)

    def test_puzzle_rejects_wrong_physical_move_without_advancing(self):
        session = GameSession()
        session.load_puzzle(self.puzzle_payload())
        before = expected_occupancy_from_board(session.board)
        wrong_board = session.board.copy()
        wrong_board.push(chess.Move.from_uci("d2d4"))

        session.start_puzzle(before)
        result = session.submit_puzzle_move(expected_occupancy_from_board(wrong_board))

        self.assertEqual(result["accepted"], False)
        self.assertEqual(result["expected"], "g1f3")
        self.assertEqual(session.public_state()["puzzle"]["solutionIndex"], 0)


class ClockParsingTest(unittest.TestCase):
    def test_parse_clocks_defaults_missing_values(self):
        self.assertEqual(parse_clocks({}), {"whiteMs": None, "blackMs": None})

    def test_parse_clocks_reads_lichess_state_names(self):
        self.assertEqual(
            parse_clocks({"wtime": 1000, "btime": 2000}),
            {"whiteMs": 1000, "blackMs": 2000},
        )


if __name__ == "__main__":
    unittest.main()
