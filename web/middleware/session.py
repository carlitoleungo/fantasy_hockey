"""
Session middleware for the Fantasy Hockey web app.

Implemented as a FastAPI Depends dependency (require_user) rather than a
Starlette middleware class.  Routes that need authentication declare
`current_user: CurrentUser = Depends(require_user)`; public routes simply
omit it, which makes exemptions explicit and avoids path-prefix matching.

EXEMPT_PREFIXES documents which path prefixes are public — it is not
evaluated at runtime in this Depends approach, but is kept as a config
constant so adding new public routes does not require hunting through logic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests
from fastapi import Cookie, Depends

from auth.oauth import _is_valid, _try_refresh
from db.connection import db_dep

EXEMPT_PREFIXES: frozenset[str] = frozenset({"/auth/", "/demo"})


class RequiresLogin(Exception):
    """Raised by require_user when the request cannot be authenticated."""


@dataclass
class CurrentUser:
    session_id: str
    access_token: str
    expires_at: float


def require_user(
    session_id: str | None = Cookie(default=None),
    db=Depends(db_dep),
) -> CurrentUser:
    """
    FastAPI dependency: validate session cookie, refresh token if needed,
    and return a CurrentUser for the route handler.

    Raises RequiresLogin (handled in main.py as a 302 to /auth/login) when:
    - session_id cookie is absent
    - session row does not exist in the DB
    - token refresh fails (stale session row is deleted before raising)
    """
    if not session_id:
        raise RequiresLogin()

    row = db.execute(
        "SELECT session_id, access_token, refresh_token, expires_at"
        " FROM user_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()

    if row is None:
        raise RequiresLogin()

    tokens: dict = {
        "access_token": row["access_token"],
        "refresh_token": row["refresh_token"],
        "expires_at": row["expires_at"],
    }

    if not _is_valid(tokens):
        try:
            new_tokens = _try_refresh(tokens)
        except requests.RequestException:
            new_tokens = None

        if new_tokens is None:
            db.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
            db.commit()
            raise RequiresLogin()

        db.execute(
            "UPDATE user_sessions"
            " SET access_token = ?, refresh_token = ?, expires_at = ?"
            " WHERE session_id = ?",
            (
                new_tokens["access_token"],
                new_tokens.get("refresh_token", tokens["refresh_token"]),
                new_tokens["expires_at"],
                session_id,
            ),
        )
        db.commit()
        tokens = new_tokens

    return CurrentUser(
        session_id=session_id,
        access_token=tokens["access_token"],
        expires_at=tokens["expires_at"],
    )
