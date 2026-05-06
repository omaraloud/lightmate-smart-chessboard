import os
import stat
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

from chessboard_app.config import AppConfigStore


FULL_LICHESS_SCOPES = [
    "preference:read",
    "preference:write",
    "email:read",
    "engine:read",
    "engine:write",
    "challenge:read",
    "challenge:write",
    "challenge:bulk",
    "study:read",
    "study:write",
    "tournament:write",
    "racer:write",
    "puzzle:read",
    "puzzle:write",
    "team:read",
    "team:write",
    "team:lead",
    "follow:read",
    "follow:write",
    "msg:write",
    "board:play",
    "bot:play",
]


class ConfigTest(unittest.TestCase):
    def test_token_round_trip_and_public_state_hides_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            store = AppConfigStore(path)

            store.save_lichess_token("secret_token", username="player1")
            loaded = store.load()

            self.assertEqual(loaded.lichess_token, "secret_token")
            self.assertEqual(loaded.lichess_username, "player1")
            self.assertEqual(store.public_state()["lichess"]["connected"], True)
            self.assertNotIn("secret_token", repr(store.public_state()))

    def test_saved_config_file_is_owner_read_write_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            store = AppConfigStore(path)

            store.save_lichess_token("secret_token")

            mode = stat.S_IMODE(os.stat(path).st_mode)
            self.assertEqual(mode, 0o600)

    def test_delete_token_keeps_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            store = AppConfigStore(path)
            config = store.load()
            config.device_name = "Board"
            store.save(config)
            store.save_lichess_token("secret_token", username="player1")

            store.delete_lichess_token()

            loaded = store.load()
            self.assertIsNone(loaded.lichess_token)
            self.assertIsNone(loaded.lichess_username)
            self.assertEqual(loaded.device_name, "Board")

    def test_public_state_token_url_requests_all_lichess_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            store = AppConfigStore(path)

            token_url = store.public_state()["lichessTokenUrl"]
            parsed = urlparse(token_url)
            query = parse_qs(parsed.query)

            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "lichess.org")
            self.assertEqual(parsed.path, "/account/oauth/token/create")
            self.assertEqual(query["scopes[]"], FULL_LICHESS_SCOPES)

    def test_update_settings_preserves_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            store = AppConfigStore(path)
            store.save_lichess_token("secret_token", username="player1")

            store.update_settings(leds_enabled=True, board_orientation="black", led_brightness=0.4)

            loaded = store.load()
            self.assertEqual(loaded.lichess_token, "secret_token")
            self.assertEqual(loaded.lichess_username, "player1")
            self.assertEqual(loaded.leds_enabled, True)
            self.assertEqual(loaded.led_brightness, 0.4)
            self.assertEqual(loaded.board_orientation, "black")

    def test_update_settings_rejects_invalid_orientation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            store = AppConfigStore(path)

            with self.assertRaises(ValueError):
                store.update_settings(board_orientation="sideways")

    def test_update_settings_rejects_invalid_brightness(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            store = AppConfigStore(path)

            with self.assertRaises(ValueError):
                store.update_settings(led_brightness=2.0)


if __name__ == "__main__":
    unittest.main()
