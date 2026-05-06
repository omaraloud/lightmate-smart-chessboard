import argparse
import os
import sys
import time


def import_circuitpython_board():
    """Avoid importing this repo's board.py when we need CircuitPython's board module."""
    here = os.path.abspath(os.path.dirname(__file__))
    cwd = os.path.abspath(os.getcwd())
    sys.path = [
        path
        for path in sys.path
        if os.path.abspath(path or cwd) != here
    ]
    import board  # type: ignore

    return board


def main():
    parser = argparse.ArgumentParser(
        description="Light each DotStar LED by index so the physical board order can be recorded."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=81,
        help="Number of LEDs. Use 81 for an 8x8 board with 9x9 corner lights.",
    )
    parser.add_argument("--brightness", type=float, default=0.1)
    parser.add_argument("--delay", type=float, default=0.0, help="Auto-advance delay in seconds.")
    args = parser.parse_args()

    circuit_board = import_circuitpython_board()
    import adafruit_dotstar as dotstar  # type: ignore

    pixels = dotstar.DotStar(
        circuit_board.SCK,
        circuit_board.MOSI,
        args.count,
        brightness=args.brightness,
        auto_write=False,
    )

    index = 0
    print("DotStar LED order calibration")
    print("Write down where each lit index appears on the physical board.")
    print("For a full framed chessboard, record a 9x9 LED_GRID from top-left to bottom-right.")
    print("Controls: Enter=next, number+jump, b=back, q=quit")

    try:
        while True:
            pixels.fill((0, 0, 0))
            pixels[index] = (255, 255, 255)
            pixels.show()
            print(f"LED index {index}")

            if args.delay > 0:
                time.sleep(args.delay)
                index = (index + 1) % args.count
                continue

            command = input("> ").strip().lower()
            if command == "q":
                break
            if command == "b":
                index = (index - 1) % args.count
            elif command.isdigit():
                index = int(command) % args.count
            else:
                index = (index + 1) % args.count
    finally:
        pixels.fill((0, 0, 0))
        pixels.show()


if __name__ == "__main__":
    main()
