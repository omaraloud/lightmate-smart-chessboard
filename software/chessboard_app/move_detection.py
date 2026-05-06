from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import chess

from chessboard_app.sensors import expected_occupancy_from_board


@dataclass(frozen=True)
class MoveDetectionResult:
    kind: str
    uci: str | None = None
    reason: str | None = None


def _same_occupancy(left: Mapping[str, bool], right: Mapping[str, bool]) -> bool:
    return all(bool(left.get(square, False)) == bool(right.get(square, False)) for square in chess.SQUARE_NAMES)


def _base_promotion_uci(move: chess.Move) -> str:
    return chess.square_name(move.from_square) + chess.square_name(move.to_square)


def _changed_squares(left: Mapping[str, bool], right: Mapping[str, bool]) -> set[str]:
    return {
        square
        for square in chess.SQUARE_NAMES
        if bool(left.get(square, False)) != bool(right.get(square, False))
    }


def _move_squares(move: chess.Move, board: chess.Board, expected_before: Mapping[str, bool], expected_after: Mapping[str, bool]) -> set[str]:
    squares = _changed_squares(expected_before, expected_after)
    squares.add(chess.square_name(move.from_square))
    squares.add(chess.square_name(move.to_square))
    return squares


def _matches_partial_move(
    board: chess.Board,
    move: chess.Move,
    before: Mapping[str, bool],
    after: Mapping[str, bool],
    expected_before: Mapping[str, bool],
    expected_after: Mapping[str, bool],
) -> bool:
    actual_changed = _changed_squares(before, after)
    expected_changed = _changed_squares(expected_before, expected_after)
    if actual_changed != expected_changed:
        return False
    for square in _move_squares(move, board, expected_before, expected_after):
        if bool(before.get(square, False)) != bool(expected_before.get(square, False)):
            return False
        if bool(after.get(square, False)) != bool(expected_after.get(square, False)):
            return False
    return True


def _required_move_squares_match(
    move: chess.Move,
    before: Mapping[str, bool],
    after: Mapping[str, bool],
    expected_before: Mapping[str, bool],
    expected_after: Mapping[str, bool],
    allow_unsynced: bool,
) -> bool:
    for square in _move_squares(move, chess.Board(), expected_before, expected_after):
        if not allow_unsynced and bool(before.get(square, False)) != bool(expected_before.get(square, False)):
            return False
        if bool(after.get(square, False)) != bool(expected_after.get(square, False)):
            return False
    return True


def _noise_count(after: Mapping[str, bool], expected_after: Mapping[str, bool]) -> int:
    return sum(
        1
        for square in chess.SQUARE_NAMES
        if bool(after.get(square, False)) != bool(expected_after.get(square, False))
    )


def _castling_rook_squares(move: chess.Move) -> tuple[str, str]:
    rank = chess.square_rank(move.from_square)
    if chess.square_file(move.to_square) > chess.square_file(move.from_square):
        return chess.square_name(chess.square(7, rank)), chess.square_name(chess.square(5, rank))
    return chess.square_name(chess.square(0, rank)), chess.square_name(chess.square(3, rank))


def _detect_castling_in_progress(
    board: chess.Board,
    before: Mapping[str, bool],
    after: Mapping[str, bool],
    expected_before: Mapping[str, bool],
) -> MoveDetectionResult | None:
    actual_changed = _changed_squares(before, after)
    for move in board.legal_moves:
        if not board.is_castling(move):
            continue
        candidate = board.copy()
        candidate.push(move)
        expected_after = expected_occupancy_from_board(candidate)
        king_squares = {
            chess.square_name(move.from_square),
            chess.square_name(move.to_square),
        }
        rook_squares = set(_castling_rook_squares(move))
        if actual_changed != rook_squares and actual_changed != king_squares:
            continue
        if any(bool(before.get(square, False)) != bool(expected_before.get(square, False)) for square in actual_changed):
            continue
        if all(bool(after.get(square, False)) == bool(expected_after.get(square, False)) for square in actual_changed):
            return MoveDetectionResult("castling_in_progress", move.uci(), "finish moving both king and rook to castle")
    return None


