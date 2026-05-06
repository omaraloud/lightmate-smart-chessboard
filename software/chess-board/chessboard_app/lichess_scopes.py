from __future__ import annotations


LICHESS_SCOPES = (
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
)


def lichess_scope_string() -> str:
    return " ".join(LICHESS_SCOPES)
