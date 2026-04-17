"""
Auth routes: GET /auth/login and GET /auth/callback.

Login: generates an OAuth URL + state nonce, persists the nonce to oauth_states
with a 300-second TTL, and redirects the browser to Yahoo.

Callback: validates the state nonce (one-time use), exchanges the code for
tokens, writes the session to user_sessions, sets a session_id cookie, and
redirects to /.

Token refresh is out of scope — see ticket 005.
"""

from __future__ import annotations

import os
import secrets
import time

import requests
from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from auth.oauth import exchange_code, get_auth_url
from db.connection import db_dep

router = APIRouter()

_NONCE_TTL_SECONDS = 300
_SESSION_COOKIE_MAX_AGE = 2592000  # 30 days


@router.get("/auth/login")
def login(db=Depends(db_dep)):
    url, state = get_auth_url()
    db.execute(
        "INSERT INTO oauth_states (state, expires_at) VALUES (?, ?)",
        (state, time.time() + _NONCE_TTL_SECONDS),
    )
    db.commit()
    return RedirectResponse(url, status_code=302)


@router.get("/auth/callback")
def callback(request: Request, db=Depends(db_dep)):
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    # Validate and consume the nonce (one-time use).
    row = db.execute(
        "SELECT expires_at FROM oauth_states WHERE state = ?", (state,)
    ).fetchone()

    if row is None or row["expires_at"] < time.time():
        return JSONResponse({"detail": "invalid or expired state"}, status_code=400)

    db.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    db.commit()

    # Exchange the code for tokens.
    try:
        tokens = exchange_code(code)
    except requests.HTTPError:
        return JSONResponse({"detail": "token exchange failed"}, status_code=400)

    # Write session.
    session_id = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO user_sessions (session_id, access_token, refresh_token, expires_at, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            session_id,
            tokens.get("access_token"),
            tokens.get("refresh_token"),
            tokens.get("expires_at"),
            time.time(),
        ),
    )
    db.commit()

    secure = os.environ.get("HTTPS_ONLY") == "true"
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=_SESSION_COOKIE_MAX_AGE,
        secure=secure,
    )
    return response


@router.get("/auth/logout")
def logout(db=Depends(db_dep), session_id: str | None = Cookie(default=None)):
    if session_id is not None:
        db.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
        db.commit()

    secure = os.environ.get("HTTPS_ONLY") == "true"
    response = RedirectResponse("/auth/login", status_code=302)
    response.delete_cookie("session_id", secure=secure)
    return response