def _detect_dragging_move(
    board: chess.Board,
    before: Mapping[str, bool],
    after: Mapping[str, bool],
    expected_before: Mapping[str, bool],
) -> MoveDetectionResult | None:
    matching_moves: list[tuple[int, chess.Move]] = []
    promotion_bases: set[str] = set()

    for move in board.legal_moves:
        from_square = chess.square_name(move.from_square)
        to_square = chess.square_name(move.to_square)
        if not bool(expected_before.get(from_square, False)):
            continue
        if bool(expected_before.get(to_square, False)):
            continue
        if not bool(after.get(from_square, False)):
            continue
        if not bool(after.get(to_square, False)):
            continue

        expected_drag = dict(expected_before)
        expected_drag[to_square] = True
        if not _same_occupancy(before, expected_before):
            continue
        if move.promotion:
            promotion_bases.add(_base_promotion_uci(move))
            continue
        matching_moves.append((_noise_count(after, expected_drag), move))

    if matching_moves:
        best_score = min(score for score, _move in matching_moves)
        best_moves = [move for score, move in matching_moves if score == best_score]
        if len(best_moves) == 1:
            return MoveDetectionResult("dragging", best_moves[0].uci(), "destination reached; clear the source square to finish")
        return MoveDetectionResult("ambiguous", reason="multiple dragged moves fit the occupancy")
    if len(promotion_bases) == 1:
        return MoveDetectionResult("promotion_required", next(iter(promotion_bases)), "dragging")
    if len(promotion_bases) > 1:
        return MoveDetectionResult("ambiguous", reason="multiple dragged promotion moves fit the occupancy")
    return None


def _detect_tolerant_move(
    board: chess.Board,
    before: Mapping[str, bool],
    after: Mapping[str, bool],
    expected_before: Mapping[str, bool],
    allow_unsynced: bool,
) -> MoveDetectionResult:
    matching_moves: list[tuple[int, chess.Move]] = []
    promotion_bases: set[str] = set()

    for move in board.legal_moves:
        candidate = board.copy()
        candidate.push(move)
        candidate_after = expected_occupancy_from_board(candidate)
        if not _required_move_squares_match(move, before, after, expected_before, candidate_after, allow_unsynced):
            continue
        if move.promotion:
            promotion_bases.add(_base_promotion_uci(move))
            continue
        matching_moves.append((_noise_count(after, candidate_after), move))

    if matching_moves:
        best_score = min(score for score, _move in matching_moves)
        best_moves = [move for score, move in matching_moves if score == best_score]
        if len(best_moves) == 1:
            return MoveDetectionResult("move", best_moves[0].uci(), "tolerant")
        return MoveDetectionResult("ambiguous", reason="multiple legal moves fit the noisy occupancy")
    if len(promotion_bases) == 1:
        return MoveDetectionResult("promotion_required", next(iter(promotion_bases)), "tolerant")
    if len(promotion_bases) > 1:
        return MoveDetectionResult("ambiguous", reason="multiple promotion moves fit the noisy occupancy")
    return MoveDetectionResult("illegal", reason="no legal move matches the occupancy change")


def detect_move(
    board: chess.Board,
    before: Mapping[str, bool],
    after: Mapping[str, bool],
    allow_unsynced: bool = False,
) -> MoveDetectionResult:
    expected_before = expected_occupancy_from_board(board)
    synced_before = _same_occupancy(before, expected_before)
    if not synced_before and not allow_unsynced:
        return MoveDetectionResult("sync_required", reason="before snapshot does not match game position")

    castling_in_progress = _detect_castling_in_progress(board, before, after, expected_before)
    if castling_in_progress is not None:
        return castling_in_progress

    matching_moves = []
    promotion_bases = set()

    for move in board.legal_moves:
        candidate = board.copy()
        candidate.push(move)
        candidate_after = expected_occupancy_from_board(candidate)
        matches = (
            _same_occupancy(after, candidate_after)
            if synced_before
            else _matches_partial_move(board, move, before, after, expected_before, candidate_after)
        )
        if matches:
            if move.promotion:
                promotion_bases.add(_base_promotion_uci(move))
            else:
                matching_moves.append(move)

    if len(matching_moves) == 1:
        return MoveDetectionResult("move", matching_moves[0].uci())
    if len(matching_moves) > 1:
        return MoveDetectionResult("ambiguous", reason="multiple legal moves match the same occupancy")
    if len(promotion_bases) == 1:
        return MoveDetectionResult("promotion_required", next(iter(promotion_bases)))
    if len(promotion_bases) > 1:
        return MoveDetectionResult("ambiguous", reason="multiple promotion moves match the same occupancy")
    tolerant = _detect_tolerant_move(board, before, after, expected_before, allow_unsynced)
    if tolerant.kind != "illegal":
        return tolerant
    dragging = _detect_dragging_move(board, before, after, expected_before)
    if dragging is not None:
        return dragging
    return tolerant
