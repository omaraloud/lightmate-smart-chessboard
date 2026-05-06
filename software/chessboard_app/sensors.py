from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import chess

from sensor_mapping import CHIP_ADDRESSES, SENSOR_MAP, square_names


@dataclass(frozen=True)
class SensorSnapshot:
    occupancy: Mapping[str, bool]

    def __post_init__(self) -> None:
        expected = set(square_names())
        actual = set(self.occupancy)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(f"sensor snapshot must contain all squares: missing={missing}, extra={extra}")

    def as_dict(self) -> dict[str, bool]:
        return {square: bool(self.occupancy[square]) for square in square_names()}


def expected_occupancy_from_board(board: chess.Board) -> dict[str, bool]:
    return {
        square_name: board.piece_at(chess.parse_square(square_name)) is not None
        for square_name in square_names()
    }


def diff_occupancy(expected: Mapping[str, bool], actual: Mapping[str, bool]) -> dict[str, object]:
    missing = [
        square
        for square in square_names()
        if expected.get(square, False) and not actual.get(square, False)
    ]
    extra = [
        square
        for square in square_names()
        if actual.get(square, False) and not expected.get(square, False)
    ]
    return {
        "matches": not missing and not extra,
        "missing": missing,
        "extra": extra,
    }


def sensor_details(occupancy: Mapping[str, bool]) -> dict[str, dict[str, object]]:
    return {
        square: {
            "chip": SENSOR_MAP[square][0],
            "pin": SENSOR_MAP[square][1],
            "active": bool(occupancy.get(square, False)),
        }
        for square in square_names()
    }


class StaticSensorReader:
    def __init__(self, occupancy: Mapping[str, bool] | None = None):
        if occupancy is None:
            occupancy = {square: False for square in square_names()}
        self.occupancy = dict(occupancy)

    def read(self) -> SensorSnapshot:
        return SensorSnapshot(self.occupancy)

    def details(self) -> dict[str, dict[str, object]]:
        return sensor_details(self.occupancy)

    def status(self) -> str:
        return "ok"


class UnavailableSensorReader(StaticSensorReader):
    def __init__(self, error: str):
        super().__init__()
        self.error = error

    def status(self) -> str:
        return "unavailable"

    def details(self) -> dict[str, dict[str, object]]:
        details = super().details()
        for value in details.values():
            value["error"] = self.error
        return details


class McpSensorReader:
    def __init__(self, pins: Mapping[str, object]):
        self.pins = dict(pins)

    @classmethod
    def create(cls) -> McpSensorReader:
        import board as circuit_board  # type: ignore
        import busio  # type: ignore
        import digitalio  # type: ignore
        from adafruit_mcp230xx.mcp23017 import MCP23017  # type: ignore

        i2c = busio.I2C(circuit_board.SCL, circuit_board.SDA)
        chips = {
            chip_name: MCP23017(i2c, address=address)
            for chip_name, address in CHIP_ADDRESSES.items()
        }

        pins = {}
        for square, chip_pin in SENSOR_MAP.items():
            chip_name, pin_num = chip_pin
            pin = chips[chip_name].get_pin(pin_num)
            pin.direction = digitalio.Direction.INPUT
            pin.pull = digitalio.Pull.UP
            pins[square] = pin
        return cls(pins)

    def read(self) -> SensorSnapshot:
        return SensorSnapshot({
            square: pin.value is False
            for square, pin in self.pins.items()
        })

    def details(self) -> dict[str, dict[str, object]]:
        return sensor_details(self.read().as_dict())

    def status(self) -> str:
        return "ok"
