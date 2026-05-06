import argparse

from light_all_leds import import_circuitpython_board, parse_color


def corner_led(row, col):
    """Return LED index for a 9x9 serpentine corner grid.

    row is 0..8 from rank 1 edge toward rank 8 edge.
    col is 0..8 from h-file side toward a-file side.
    """
    if row == 0:
        physical_led = col + 1
    else:
        physical_led = row * 9 + (9 - col)
    return physical_led - 1


def build_square_leds():
    square_leds = {}
    for rank in range(1, 9):
        bottom_row = rank - 1
        top_row = rank
        for col, file_name in enumerate("hgfedcba"):
            corners = (
                corner_led(bottom_row, col),
                corner_led(bottom_row, col + 1),
                corner_led(top_row, col),
                corner_led(top_row, col + 1),
            )
            square_leds[f"{file_name}{rank}"] = tuple(sorted(corners))

    return square_leds


SQUARE_LEDS = build_square_leds()


def physical_numbers(leds):
    return tuple(led + 1 for led in leds)


def main():
    parser = argparse.ArgumentParser(description="Light the 4 corner LEDs for a chess square.")
    parser.add_argument("--count", type=int, default=81)
    parser.add_argument("--brightness", type=float, default=0.4)
    parser.add_argument("--color", type=parse_color, default=(0, 0, 120))
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

    print("Type a square like e4, or q to quit.")
    print("Each square should light 4 corner LEDs.")
    print("Checks:")
    print(f"  h1 -> indexes {SQUARE_LEDS['h1']} / physical {physical_numbers(SQUARE_LEDS['h1'])}")
    print(f"  a1 -> indexes {SQUARE_LEDS['a1']} / physical {physical_numbers(SQUARE_LEDS['a1'])}")
    print(f"  h8 -> indexes {SQUARE_LEDS['h8']} / physical {physical_numbers(SQUARE_LEDS['h8'])}")
    print(f"  a8 -> indexes {SQUARE_LEDS['a8']} / physical {physical_numbers(SQUARE_LEDS['a8'])}")

    try:
        while True:
            square = input("> ").strip().lower()
            if square == "q":
                break
            if square not in SQUARE_LEDS:
                print("Unknown square. Use a1 through h8, or q.")
                continue

            pixels.fill((0, 0, 0))
            for led in SQUARE_LEDS[square]:
                pixels[led] = args.color
            pixels.show()
            print(f"{square}: indexes {SQUARE_LEDS[square]} / physical {physical_numbers(SQUARE_LEDS[square])}")
    finally:
        pixels.fill((0, 0, 0))
        pixels.show()
        print("LEDs off.")


if __name__ == "__main__":
    main()
