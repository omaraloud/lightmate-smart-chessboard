from __future__ import annotations

from dataclasses import dataclass, field
import io
from typing import Any, Mapping

import chess
import chess.pgn

from chessboard_app.move_detection import MoveDetectionResult, detect_move
from chessboard_app.sensors import diff_occupancy, expected_occupancy_from_board


def parse_clocks(state: Mapping[str, Any]) -> dict[str, int | None]:
    return {
        "whiteMs": state.get("wtime"),
        "blackMs": state.get("btime"),
    }


def board_from_uci_moves(moves_text: str) -> chess.Board:
    board = chess.Board()
    for uci in moves_text.split():
        board.push(chess.Move.from_uci(uci))
    return board


@dataclass
class GameSession:
    game_id: str | None = None
    board: chess.Board = field(default_factory=chess.Board)
    players: dict[str, dict[str, Any]] = field(default_factory=lambda: {
        "white": {"name": None, "rating": None},
        "black": {"name": None, "rating": None},
    })
    clock: dict[str, int | None] = field(default_factory=lambda: {
        "whiteMs": None,
        "blackMs": None,
    })
    status: str = "idle"
    last_move: str | None = None
    player_color: str | None = None
    player_color_reason: str | None = None
    last_occupancy: dict[str, bool] | None = None
    mode: str = "game"
    puzzle: dict[str, Any] | None = None
    puzzle_solution: list[str] = field(default_factory=list)
    puzzle_index: int = 0
    draw_offer: str | None = None
    winner: str | None = None
    display_board: chess.Board | None = None

    def update_from_lichess_state(self, event: Mapping[str, Any]) -> None:
        self.mode = "game"
        self.puzzle = None
        self.puzzle_solution = []
        self.puzzle_index = 0
        self.display_board = None
        self.game_id = event.get("id", self.game_id)
        self.players = {
            "white": _player_public(event.get("white", {})),
            "black": _player_public(event.get("black", {})),
        }
        state = event.get("state", event)
        moves_text = state.get("moves", "")
        self.board = board_from_uci_moves(moves_text)
        moves = moves_text.split()
        self.last_move = moves[-1] if moves else None
        self.clock = parse_clocks(state)
        self.status = state.get("status", event.get("status", "started"))
        self.draw_offer = _draw_offer_from_state(state)
        self.winner = _winner_from_state(state)

    def reset_to_game_setup(self) -> None:
        self.game_id = None
        self.board = chess.Board()
        self.players = {
            "white": {"name": None, "rating": None},
            "black": {"name": None, "rating": None},
        }
        self.clock = {"whiteMs": None, "blackMs": None}
        self.status = "idle"
        self.last_move = None
        self.player_color = None
        self.player_color_reason = None
        self.last_occupancy = None
        self.mode = "game"
        self.puzzle = None
        self.puzzle_solution = []
        self.puzzle_index = 0
        self.draw_offer = None
        self.winner = None
        self.display_board = None

    def expected_occupancy(self) -> dict[str, bool]:
        return expected_occupancy_from_board(self.board)

    def sync_status(self, actual_occupancy: Mapping[str, bool]) -> dict[str, Any]:
        return diff_occupancy(self.expected_occupancy(), actual_occupancy)

    def detect_physical_move(
        self,
        before_occupancy: Mapping[str, bool],
        after_occupancy: Mapping[str, bool],
        allow_unsynced: bool = False,
    ) -> MoveDetectionResult:
        return detect_move(self.board, before_occupancy, after_occupancy, allow_unsynced=allow_unsynced)

    def mark_synced(self, occupancy: Mapping[str, bool]) -> None:
        self.last_occupancy = dict(occupancy)
        if self.display_board is not None and self.sync_status(occupancy)["matches"]:
            self.display_board = None

    def detect_move_from_last_snapshot(
        self,
        after_occupancy: Mapping[str, bool],
        allow_unsynced: bool = False,
    ) -> MoveDetectionResult:
        if self.last_occupancy is None:
            return MoveDetectionResult(kind="sync_required", reason="No synced physical snapshot")
        return self.detect_physical_move(self.last_occupancy, after_occupancy, allow_unsynced=allow_unsynced)

    def apply_submitted_move(self, uci: str, occupancy: Mapping[str, bool]) -> None:
        move = chess.Move.from_uci(uci)
        self.board.push(move)
        self.last_move = uci
        self.last_occupancy = self.expected_occupancy()
        self.display_board = None

    def copied_last_move_matches(self, occupancy: Mapping[str, bool]) -> bool:
        if not self.last_move or not self.board.move_stack:
            return False
        expected_after = self.expected_occupancy()
        if self.last_occupancy is not None and all(
            bool(self.last_occupancy.get(square, False)) == expected_after[square]
            for square in chess.SQUARE_NAMES
        ):
            return False
        previous = self.board.copy()
        try:
            move = previous.pop()
        except IndexError:
            return False
        expected_before = expected_occupancy_from_board(previous)
        required = {
            square
            for square in chess.SQUARE_NAMES
            if expected_before[square] != expected_after[square]
        }
        required.add(chess.square_name(move.from_square))
        required.add(chess.square_name(move.to_square))
        return all(bool(occupancy.get(square, False)) == expected_after[square] for square in required)

    def load_puzzle(self, payload: Mapping[str, Any]) -> None:
        game = payload.get("game", {})
        puzzle = payload.get("puzzle", {})
        self.board = board_from_pgn(game.get("pgn", ""))
        self.game_id = game.get("id")
        self.players = _players_from_puzzle_game(game)
        self.clock = {"whiteMs": None, "blackMs": None}
        self.mode = "puzzle"
        self.status = "puzzle_setup"
        self.last_move = None
        self.last_occupancy = None
        self.display_board = None
        self.set_player_color(
            "white" if self.board.turn == chess.WHITE else "black",
            "puzzle side to move after PGN",
        )
        self.draw_offer = None
        self.winner = None
        self.puzzle_solution = list(puzzle.get("solution", []))
        self.puzzle_index = 0
        self.puzzle = {
            "id": puzzle.get("id"),
            "rating": puzzle.get("rating"),
            "themes": list(puzzle.get("themes", [])),
            "plays": puzzle.get("plays"),
            "initialPly": puzzle.get("initialPly"),
            "status": self.status,
            "solutionIndex": self.puzzle_index,
            "solutionLength": len(self.puzzle_solution),
        }

    def start_puzzle(self, occupancy: Mapping[str, bool]) -> None:
        if self.mode != "puzzle" or not self.puzzle:
            raise ValueError("No puzzle is loaded")
        self.status = "puzzle_play"
        self.mark_synced(occupancy)
        self._update_puzzle_public_fields()

    def set_player_color(self, color: str | None, reason: str | None = None) -> None:
        self.player_color = color if color in {"white", "black"} else None
        self.player_color_reason = reason if self.player_color else None

    def submit_puzzle_move(
        self,
        after_occupancy: Mapping[str, bool],
        allow_unsynced: bool = False,
    ) -> dict[str, Any]:
        if self.mode != "puzzle" or not self.puzzle:
            return {"accepted": False, "message": "No puzzle is loaded"}
        if self.status == "puzzle_complete":
            if self.sync_status(after_occupancy)["matches"]:
                self.mark_synced(after_occupancy)
                return {
                    "accepted": False,
                    "kind": "synced",
                    "message": "Board synced. Puzzle is complete.",
                }
            return {"accepted": False, "message": "Puzzle is already complete"}
        if self.last_occupancy is None:
            return {"accepted": False, "message": "Start the puzzle first"}

        if self.sync_status(after_occupancy)["matches"]:
            self.mark_synced(after_occupancy)
            return {
                "accepted": False,
                "kind": "synced",
                "message": "Board synced. Play the next puzzle move.",
            }

        result = self.detect_move_from_last_snapshot(after_occupancy, allow_unsynced=allow_unsynced)
        if result.kind != "move" or not result.uci:
            return {"accepted": False, "kind": result.kind, "message": result.reason or "Move is not ready"}

        expected = self._next_solution_move()
        if result.uci != expected:
            return {
                "accepted": False,
                "move": result.uci,
                "expected": expected,
                "message": "That is not the puzzle move",
            }

        self.board.push(chess.Move.from_uci(result.uci))
        self.last_move = result.uci
        self.last_occupancy = dict(after_occupancy)
        self.puzzle_index += 1
        self.display_board = None
        reply = None
        if self.puzzle_index < len(self.puzzle_solution):
            reply = self.puzzle_solution[self.puzzle_index]
            self.display_board = self.board.copy()
            self.board.push(chess.Move.from_uci(reply))
            self.last_move = reply
            self.puzzle_index += 1
        self.status = "puzzle_complete" if self.puzzle_index >= len(self.puzzle_solution) else "puzzle_play"
        self._update_puzzle_public_fields()
        return {
            "accepted": True,
            "move": result.uci,
            "reply": reply,
            "complete": self.status == "puzzle_complete",
            "game": self.public_state(),
        }

    def auto_mark_synced(self) -> bool:
        return self.mode == "puzzle" and self.status in {"puzzle_play", "puzzle_complete"}

    def public_state(self) -> dict[str, Any]:
        return {
            "id": self.game_id,
            "fen": self.board.fen(),
            "mode": self.status if self.mode == "puzzle" else self.mode,
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "status": self.status,
            "lastMove": self.last_move,
            "clock": self.clock,
            "players": self.players,
            "playerColor": self.player_color,
            "drawOffer": self.draw_offer,
            "winner": self.winner,
            "pieces": piece_map(self.display_board or self.board),
            "puzzle": self._public_puzzle(),
            "debug": self.debug_state(),
        }

    def debug_state(self) -> dict[str, Any]:
        return {
            "playerColor": self.player_color,
            "playerColorReason": self.player_color_reason,
            "turn": "white" if self.board.turn == chess.WHITE else "black",
            "lastMove": self.last_move,
            "winner": self.winner,
            "fen": self.board.fen(),
            "lastOccupancyCount": sum(1 for occupied in (self.last_occupancy or {}).values() if occupied),
        }

    def _next_solution_move(self) -> str | None:
        if self.puzzle_index >= len(self.puzzle_solution):
            return None
        return self.puzzle_solution[self.puzzle_index]

    def _update_puzzle_public_fields(self) -> None:
        if not self.puzzle:
            return
        self.puzzle["status"] = self.status.replace("puzzle_", "")
        self.puzzle["solutionIndex"] = self.puzzle_index
        self.puzzle["solutionLength"] = len(self.puzzle_solution)

    def _public_puzzle(self) -> dict[str, Any] | None:
        if not self.puzzle:
            return None
        self._update_puzzle_public_fields()
        public = dict(self.puzzle)
        if self.puzzle_index < len(self.puzzle_solution):
            public["nextMoveNumber"] = self.puzzle_index + 1
        return public


def _player_public(player: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": player.get("name") or player.get("user", {}).get("name"),
        "rating": player.get("rating"),
    }


def board_from_pgn(pgn_text: str) -> chess.Board:
    game = chess.pgn.read_game(io.StringIO(pgn_text or ""))
    board = chess.Board()
    if not game:
        return board
    for move in game.mainline_moves():
        board.push(move)
    return board


def piece_map(board: chess.Board) -> dict[str, str]:
    return {
        chess.square_name(square): piece.symbol()
        for square, piece in board.piece_map().items()
    }


def _players_from_puzzle_game(game: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    players = {
        "white": {"name": None, "rating": None},
        "black": {"name": None, "rating": None},
    }
    for player in game.get("players", []) or []:
        color = player.get("color")
        if color in players:
            players[color] = _player_public(player)
    return players


def _winner_from_state(state: Mapping[str, Any]) -> str | None:
    winner = state.get("winner")
    return winner if winner in {"white", "black"} else None


def _draw_offer_from_state(state: Mapping[str, Any]) -> str | None:
    if state.get("wdraw"):
        return "white"
    if state.get("bdraw"):
        return "black"
    return None
