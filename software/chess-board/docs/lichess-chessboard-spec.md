# Lichess Physical Chessboard Spec

Date: 2026-04-27

## Goal

Build the Raspberry Pi chessboard into a full physical Lichess board. A user should be able to connect the Pi to Wi-Fi, connect their Lichess account, start or join a game, play moves on the physical board, and see the same game state on the Pi screen.

The physical board is the source of local move input. Lichess is the source of online game truth. The screen is the user's local control panel and game display.

## Current Hardware State

- Raspberry Pi running Python.
- 64 magnetic sensors mapped through four MCP23017 expanders.
- Confirmed MCP23017 addresses:
  - U66: `0x20`
  - U67: `0x24`
  - U68: `0x22`
  - U69: `0x26`
- Full `SENSOR_MAP` exists in `sensor_mapping.py`.
- LED chain exists but only first 18 LEDs currently work reliably. LED support should be optional until the wiring issue is fixed.
- Pi screen will be attached and should show a local web app.

## Lichess Integration Requirements

Use the official Lichess Board API, not browser automation.

Required API behavior:

- Authenticate using either OAuth PKCE or a personal access token.
- Token must include `board:play`.
- Use `GET /api/stream/event` to receive incoming events and active game events.
- Use `GET /api/board/game/stream/{gameId}` to stream game state as NDJSON.
- Use `POST /api/board/game/{gameId}/move/{move}` to play moves in UCI format.
- Support challenge creation, accepting, aborting, resigning, draw offers, and game finish handling later.

Important Lichess rules:

- eBoards must use the Board API.
- Engine help must not be provided.
- Board API time controls are restricted by Lichess. Rapid, classical, and correspondence are generally supported. Blitz is only supported in specific cases such as direct challenges, AI games, or bulk pairing.
- Respect Lichess rate limits: one request at a time, and wait after HTTP `429`.

## Authentication Design

Two setup paths should be supported.

### Recommended: Login With Lichess

The local web app provides a "Connect Lichess" button.

Flow:

1. User opens the Pi web UI.
2. User clicks "Connect Lichess".
3. App starts OAuth2 PKCE flow with scope `board:play`.
4. Browser opens Lichess authorization page.
5. User approves access.
6. App receives token through local callback.
7. Token is saved securely on the Pi.
8. App calls `GET /api/account` to confirm username.

This is best for normal use because the user does not manually paste a secret token.

### Fallback: Paste Token

The settings screen also supports manual token entry.

Flow:

1. App shows a link to `https://lichess.org/account/oauth/token`.
2. User creates a personal token with `board:play`.
3. User pastes token into Pi web UI.
4. App tests token with `GET /api/account`.
5. If valid, token is saved locally.

Token storage:

- Store token server-side only.
- Never put token into frontend JavaScript bundles.
- Save to a local config file with restricted permissions, for example `0600`.
- Provide "Disconnect Lichess" to delete the token.

## Wi-Fi Setup Requirement

The device must be usable without SSH.

Recommended behavior:

1. On boot, if Wi-Fi is already connected, start the local chess UI.
2. If no network is available, start a setup hotspot.
3. Hotspot SSID: `ChessBoard-Setup`.
4. User connects phone/laptop to the hotspot.
5. Browser opens or user navigates to `http://chessboard.local` or `http://192.168.4.1`.
6. Setup page scans for Wi-Fi networks.
7. User selects SSID and enters password.
8. Pi saves credentials and tries to connect.
9. On success, hotspot shuts down and the main app starts.

Implementation options:

- Use NetworkManager through `nmcli` if available.
- Use `wpa_supplicant` only if NetworkManager is not installed.
- Use Avahi/mDNS for `chessboard.local`.

Wi-Fi UI states:

- Connected: show SSID and IP address.
- Not connected: show setup flow.
- Bad password: show retry screen.
- Weak/no signal: show visible warning.
- No internet: allow local board testing but disable Lichess game actions.

## Application Architecture

Use a local Python backend plus a browser frontend.

Recommended stack:

- Backend: Python `FastAPI` or `aiohttp`.
- Hardware service: Python modules for MCP23017 sensor reading and optional DotStar LEDs.
- Chess rules: `python-chess`.
- Lichess client: async HTTP client using `httpx` or `aiohttp`.
- Frontend: local web app served by the backend.
- Screen: Raspberry Pi launches Chromium in kiosk mode pointing to the local UI.

Process layout:

- `chessboard.service`: main backend and web server.
- `chessboard-kiosk.service`: launches browser after backend is ready.
- Optional `chessboard-wifi.service`: setup hotspot/network management.

## Backend Components

### Hardware Sensor Reader

Responsibilities:

- Initialize all four MCP23017 expanders.
- Read 64 square occupancy from `SENSOR_MAP`.
- Debounce sensor changes.
- Publish board snapshots.
- Detect piece lift/drop events.

Key output:

```python
{
    "a1": True,
    "b1": False,
    ...
}
```

### Board State Engine

Responsibilities:

