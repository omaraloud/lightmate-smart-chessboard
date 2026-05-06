# Lichess Physical Puzzle Flow Spec

## Goal
Add a full puzzle mode for the physical board: fetch a Lichess puzzle, show the exact puzzle position on the screen, let the user place the pieces, then start the puzzle and validate physical moves against the Lichess solution.

## User Flow
1. User opens `Tactics`.
2. User chooses `New Puzzle` or `Daily Puzzle`.
3. The Pi fetches the puzzle JSON from Lichess.
4. The kiosk shows a virtual chess board with the puzzle position, rating/themes, and physical sync status.
5. The user places pieces on the physical board to match the displayed position.
6. When ready, the user selects `Start Puzzle`.
7. The Pi marks the current sensor snapshot as the baseline for move detection.
8. The user physically plays the next puzzle move.
9. The user selects `Submit Puzzle Move`.
10. If the move matches the next solution move, the app applies it.
11. If Lichess solution has an opponent reply next, the app applies that reply and lights the from/to squares so the user can copy it on the board.
12. When all solution moves are complete, the screen shows the puzzle as solved.

## Scope
- This is a local puzzle trainer after fetching the Lichess puzzle. It does not need to submit puzzle results back to Lichess in this pass.
- The screen must work with the five external buttons.
- The virtual board must show pieces from the puzzle position, not sensor occupancy dots.
- Existing LED move highlighting should be reused for opponent replies.

## Data Model
- Add puzzle state to `GameSession`: puzzle id, rating, themes, solution moves, current solution index, active/started/completed status.
- Use python-chess to convert puzzle PGN into a board position.
- Keep `last_occupancy` as the physical baseline once setup is started.

## Endpoints
- `POST /api/puzzles/next` fetches and loads a new puzzle into session.
- `POST /api/puzzles/daily` fetches and loads daily puzzle into session.
- `POST /api/puzzle/start` marks the current physical snapshot as the puzzle baseline.
- `POST /api/puzzle/submit-physical` detects a physical move, checks it against the next solution move, and advances puzzle state.

## Acceptance Criteria
- Fetching a puzzle updates public state with puzzle id/rating/themes, board FEN, piece map, and sync status.
- Kiosk Tactics screen has puzzle fetch actions.
- Puzzle screen has `Start Puzzle`, `Submit Puzzle Move`, `Refresh Puzzle`, and `Back` actions.
- Starting a puzzle stores the current sensor snapshot.
- A correct physical move advances the solution.
- A wrong physical move is rejected with a clear message and does not advance.
- An opponent reply is applied and highlighted with the existing LED move mode.
- Completed puzzle state is visible on screen.
