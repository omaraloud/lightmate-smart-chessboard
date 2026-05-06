# Lichess Computer Game Spec

## Goal
Make the board able to start a Lichess AI game, show the live Lichess game state, accept physical moves from the hall sensors, submit those moves to Lichess, and make light controls usable after testing.

## User Flow
1. User opens `Play`.
2. User chooses `Play Computer`.
3. The Pi calls Lichess `POST /api/challenge/ai` with a casual standard game, default level 3, 3+2 clock, and random color.
4. The app stores the returned game id and updates the current `GameSession`.
5. The user goes to `Current Game`.
6. The screen shows game id, turn, clocks, last move, and board sync status.
7. If it is the user's turn, moving a physical piece from one legal position to another submits the UCI move to Lichess through `POST /api/board/game/{gameId}/move/{uci}`.
8. After submitting a move, the app refreshes the Lichess game state from the board game stream.
9. If Lichess AI moves, the board state updates and the existing LED logic can highlight the opponent move to copy.
10. In Settings and LED Test, the user can turn lights off and reduce brightness, not only increase it.

## Architecture
- `chessboard_app/lichess_client.py` remains the boundary for Lichess HTTP calls.
- `chessboard_app/game_session.py` owns game state and move detection from sensor snapshots.
- `chessboard_app/server.py` orchestrates UI actions: start AI game, refresh game state, submit detected moves, update light settings.
- The kiosk keeps using five-button navigation. No keyboard or mouse is required.

## Lichess API
Official Lichess API docs used:
- `POST /api/challenge/ai` starts a Lichess AI game and returns the game id.
- `GET /api/board/game/stream/{gameId}` streams Board API game state as ndjson. The first line is `gameFull`; later lines are `gameState`.
- `POST /api/board/game/{gameId}/move/{uci}` submits a board move in UCI format.

## Acceptance Criteria
- `Play Computer` starts a Lichess AI game and stores the game id in `GameSession`.
- The app can refresh the current Lichess game state from the board stream.
- The app can submit one legal physical move when sensors change from the previous synced snapshot.
- Duplicate/no-change snapshots do not submit moves.
- Illegal physical transitions do not submit moves and show a clear message.
- Light controls include off, brightness up, and brightness down.
- Tests cover Lichess client endpoints, server endpoints, and kiosk strings.
