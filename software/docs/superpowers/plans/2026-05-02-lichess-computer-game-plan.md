# Lichess Computer Game Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete first-pass Lichess AI game loop for board testing and improve LED controls.

**Architecture:** Extend the existing FastAPI backend and five-button kiosk UI. Lichess HTTP remains inside `LichessClient`; `GameSession` keeps board state and previous synced occupancy; `server.py` coordinates actions and exposes small endpoints.

**Tech Stack:** Python 3.11, FastAPI, python-chess, Lichess Board API, existing vanilla JS kiosk UI.

---

### Task 1: Lichess Client Game State

**Files:**
- Modify: `chessboard_app/lichess_client.py`
- Modify: `test_lichess_client.py`

- [ ] Add tests for `stream_game_state(game_id)` parsing ndjson lines and returning the latest game event/state.
- [ ] Add implementation using `GET /api/board/game/stream/{gameId}`.
- [ ] Verify `python3 -m unittest test_lichess_client.py`.

### Task 2: Game Session Move Submission State

**Files:**
- Modify: `chessboard_app/game_session.py`
- Modify: `test_game_session.py`

- [ ] Add `last_occupancy` storage.
- [ ] Add helpers to mark a synced physical snapshot and apply a submitted move.
- [ ] Verify move detection uses the previous synced snapshot.

### Task 3: Server Endpoints

**Files:**
- Modify: `chessboard_app/server.py`
- Modify: `test_server.py`

- [ ] Add `POST /api/play/ai` behavior that starts a Lichess AI game, stores game id/player color, fetches game state, and marks the current physical snapshot as baseline.
- [ ] Add `POST /api/game/refresh` to refresh game state from Lichess.
- [ ] Add `POST /api/game/submit-physical` to detect and submit one physical move.
- [ ] Add clear JSON results for submitted, no move, illegal move, and sync required.

### Task 4: Kiosk UI Controls

**Files:**
- Modify: `chessboard_app/server.py`
- Modify: `test_kiosk.py`

- [ ] Rename `AI 3+2` to `Play Computer`.
- [ ] Trigger refresh and current-game screen after starting the AI game.
- [ ] Add a `Submit Move` action on the Current Game screen.
- [ ] Add `Lights Off`, `Brightness Up`, and `Brightness Down` controls in LED Test and Settings.

### Task 5: Verification and Pi Deploy

**Files:**
- Deploy changed files to `/home/pi/Desktop/chess-board`.

- [ ] Run local `python3 -m unittest discover -v`.
- [ ] Copy changed files to Pi.
- [ ] Restart `chessboard.service`.
- [ ] Run Pi `python3 -m unittest discover -v`.
- [ ] Open/restart Chromium on the Pi.