- Keep local `python-chess` board synchronized with Lichess game state.
- Convert physical changes into legal UCI moves.
- Reject ambiguous or illegal physical movements.
- Handle captures, castling, en passant, and promotion.

Move detection:

- Normal move: one occupied square becomes empty, one empty square becomes occupied.
- Capture: source square becomes empty, destination remains occupied or changes through a short transition.
- Castling: king and rook both move; detect as one legal castle if changes match.
- En passant: source empty, target occupied, captured pawn square empty.
- Promotion: require UI selection before sending move, for example `e7e8q`.

The engine must compare candidate physical changes against legal moves from the current Lichess position. Do not infer moves only from raw sensor order.

### Lichess Client

Responsibilities:

- Authenticate requests with bearer token.
- Stream account/game events.
- Stream active game state with NDJSON.
- Send physical moves to Lichess.
- Update local state from Lichess after every event.
- Back off on errors and rate limits.

Important principle:

Lichess wins if local state disagrees. The board should show "sync needed" and guide the user to fix the pieces.

### Game Session Manager

Responsibilities:

- Track current game id.
- Track player color.
- Track whose turn it is.
- Track clocks.
- Track opponent name/rating.
- Track last move.
- Track game result.
- Expose state to frontend through WebSocket or Server-Sent Events.

### Config Manager

Responsibilities:

- Store Lichess token.
- Store device name.
- Store board orientation.
- Store Wi-Fi setup status if needed.
- Store LED enable/disable flag.
- Store screen theme preferences.

## Frontend Requirements

The Pi screen should look and feel familiar to a Lichess player, but it should be a local app, not an embedded Lichess page.

Main screens:

- Setup
- Connect Wi-Fi
- Connect Lichess
- Home
- Active Game
- Board Calibration/Diagnostics
- Settings

### Active Game Screen

Must show:

- Digital chessboard with current position.
- Player names and ratings.
- Clocks.
- Whose turn it is.
- Last move.
- Move status: waiting, legal move detected, sending move, move accepted, illegal move.
- Connection status.
- Sync status between physical board and Lichess.

Controls:

- Resign.
- Offer/accept/decline draw.
- Abort game if available.
- Flip board.
- Reconnect.
- Return to home.

Avoid analysis tools, engine evaluation, suggested moves, or anything that could violate fair play.

### Home Screen

Must show:

- Connected Lichess user.
- Current/ongoing games.
- Incoming challenges.
- Start game options:
  - Challenge username.
  - Challenge AI if supported by Board API flow.
  - Create seek, if desired.
- Hardware status:
  - Sensors OK.
  - LEDs disabled/partial/OK.
  - Internet OK.

### Diagnostics Screen

Must show:

- Live 8x8 sensor occupancy grid.
- Square names.
- Raw chip/pin values.
- Sensor map validation.
- LED test controls when LED wiring is fixed.

## Physical Move UX

When it is the user's turn:

1. User lifts a piece.
2. UI highlights source square.
3. User places it on destination.
4. Backend validates candidate move against `python-chess`.
5. If promotion, UI asks for queen/rook/bishop/knight.
6. Backend sends UCI move to Lichess.
7. UI shows "sending".
8. Lichess stream confirms move.
9. UI updates clocks and board.

When opponent moves:

1. Lichess stream receives opponent move.
2. UI updates digital board.
3. Physical board enters "please move opponent piece" mode.
4. User moves opponent piece physically.
5. Sensors confirm physical board matches Lichess.
6. Game returns to normal.

If physical board does not match:

- Show exact squares that are wrong.
- Do not send any moves.
- Keep reading sensors until the physical board matches expected occupancy.

## Data Model

### App State

```json
{
  "network": {
    "connected": true,
    "ssid": "HomeWiFi",
    "internet": true
  },
  "lichess": {
    "connected": true,
    "username": "example"
  },
  "hardware": {
    "sensors": "ok",
    "leds": "disabled"
  },
  "game": {
    "id": "abc123",
    "color": "white",
    "fen": "startpos",
    "turn": "white",
    "clock": {
      "whiteMs": 300000,
      "blackMs": 300000
    }
  }
}
```

### Physical Board Snapshot

```json
{
  "a8": true,
  "b8": true,
  "c8": true,
  "d8": true,
  "e8": true,
  "f8": true,
  "g8": true,
  "h8": true
}
```

### Move Candidate

```json
{
  "from": "e2",
  "to": "e4",
  "promotion": null,
  "uci": "e2e4"
}
```

## Local API

Backend endpoints:

- `GET /` serves frontend.
- `GET /api/state` returns app state.
- `GET /api/sensors` returns raw and mapped sensor state.
- `POST /api/lichess/token` saves manual token.
- `POST /api/lichess/logout` deletes token.
- `GET /auth/lichess/start` starts OAuth PKCE.
- `GET /auth/lichess/callback` completes OAuth PKCE.
- `GET /api/games` returns active games.
- `POST /api/challenge` creates challenge.
- `POST /api/game/{gameId}/resign` resigns.
- `POST /api/game/{gameId}/abort` aborts.
- `POST /api/game/{gameId}/draw/{accept}` handles draw.
- `GET /events` streams local app events to frontend.
- `POST /api/wifi/connect` saves Wi-Fi credentials and connects.
- `GET /api/wifi/status` returns Wi-Fi status.
- `GET /api/wifi/scan` returns visible networks.

