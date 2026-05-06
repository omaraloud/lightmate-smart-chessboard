#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time

from chessboard_app.leds import DotStarLedController, LedSettings
from chessboard_app.orientation import orient_square
from chessboard_app.sensors import McpSensorReader
from led_mapping import SQUARE_TO_LED


def parse_color(value: str) -> tuple[int, int, int]:
    parts = value.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("color must be R,G,B tuple used by the LED driver, like 180,100,150")
    try:
        channels = tuple(int(part.strip()) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("color channels must be integers") from exc
    if any(channel < 0 or channel > 255 for channel in channels):
        raise argparse.ArgumentTypeError("color channels must be between 0 and 255")
    return channels


def active_squares(snapshot: dict[str, bool], orientation: str) -> list[str]:
    squares = [square for square, active in snapshot.items() if active]
    if orientation == "black":
        return [orient_square(square, "black") for square in squares]
    return squares


def main() -> None:
    parser = argparse.ArgumentParser(description="Light each square whose hall sensor sees a magnet.")
    parser.add_argument("--brightness", type=float, default=0.1, help="DotStar brightness, 0.0 to 1.0.")
    parser.add_argument("--color", type=parse_color, default=(180, 100, 150), help="LED color tuple. Default is the white confirmation color.")
    parser.add_argument("--poll-delay", type=float, default=0.03, help="Seconds between sensor reads.")
    parser.add_argument("--orientation", choices=["white", "black"], default="white", help="Rotate square names for black-side testing.")
    args = parser.parse_args()

    sensors = McpSensorReader.create()
    leds = DotStarLedController.create()
    leds.apply_settings(LedSettings(enabled=True, brightness=args.brightness, orientation=args.orientation))

    print("Sensor to LED test running.")
    print("Put a magnet on any square; its four corner LEDs should light.")
    print("Press Ctrl+C to stop and turn lights off.", flush=True)

    last_active: list[str] | None = None
    try:
        while True:
            snapshot = sensors.read().as_dict()
            active = active_squares(snapshot, args.orientation)
            pixels = getattr(leds, "pixels")
            pixels.fill((0, 0, 0))
            for square in active:
                physical_square = orient_square(square, args.orientation)
                for index in SQUARE_TO_LED.get(physical_square, []):
                    if 0 <= index < leds.count:
                        pixels[index] = args.color
            pixels.show()

            if active != last_active:
                print("Active:", ", ".join(active) if active else "none", flush=True)
                last_active = active
            time.sleep(args.poll_delay)
    except KeyboardInterrupt:
        leds.clear()
        print("\nStopped. Lights cleared.")


if __name__ == "__main__":
    main()
