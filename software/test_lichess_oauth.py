import unittest
from urllib.parse import parse_qs, urlparse

from chessboard_app.lichess_oauth import LichessOAuth, OAuthSession


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


class LichessOAuthTest(unittest.TestCase):
    def test_start_builds_pkce_authorization_url(self):
        oauth = LichessOAuth(client_id="chessboard-test")

        session, url = oauth.start("http://pi.local/auth/lichess/callback")
        query = parse_qs(urlparse(url).query)

        self.assertEqual(urlparse(url).scheme, "https")
        self.assertEqual(urlparse(url).netloc, "lichess.org")
        self.assertEqual(urlparse(url).path, "/oauth")
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["client_id"], ["chessboard-test"])
        self.assertEqual(query["redirect_uri"], ["http://pi.local/auth/lichess/callback"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["scope"], [" ".join(FULL_LICHESS_SCOPES)])
        self.assertEqual(query["state"], [session.state])

    def test_finish_exchanges_code_for_access_token(self):
        transport = FakeTransport([FakeResponse(data={
            "token_type": "Bearer",
            "access_token": "oauth_token",
            "expires_in": 31536000,
        })])
        oauth = LichessOAuth(client_id="chessboard-test", transport=transport)
        session = OAuthSession(
            state="state1",
            code_verifier="verifier1",
            redirect_uri="http://pi.local/auth/lichess/callback",
        )

        token = oauth.finish(session, "code1")

        self.assertEqual(token, "oauth_token")
        method, url, kwargs = transport.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://lichess.org/api/token")
        self.assertEqual(kwargs["data"]["grant_type"], "authorization_code")
        self.assertEqual(kwargs["data"]["code"], "code1")
        self.assertEqual(kwargs["data"]["code_verifier"], "verifier1")
        self.assertEqual(kwargs["data"]["client_id"], "chessboard-test")


if __name__ == "__main__":
    unittest.main()
