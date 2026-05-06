from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any
from urllib import parse

from .lichess_scopes import LICHESS_SCOPES


@dataclass
class AppConfig:
    device_name: str = "ChessBoard"
    lichess_token: str | None = None
    lichess_username: str | None = None
    board_orientation: str = "white"
    leds_enabled: bool = False
    led_brightness: float = 0.1
    test_mode: bool = False
    submit_move_enabled: bool = False


class AppConfigStore:
    def __init__(self, path: str | os.PathLike[str] | None = None):
        if path is None:
            path = Path.home() / ".config" / "chessboard" / "config.json"
        self.path = Path(path)

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        with self.path.open("r", encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)
        allowed = set(AppConfig.__dataclass_fields__)
        return AppConfig(**{key: value for key, value in data.items() if key in allowed})

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(asdict(config), file, indent=2, sort_keys=True)
            file.write("\n")
        os.chmod(tmp_path, 0o600)
        tmp_path.replace(self.path)
        os.chmod(self.path, 0o600)

    def save_lichess_token(self, token: str, username: str | None = None) -> None:
        config = self.load()
        config.lichess_token = token
        config.lichess_username = username
        self.save(config)

    def delete_lichess_token(self) -> None:
        config = self.load()
        config.lichess_token = None
        config.lichess_username = None
        self.save(config)

    def update_settings(
        self,
        *,
        leds_enabled: bool | None = None,
        board_orientation: str | None = None,
        device_name: str | None = None,
        led_brightness: float | None = None,
        test_mode: bool | None = None,
        submit_move_enabled: bool | None = None,
    ) -> AppConfig:
        config = self.load()
        if leds_enabled is not None:
            config.leds_enabled = bool(leds_enabled)
        if board_orientation is not None:
            if board_orientation not in {"white", "black"}:
                raise ValueError("board_orientation must be 'white' or 'black'")
            config.board_orientation = board_orientation
        if device_name is not None:
            cleaned = device_name.strip()
            if not cleaned:
                raise ValueError("device_name cannot be empty")
            config.device_name = cleaned
        if led_brightness is not None:
            brightness = float(led_brightness)
            if brightness < 0 or brightness > 1:
                raise ValueError("led_brightness must be between 0 and 1")
            config.led_brightness = brightness
        if test_mode is not None:
            config.test_mode = bool(test_mode)
        if submit_move_enabled is not None:
            config.submit_move_enabled = bool(submit_move_enabled)
        self.save(config)
        return config

    def public_state(self) -> dict[str, Any]:
        config = self.load()
        token_query = parse.urlencode([("scopes[]", scope) for scope in LICHESS_SCOPES])
        return {
            "deviceName": config.device_name,
            "boardOrientation": config.board_orientation,
            "ledsEnabled": config.leds_enabled,
            "ledBrightness": config.led_brightness,
            "testMode": config.test_mode,
            "submitMoveEnabled": config.submit_move_enabled,
            "lichessTokenUrl": f"https://lichess.org/account/oauth/token/create?{token_query}",
            "lichess": {
                "connected": config.lichess_token is not None,
                "username": config.lichess_username,
            },
        }
