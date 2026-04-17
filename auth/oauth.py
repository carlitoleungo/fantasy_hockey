"""
Yahoo OAuth 2.0 flow for the Fantasy Hockey web app.

Design notes:
- yahoo_oauth's OAuth2 class is designed for interactive terminal use and cannot
  handle redirect-based callback flows, so we implement the auth dance directly
  with requests.
- Credentials (client_id, client_secret, redirect_uri) come from environment
  variables and are never written to disk.
- Tokens are kept in the SQLite user_sessions table. No session_state or token
  file is used.
- A random `state` nonce is returned from get_auth_url() so the caller can
  persist it (e.g. to the oauth_states DB table) and validate it on callback.
"""

from __future__ import annotations

import os
import secrets
import time
import urllib.parse

import requests

YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
TOKEN_EXPIRY_BUFFER_SECONDS = 60   # refresh this many seconds before actual expiry


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_auth_url() -> tuple[str, str]:
    """
    Return a (url, state) tuple for starting the Yahoo OAuth flow.

    The caller is responsible for persisting the state nonce (e.g. inserting it
    into the oauth_states DB table) so it can be validated on callback.
    """
    state = secrets.token_urlsafe(32)
    params = urllib.parse.urlencode({
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "state": state,
    })
    return f"{YAHOO_AUTH_URL}?{params}", state


def make_session(access_token: str) -> requests.Session:
    """Return a requests.Session pre-configured with the Yahoo OAuth Bearer token."""
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {access_token}"})
    return session


def exchange_code(code: str) -> dict:
    """
    Exchange an authorization code (from Yahoo's redirect callback) for tokens.
    Returns the token dict. Raises requests.HTTPError on failure.
    """
    response = requests.post(
        YAHOO_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(),
        },
        auth=(_client_id(), _client_secret()),
    )
    response.raise_for_status()
    return _stamp_expiry(response.json())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _client_id() -> str:
    return os.environ["YAHOO_CLIENT_ID"]


def _client_secret() -> str:
    return os.environ["YAHOO_CLIENT_SECRET"]


def _redirect_uri() -> str:
    return os.environ["YAHOO_REDIRECT_URI"]


def _stamp_expiry(tokens: dict) -> dict:
    """Add an absolute expires_at timestamp so we can check validity later."""
    tokens["expires_at"] = time.time() + int(tokens.get("expires_in", 3600))
    return tokens


def _is_valid(tokens: dict) -> bool:
    """True if the access token won't expire within the buffer window."""
    return time.time() < tokens.get("expires_at", 0) - TOKEN_EXPIRY_BUFFER_SECONDS


def _try_refresh(tokens: dict) -> dict | None:
    """
    Attempt to refresh the access token using the refresh token.
    Returns new tokens on success, None on failure.
    """
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return None

    try:
        response = requests.post(
            YAHOO_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "redirect_uri": _redirect_uri(),
            },
            auth=(_client_id(), _client_secret()),
        )
        response.raise_for_status()
        return _stamp_expiry(response.json())
    except requests.HTTPError:
        return None
