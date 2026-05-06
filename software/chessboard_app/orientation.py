from __future__ import annotations

from typing import Mapping


FILES = "abcdefgh"


def normalize_orientation(orientation: str | None) -> str:
    return "black" if orientation == "black" else "white"


def rotate_square_180(square: str) -> str:
    if len(square) != 2 or square[0] not in FILES or square[1] not in "12345678":
        raise ValueError(f"invalid chess square: {square}")
    file_name = FILES[7 - FILES.index(square[0])]
    rank_name = str(9 - int(square[1]))
    return file_name + rank_name


def orient_square(square: str, orientation: str | None) -> str:
    if normalize_orientation(orientation) == "black":
        return rotate_square_180(square)
    return square


def orient_occupancy(occupancy: Mapping[str, bool], orientation: str | None) -> dict[str, bool]:
    if normalize_orientation(orientation) != "black":
        return {square: bool(value) for square, value in occupancy.items()}
    return {
        rotate_square_180(square): bool(value)
        for square, value in occupancy.items()
    }
