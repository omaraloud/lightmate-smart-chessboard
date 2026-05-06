import chess


# Physical LED corner grid, stored as zero-based DotStar indexes.
# Rows are the board's corner rows from rank 8 edge down to rank 1 edge.
# Columns are from a-file edge through h-file edge plus the h-side border.
LED_GRID = [
    [72, 73, 74, 75, 76, 77, 78, 79, 80],
    [63, 64, 65, 66, 67, 68, 69, 70, 71],
    [54, 55, 56, 57, 58, 59, 60, 61, 62],
    [45, 46, 47, 48, 49, 50, 51, 52, 53],
    [36, 37, 38, 39, 40, 41, 42, 43, 44],
    [27, 28, 29, 30, 31, 32, 33, 34, 35],
    [18, 19, 20, 21, 22, 23, 24, 25, 26],
    [9, 10, 11, 12, 13, 14, 15, 16, 17],
    [8, 7, 6, 5, 4, 3, 2, 1, 0],
]


def build_square_to_led_corners(led_grid):
    """
    Return {'a1': [top-right, top-left, bottom-left, bottom-right], ...}.

    led_grid is a 9x9 grid of physical LED indices, written from the board's
    top-left corner to bottom-right corner.
    """
    if len(led_grid) != 9 or any(len(row) != 9 for row in led_grid):
        raise ValueError("led_grid must be 9 rows by 9 columns")

    square_to_led = {}
    for rank in range(1, 9):
        top_row = 8 - rank
        bottom_row = top_row + 1
        for file_index, file_name in enumerate("abcdefgh"):
            square = f"{file_name}{rank}"
            square_to_led[square] = [
                led_grid[top_row][file_index + 1],
                led_grid[top_row][file_index],
                led_grid[bottom_row][file_index],
                led_grid[bottom_row][file_index + 1],
            ]
    return square_to_led


def build_square_to_led(led_grid):
    return {
        square: sorted(corners)
        for square, corners in build_square_to_led_corners(led_grid).items()
    }


SQUARE_TO_LED_CORNERS = build_square_to_led_corners(LED_GRID)
SQUARE_TO_LED = {
    square: sorted(corners)
    for square, corners in SQUARE_TO_LED_CORNERS.items()
}
ALL_SQUARES = [chess.square_name(index) for index in chess.SQUARES]
SQ_TO_IDX = {square: chess.parse_square(square) for square in ALL_SQUARES}
