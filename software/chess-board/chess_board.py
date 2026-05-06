import time
import random

import board
import busio
import digitalio
from adafruit_mcp230xx.mcp23017 import MCP23017
import adafruit_dotstar as dotstar
import chess

# ---------------------------------------
# 1. MCP23017 SENSOR MAPPING (16 SQUARES)
# ---------------------------------------
# c1â€“f4, top row is rank 4, bottom row is rank 1
MCP_MAP = {
    "c4": 3,  "d4": 2,  "e4": 1,  "f4": 0,
    "c3": 7,  "d3": 6,  "e3": 5,  "f3": 4,
    "c2": 8,  "d2": 9,  "e2": 10, "f2": 11,
    "c1": 12, "d1": 13, "e1": 14, "f1": 15,
}

MINI_SQUARES = list(MCP_MAP.keys())
SQ_TO_IDX = {sq: chess.parse_square(sq) for sq in MINI_SQUARES}

# ---------------------------------------
# 2. DOTSTAR LED SETUP (25 LEDs)
# ---------------------------------------
NUM_LEDS = 25
pixels = dotstar.DotStar(
    board.SCK,
    board.MOSI,
    NUM_LEDS,
    brightness=0.1,    # not too bright
    auto_write=False,
)

# âœ… YOUR VERIFIED SQUARE â†’ LED MAPPING
SQUARE_TO_LED = {
    # rank 1 (bottom row, columns 0â€“1)
    "c1": [3, 4, 5, 6],
    "d1": [2, 3, 6, 7],
    "e1": [1, 2, 7, 8],
    "f1": [0, 1, 8, 9],

    # rank 2 (columns 1â€“2)
    "c2": [6, 5, 11, 10],
    "d2": [7, 6, 11, 12],
    "e2": [8, 7, 12, 13],
    "f2": [9, 8, 13, 14],

    # rank 3 (columns 2â€“3)
    "f3": [13, 14, 18, 19],
    "e3": [12, 13, 17, 18],
    "d3": [11, 12, 16, 17],
    "c3": [10, 11, 15, 16],

    # rank 4 (top row, columns 3â€“4)
    "c4": [16, 15, 20, 21],
    "d4": [17, 16, 21, 22],
    "e4": [18, 17, 22, 23],
    "f4": [19, 18, 23, 24],
}

COLOR_OCCUPIED = (255, 255, 255)  # white
COLOR_HIGHLIGHT = (255, 255, 0)   # yellow

def clear_leds():
    pixels.fill((0, 0, 0))
    pixels.show()

def show_occupancy(occ):
    """
    Show where pieces currently are using white frames.
    occ: {'c1': True/False, ...}, True = piece present
    """
    pixels.fill((0, 0, 0))
    for sq, present in occ.items():
        if present:
            for idx in SQUARE_TO_LED.get(sq, []):
                if 0 <= idx < NUM_LEDS:
                    pixels[idx] = COLOR_OCCUPIED
    pixels.show()

def show_highlights(squares):
    """
    Highlight the legal target squares in yellow.
    """
    pixels.fill((0, 0, 0))
    for sq in squares:
        for idx in SQUARE_TO_LED.get(sq, []):
            if 0 <= idx < NUM_LEDS:
                pixels[idx] = COLOR_HIGHLIGHT
    pixels.show()

# ---------------------------------------
# 3. SETUP MCP23017 (ACTIVE-LOW SENSORS)
# ---------------------------------------
i2c = busio.I2C(board.SCL, board.SDA)
mcp = MCP23017(i2c, address=0x20)

pins = {}
for sq, pin_num in MCP_MAP.items():
    p = mcp.get_pin(pin_num)
    p.direction = digitalio.Direction.INPUT
    p.pull = digitalio.Pull.UP      # active-low: LOW = magnet present
    pins[sq] = p

def read_occupancy():
    """
    Return dict: {'c2': True, ... } where True = piece present.
    """
    return {sq: (p.value is False) for sq, p in pins.items()}

# ---------------------------------------
# 4. CHESS ENGINE
# ---------------------------------------
board_obj = chess.Board()

def legal_targets(from_sq):
    """
    Return list of legal target squares (within c1â€“f4) from from_sq.
    """
    idx = SQ_TO_IDX[from_sq]
    result = []
    for move in board_obj.legal_moves:
        if move.from_square == idx:
            name = chess.square_name(move.to_square)
            if name in MINI_SQUARES:
                result.append(name)
    return result

def computer_reply():
    """
    Computer picks a random legal move and plays it.
    """
    legal = list(board_obj.legal_moves)
    if not legal:
        print("Computer has no legal moves (checkmate / stalemate?).")
        return
    move = random.choice(legal)
    board_obj.push(move)
    print(f"Computer plays: {move.uci()}")
    print(board_obj)

# ---------------------------------------
# 5. MAIN LOOP
# ---------------------------------------
print("=== Mini Chess Board with LEDs & Computer Opponent ===")
print("Lift a single piece (one magnet) to see legal moves (LEDs + terminal).")
print("Drop it on a legal square to play your move.")
print()
print(board_obj)
print("-------------------------------------------")

last = read_occupancy()
pending_from = None

# Initial LED state: show where pieces are (whatever magnets you placed)
show_occupancy(last)

try:
    while True:
        time.sleep(0.05)
        occ = read_occupancy()

        # transitions
        picked_up = [sq for sq in MINI_SQUARES if last[sq] and not occ[sq]]
        put_down  = [sq for sq in MINI_SQUARES if not last[sq] and occ[sq]]

        # -------------------------
        # No piece currently lifted
        # -------------------------
        if pending_from is None:
            if len(picked_up) == 1:
                pending_from = picked_up[0]
                print(f"\nPiece lifted from: {pending_from}")

                targets = legal_targets(pending_from)
                print("Legal moves from", pending_from, ":", targets)

                # LEDs: show legal target squares
                show_highlights(targets)

        # -------------------------
        # One piece is lifted, waiting for drop
        # -------------------------
        else:
            if len(put_down) == 1:
                to_sq = put_down[0]

                if to_sq == pending_from:
                    print("Move canceled (piece returned).")
                else:
                    uci = pending_from + to_sq
                    print(f"Detected move: {uci}")
                    move = chess.Move.from_uci(uci)

                    if move in board_obj.legal_moves:
                        board_obj.push(move)
                        print("\n=== BOARD AFTER YOUR MOVE ===")
                        print(board_obj)

                        # Computer reply
                        computer_reply()
                    else:
                        print("âš ï¸ Illegal move (ignored).")

                # done with this move / cancel
                pending_from = None
                # back to showing piece positions
                show_occupancy(occ)

        last = occ

except KeyboardInterrupt:
    clear_leds()
    print("\nStopped.")
