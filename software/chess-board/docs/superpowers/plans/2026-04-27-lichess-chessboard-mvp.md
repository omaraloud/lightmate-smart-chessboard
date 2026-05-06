# Lichess Chessboard MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable local service for the physical chessboard: config, sensor snapshots, move detection, Lichess token validation boundary, and a local web/API shell.

**Architecture:** Keep hardware, chess rules, Lichess API, config, and web service in separate Python modules under `chessboard_app`. Hardware modules expose pure interfaces that can be tested without Raspberry Pi libraries, while Pi-specific imports stay inside runtime constructors.

**Tech Stack:** Python 3, `python-chess`, optional FastAPI/uvicorn for the web service, Adafruit Blinka/MCP23017 for hardware runtime.

---

## File Structure

- `chessboard_app/__init__.py`: package marker.
- `chessboard_app/config.py`: server-side config and token storage.
- `chessboard_app/sensors.py`: sensor snapshot interfaces, MCP runtime reader, sync helpers.
- `chessboard_app/move_detection.py`: physical occupancy changes to legal UCI moves.
- `chessboard_app/lichess_client.py`: token validation and Board API request boundary.
- `chessboard_app/server.py`: local API and minimal UI shell.
- `run_server.py`: app entrypoint.
- `test_config.py`: config tests.
- `test_sensors.py`: sensor helper tests.
- `test_move_detection.py`: chess move detection tests.
- `test_lichess_client.py`: Lichess client tests with fake HTTP transport.

## Tasks

### Task 1: Config Storage

- [x] Add failing tests in `test_config.py` for saving/loading/deleting a token without exposing it in public state.
- [x] Implement `chessboard_app/config.py` with JSON config file storage and `0600` permissions.
- [x] Run `python3 -m unittest test_config.py`.

### Task 2: Sensor Runtime Helpers

- [x] Add failing tests in `test_sensors.py` for complete snapshots and board mismatch reporting.
- [x] Implement `chessboard_app/sensors.py` with a testable `SensorSnapshot`, `expected_occupancy_from_board`, and `diff_occupancy`.
- [x] Keep Adafruit imports inside `McpSensorReader.create()` only.
- [x] Run `python3 -m unittest test_sensors.py test_sensor_mapping.py`.

### Task 3: Move Detection

- [x] Add failing tests in `test_move_detection.py` for normal move, capture, castling, en passant, promotion-needed, and illegal transitions.
- [x] Implement `chessboard_app/move_detection.py` using `python-chess` legal move comparison.
- [x] Run `python3 -m unittest test_move_detection.py`.

### Task 4: Lichess Client Boundary

- [x] Add failing tests in `test_lichess_client.py` for auth headers, token validation, and move request paths.
- [x] Implement `chessboard_app/lichess_client.py` with injected HTTP transport.
- [x] Run `python3 -m unittest test_lichess_client.py`.

### Task 5: Local API Shell

- [x] Implement `chessboard_app/server.py` with `/api/state`, `/api/sensors`, `/api/lichess/token`, `/api/lichess/logout`, and `/`.
- [x] Implement `run_server.py`.
- [x] Make FastAPI optional at import time so non-Pi unit tests still run.
- [x] Run `python3 -m py_compile chessboard_app/*.py run_server.py`.

### Task 6: Verification

- [x] Run all unit tests with `python3 -m unittest`.
- [x] Run compile check for all project Python files.
- [ ] Report remaining hardware-only steps clearly.
