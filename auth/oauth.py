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
_NONCE_TTL_SECONDS = 300

# In-memory state nonce store for Streamlit's single-process OAuth flow.
# FastAPI stores nonces in the DB instead; this dict is ignored there.
_pending_states: dict[str, float] = {}  # state -> expires_at


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_auth_url() -> tuple[str, str]:
    """
    Return a (url, state) tuple for starting the Yahoo OAuth flow.

    Also stores the state nonce in _pending_states so validate_and_consume_state
    can verify it on callback (used by the Streamlit app). FastAPI callers should
    additionally persist the nonce to the oauth_states DB table.
    """
    state = secrets.token_urlsafe(32)
    params = urllib.parse.urlencode({
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "state": state,
    })
    _pending_states[state] = time.time() + _NONCE_TTL_SECONDS
    return f"{YAHOO_AUTH_URL}?{params}", state


def validate_and_consume_state(state: str) -> bool:
    """
    Validate and consume a state nonce from _pending_states (one-time use).
    Returns True if valid, False if missing or expired.
    """
    now = time.time()
    # Evict expired entries
    expired = [s for s, exp in list(_pending_states.items()) if exp < now]
    for s in expired:
        _pending_states.pop(s, None)

    if state in _pending_states:
        del _pending_states[state]
        return True
    return False


def try_restore_session() -> None:
    """
    Attempt to restore a valid session into st.session_state["tokens"].

    For the Streamlit app, tokens only live in session_state (no persistent
    storage). This is a no-op if tokens are already present or absent — the
    caller should check session_state["tokens"] after calling this.
    """
    import streamlit as st  # lazy import; not available in the FastAPI process
    tokens = st.session_state.get("tokens")
    if tokens is None:
        return
    if not _is_valid(tokens):
        refreshed = _try_refresh(tokens)
        if refreshed is not None:
            st.session_state["tokens"] = refreshed
        else:
            st.session_state.pop("tokens", None)


def get_session() -> requests.Session | None:
    """
    Return an authenticated requests.Session using tokens from st.session_state,
    refreshing if needed. Returns None if there are no valid tokens.
    """
    import streamlit as st  # lazy import
    tokens = st.session_state.get("tokens")
    if tokens is None:
        return None
    if not _is_valid(tokens):
        tokens = _try_refresh(tokens)
        if tokens is None:
            return None
        st.session_state["tokens"] = tokens
    return make_session(tokens["access_token"])


def clear_session() -> None:
    """Remove tokens from st.session_state, effectively logging the user out."""
    import streamlit as st  # lazy import
    st.session_state.pop("tokens", None)


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
