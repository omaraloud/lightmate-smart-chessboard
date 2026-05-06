from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import secrets
from typing import Any
from urllib import parse, request as urllib_request
from urllib.error import HTTPError

from .lichess_scopes import lichess_scope_string


@dataclass(frozen=True)
class OAuthSession:
    state: str
    code_verifier: str
    redirect_uri: str


class FormResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        import json

        return json.loads(self.text)


class FormTransport:
    def request(self, method: str, url: str, **kwargs: Any):
        data = kwargs.get("data")
        encoded = None
        headers = kwargs.get("headers", {})
        if data is not None:
            encoded = parse.urlencode(data).encode("utf-8")
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                **headers,
            }
        req = urllib_request.Request(url, data=encoded, method=method, headers=headers)
        try:
            response = urllib_request.urlopen(req, timeout=kwargs.get("timeout", 10))
        except HTTPError as exc:
            return FormResponse(exc.code, exc.read().decode("utf-8"))
        return FormResponse(response.status, response.read().decode("utf-8"))


class LichessOAuth:
    def __init__(
        self,
        client_id: str = "physical-chessboard",
        transport: Any | None = None,
        base_url: str = "https://lichess.org",
    ):
        self.client_id = client_id
        self.transport = transport or FormTransport()
        self.base_url = base_url.rstrip("/")

    def start(self, redirect_uri: str) -> tuple[OAuthSession, str]:
        code_verifier = _token()
        state = _token()
        session = OAuthSession(
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
        )
        query = parse.urlencode({
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "code_challenge_method": "S256",
            "code_challenge": _code_challenge(code_verifier),
            "scope": lichess_scope_string(),
            "state": state,
        })
        return session, f"{self.base_url}/oauth?{query}"

    def finish(self, session: OAuthSession, code: str) -> str:
        response = self.transport.request(
            "POST",
            f"{self.base_url}/api/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": session.code_verifier,
                "redirect_uri": session.redirect_uri,
                "client_id": self.client_id,
            },
            timeout=10,
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(f"Lichess OAuth token exchange failed: {response.status_code} {response.text}")
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Lichess OAuth response did not include access_token")
        return token


def _token() -> str:
    return secrets.token_urlsafe(48)


def _code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
