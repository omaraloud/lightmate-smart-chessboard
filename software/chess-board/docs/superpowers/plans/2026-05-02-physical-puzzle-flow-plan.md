# Physical Puzzle Flow Implementation Plan

## Task 1: GameSession puzzle state
- Add tests for loading a Lichess puzzle payload into a board position.
- Add tests for starting a puzzle, accepting a correct physical move, rejecting a wrong move, applying an opponent reply, and completing the puzzle.
- Implement puzzle fields and methods in `chessboard_app/game_session.py`.

## Task 2: Server state and endpoints
- Add tests for `POST /api/puzzles/next` and `POST /api/puzzle/start`/`submit-physical`.
- Include puzzle public state in `/api/state` and `/api/live-state` through `game.public_state()`.
- Implement endpoint orchestration in `chessboard_app/server.py`.

## Task 3: Kiosk UI
- Add tests for new kiosk strings and endpoint hooks.
- Render a virtual board from `game.pieces` during puzzle mode.
- Add actions: `Start Puzzle`, `Submit Puzzle Move`, `Refresh Puzzle`, `Back`.
- Keep five-button navigation.

## Task 4: Verification and deploy
- Run focused tests.
- Run full local test suite.
- Copy changed files to the Pi.
- Restart `chessboard.service`.
- Run Pi tests and verify `/api/state`.