## Error Handling

### Sensor Errors

- Missing expander: show chip name and I2C address.
- Duplicate sensor map: fail startup.
- Sensor bouncing: debounce and ignore unstable events.
- Impossible board state: show sync screen.

### Lichess Errors

- Invalid token: disconnect account and ask user to reconnect.
- Missing `board:play`: explain needed permission.
- Network down: keep local UI running.
- Stream disconnected: reconnect with backoff.
- HTTP `429`: wait at least one minute before retrying API requests.
- Move rejected: reload game state and ask user to restore physical board.

### Wi-Fi Errors

- Wrong password: retry form.
- No networks found: manual SSID entry.
- Connected without internet: show local-only mode.

## Security

- Tokens are secrets.
- Never print tokens in logs.
- Never send token to browser except through opaque "connected" state.
- Store tokens in server-side config with restricted permissions.
- Local web UI should bind to localhost during normal kiosk mode.
- During setup hotspot, expose only setup routes until Wi-Fi is configured.
- Provide token revoke/delete instructions.

## Testing Plan

### Unit Tests

- Sensor map has 64 unique chip/pin assignments.
- Board snapshot conversion works.
- Legal move detection for:
  - normal moves
  - captures
  - castling
  - en passant
  - promotion
- Illegal physical move is rejected.
- Lichess NDJSON parser handles gameFull, gameState, chatLine, and gameFinish events.
- Token validation handles good/bad/missing scopes.

### Hardware Tests

- Read all 64 sensors live.
- Confirm starting chess position occupancy.
- Confirm every square toggles correctly.
- Confirm two-square move detection.
- Confirm capture transitions.
- Confirm I2C reconnect behavior after transient failure.

### Integration Tests

- Use mocked Lichess streams first.
- Send a legal physical move and verify correct UCI request.
- Simulate opponent move and verify physical sync prompt.
- Simulate network loss and recovery.
- Simulate token revoked mid-game.

### Manual Acceptance Tests

- Fresh Pi boots to setup if no Wi-Fi.
- User connects Wi-Fi from screen.
- User connects Lichess account.
- User starts or joins a game.
- User plays `e2e4` physically and it appears on Lichess.
- Opponent move appears on Pi screen.
- User updates physical board and sync clears.
- Clock display updates.
- Game finish displays result.

## Implementation Phases

### Phase 1: Stabilize Current Code

- Keep calibration scripts.
- Keep `sensor_mapping.py` as source of truth.
- Rename old experimental game loop into a hardware test/demo only.
- Add a proper package structure.
- Add config file handling.

### Phase 2: Sensor Runtime

- Build MCP23017 reader using `SENSOR_MAP`.
- Add debounce.
- Add live snapshot API.
- Add diagnostics screen.
- Prove all 64 sensors are stable.

### Phase 3: Local Game Engine

- Add `python-chess` board state service.
- Detect moves from sensor transitions.
- Add special move handling.
- Add board sync validation.
- Run local-only games without Lichess.

### Phase 4: Lichess Client

- Add token validation.
- Add Board API event stream.
- Add game stream.
- Add move sending.
- Add reconnect/backoff.
- Add current game selection.

### Phase 5: Frontend/Kiosk

- Build local web UI.
- Add game screen with board, clocks, status, and controls.
- Add settings and diagnostics.
- Add kiosk startup service.

### Phase 6: Wi-Fi Setup

- Add Wi-Fi status detection.
- Add setup hotspot mode.
- Add scan/connect UI.
- Add `chessboard.local`.
- Add boot behavior.

### Phase 7: End-to-End Play

- Play full Lichess game using physical board.
- Handle opponent move synchronization.
- Test disconnections.
- Test invalid physical moves.
- Test game finish states.

### Phase 8: LEDs

- Keep LEDs disabled by default until hardware chain is fixed.
- Once fixed, use `LED_GRID` to highlight:
  - selected source
  - legal destinations
  - opponent move target
  - sync errors

## Open Questions

- What exact screen size/resolution will be attached to the Pi?
- Should the board support only one logged-in user, or multiple saved profiles?
- Should the app support creating seeks, or only direct challenges and ongoing games first?
- Should the physical board orientation be fixed, or should it flip automatically based on player color?
- Should Wi-Fi setup use NetworkManager, or is the Pi image currently using only `wpa_supplicant`?

## Recommended MVP

Build the first usable version with this scope:

- Wi-Fi already configured manually.
- Manual Lichess token paste with `board:play`.
- One logged-in user.
- Show active games.
- Join/select one active game.
- Read all 64 sensors.
- Send legal physical moves to Lichess.
- Show opponent moves and ask user to update the board.
- Show clocks and game result.
- No LEDs until wiring is repaired.
- Add OAuth and Wi-Fi setup after the core game loop is reliable.
