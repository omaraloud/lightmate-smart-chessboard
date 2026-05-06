import unittest
from unittest.mock import patch

from chessboard_app.lichess_client import LichessClient, UrllibTransport


class FakeResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class LichessClientTest(unittest.TestCase):
    def test_validate_token_sends_bearer_auth_and_returns_username(self):
        transport = FakeTransport([FakeResponse(data={"username": "player1"})])
        client = LichessClient("secret", transport=transport)

        username = client.validate_token()

        self.assertEqual(username, "player1")
        method, url, kwargs = transport.calls[0]
        self.assertEqual(method, "GET")
        self.assertEqual(url, "https://lichess.org/api/account")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")

    def test_validate_token_rejects_bad_token(self):
        transport = FakeTransport([FakeResponse(status_code=401, text="Unauthorized")])
        client = LichessClient("bad", transport=transport)

        with self.assertRaises(PermissionError):
            client.validate_token()

    def test_urllib_transport_get_with_none_data_does_not_encode_body(self):
        class UrlopenResponse:
            status = 200

            def read(self):
                return b'{"username":"player1"}'

        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return UrlopenResponse()

        with patch("chessboard_app.lichess_client.urllib_request.urlopen", fake_urlopen):
            response = UrllibTransport().request(
                "GET",
                "https://lichess.org/api/account",
                headers={"Authorization": "Bearer secret"},
                data=None,
                timeout=3,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(captured["request"].data)
        self.assertEqual(captured["timeout"], 3)

    def test_make_move_posts_board_api_move(self):
        transport = FakeTransport([FakeResponse(data={"ok": True})])
        client = LichessClient("secret", transport=transport)

        client.make_move("game123", "e2e4")

        method, url, kwargs = transport.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://lichess.org/api/board/game/game123/move/e2e4")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")

    def test_active_games_uses_account_playing_endpoint(self):
        transport = FakeTransport([FakeResponse(data={"nowPlaying": [{"gameId": "abc"}]})])
        client = LichessClient("secret", transport=transport)

        games = client.active_games()

        self.assertEqual(games, [{"gameId": "abc"}])
        self.assertEqual(transport.calls[0][1], "https://lichess.org/api/account/playing")

    def test_game_controls_use_board_api_paths(self):
        transport = FakeTransport([FakeResponse(), FakeResponse(), FakeResponse()])
        client = LichessClient("secret", transport=transport)

        client.resign("game1")
        client.abort("game1")
        client.handle_draw("game1", accept=True)

        self.assertEqual(transport.calls[0][1], "https://lichess.org/api/board/game/game1/resign")
        self.assertEqual(transport.calls[1][1], "https://lichess.org/api/board/game/game1/abort")
        self.assertEqual(transport.calls[2][1], "https://lichess.org/api/board/game/game1/draw/yes")

    def test_can_create_friend_challenge_with_clock(self):
        transport = FakeTransport([FakeResponse(data={"challenge": {"id": "c1"}})])
        client = LichessClient("secret", transport=transport)

        result = client.challenge_friend("friend", clock_limit=180, increment=2, rated=False, color="random")

        self.assertEqual(result, {"challenge": {"id": "c1"}})
        method, url, kwargs = transport.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://lichess.org/api/challenge/friend")
        self.assertEqual(kwargs["data"]["clock.limit"], 180)
        self.assertEqual(kwargs["data"]["clock.increment"], 2)
        self.assertEqual(kwargs["data"]["rated"], "false")

    def test_can_challenge_ai(self):
        transport = FakeTransport([FakeResponse(status_code=201, data={"id": "game1"})])
        client = LichessClient("secret", transport=transport)

        result = client.challenge_ai(level=3, clock_limit=180, increment=2)

        self.assertEqual(result, {"id": "game1"})
        self.assertEqual(transport.calls[0][1], "https://lichess.org/api/challenge/ai")
        self.assertEqual(transport.calls[0][2]["data"]["level"], 3)

    def test_stream_game_state_reads_latest_ndjson_event(self):
        text = (
            '{"type":"gameFull","id":"game123","white":{"name":"me"},"black":{"name":"AI"},"state":{"moves":"","status":"started"}}\n'
            '{"type":"gameState","moves":"e2e4 e7e5","status":"started","wtime":180000,"btime":178000}\n'
        )
        transport = FakeTransport([FakeResponse(text=text)])
        client = LichessClient("secret", transport=transport)

        event = client.stream_game_state("game123")

        self.assertEqual(event["id"], "game123")
        self.assertEqual(event["white"], {"name": "me"})
        self.assertEqual(event["black"], {"name": "AI"})
        self.assertEqual(event["state"]["moves"], "e2e4 e7e5")
        self.assertEqual(transport.calls[0][0], "GET")
        self.assertEqual(transport.calls[0][1], "https://lichess.org/api/board/game/stream/game123")

    def test_can_create_seek(self):
        transport = FakeTransport([FakeResponse(data={"id": "seek1"})])
        client = LichessClient("secret", transport=transport)

        result = client.create_seek(time_minutes=3, increment=2, rated=False)

        self.assertEqual(result, {"id": "seek1"})
        self.assertEqual(transport.calls[0][1], "https://lichess.org/api/board/seek")
        self.assertEqual(transport.calls[0][2]["data"]["time"], 3)

    def test_real_time_seek_empty_stream_returns_ok(self):
        transport = FakeTransport([FakeResponse(text="")])
        client = LichessClient("secret", transport=transport)

        result = client.create_seek(time_minutes=10, increment=0, rated=False)

        self.assertEqual(result, {"ok": True})

    def test_can_create_open_challenge(self):
        transport = FakeTransport([FakeResponse(data={"url": "https://lichess.org/abc"})])
        client = LichessClient("secret", transport=transport)

        result = client.open_challenge(clock_limit=180, increment=2, name="ChessBoard")

        self.assertEqual(result, {"url": "https://lichess.org/abc"})
        self.assertEqual(transport.calls[0][1], "https://lichess.org/api/challenge/open")
        self.assertEqual(transport.calls[0][2]["data"]["name"], "ChessBoard")

    def test_can_cancel_challenge(self):
        transport = FakeTransport([FakeResponse(data={"ok": True})])
        client = LichessClient("secret", transport=transport)

        client.cancel_challenge("challenge123")

        self.assertEqual(transport.calls[0][0], "POST")
        self.assertEqual(transport.calls[0][1], "https://lichess.org/api/challenge/challenge123/cancel")

    def test_can_fetch_puzzles(self):
        transport = FakeTransport([FakeResponse(data={"puzzle": {"id": "p1"}}), FakeResponse(data={"puzzle": {"id": "daily"}})])
        client = LichessClient("secret", transport=transport)

        self.assertEqual(client.next_puzzle(), {"puzzle": {"id": "p1"}})
        self.assertEqual(client.daily_puzzle(), {"puzzle": {"id": "daily"}})
        self.assertEqual(transport.calls[0][1], "https://lichess.org/api/puzzle/next")
        self.assertEqual(transport.calls[1][1], "https://lichess.org/api/puzzle/daily")


if __name__ == "__main__":
    unittest.main()
