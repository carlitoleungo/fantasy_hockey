"""
Yahoo OAuth 2.0 flow for the Fantasy Hockey Streamlit app.

Design notes:
- yahoo_oauth's OAuth2 class is designed for interactive terminal use and cannot
  handle Streamlit's redirect-based callback flow, so we implement the auth dance
  directly with requests. The pattern mirrors the notebook's get_oauth() approach:
  check validity → refresh if needed → return authenticated session.
- Credentials (client_id, client_secret) come from st.secrets and are never written
  to disk.
- Tokens are kept exclusively in st.session_state["tokens"] (server-side, per-user).
  No token file is used — this prevents cross-user token collision when multiple
  people use the app simultaneously.
- A random `state` nonce is stored in session state when the auth URL is generated
  and validated when Yahoo redirects back, preventing CSRF attacks.
- Yahoo's browser session makes re-authentication seamless: if the user opens a new
  tab, clicking "Sign in with Yahoo" redirects to Yahoo and back in under a second
  without a password prompt.
"""

import json
import os
import secrets
import time
import urllib.parse

import requests
import streamlit as st

YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
TOKEN_EXPIRY_BUFFER_SECONDS = 60   # refresh this many seconds before actual expiry
_STATE_FILE = ".streamlit/oauth_states.json"
_STATE_TTL = 300  # nonces expire after 5 minutes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_auth_url() -> str:
    """
    Return the Yahoo authorization URL to send the user to.

    Generates a random state nonce and persists it server-side with a short TTL.
    Session state can't be used here because the browser navigates away to Yahoo
    and back, creating a new Streamlit session on return.
    """
    state = secrets.token_urlsafe(32)
    _save_state(state)
    params = urllib.parse.urlencode({
        "client_id": st.secrets["yahoo"]["client_id"],
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "state": state,
    })
    return f"{YAHOO_AUTH_URL}?{params}"


def validate_and_consume_state(state: str) -> bool:
    """
    Return True if state is a known, unexpired nonce, and consume it.
    One-time use: a valid state is deleted on first check.
    """
    states = _load_states()
    now = time.time()
    if state in states and states[state] > now:
        del states[state]
        _save_states({s: exp for s, exp in states.items() if exp > now})
        return True
    return False


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


def get_session() -> requests.Session | None:
    """
    Return a requests.Session with a valid Bearer token, or None if not logged in.

    Reads exclusively from st.session_state — no disk fallback. Transparently
    refreshes the access token if it has expired within the current session.
    """
    tokens = st.session_state.get("tokens")
    if not tokens:
        return None

    if not _is_valid(tokens):
        tokens = _try_refresh(tokens)
        if tokens is None:
            return None

    st.session_state["tokens"] = tokens

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return session


def try_restore_session() -> bool:
    """
    Called once at app startup. Returns True if a valid session already exists
    in session state (e.g. page rerun or F5 refresh within the same session).
    """
    return "tokens" in st.session_state


def clear_session() -> None:
    """Log the user out by removing tokens from session state."""
    st.session_state.pop("tokens", None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _redirect_uri() -> str:
    return st.secrets["yahoo"].get("redirect_uri", "https://localhost:8501").strip()


def _client_id() -> str:
    return st.secrets["yahoo"]["client_id"]


def _client_secret() -> str:
    return st.secrets["yahoo"]["client_secret"]


def _stamp_expiry(tokens: dict) -> dict:
    """Add an absolute expires_at timestamp so we can check validity later."""
    tokens["expires_at"] = time.time() + int(tokens.get("expires_in", 3600))
    return tokens


def _is_valid(tokens: dict) -> bool:
    """True if the access token won't expire within the buffer window."""
    return time.time() < tokens.get("expires_at", 0) - TOKEN_EXPIRY_BUFFER_SECONDS


def _save_state(state: str) -> None:
    states = _load_states()
    now = time.time()
    # Prune expired entries on each write to keep the file small
    states = {s: exp for s, exp in states.items() if exp > now}
    states[state] = now + _STATE_TTL
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    with open(_STATE_FILE, "w") as f:
        json.dump(states, f)


def _load_states() -> dict:
    if not os.path.exists(_STATE_FILE):
        return {}
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_states(states: dict) -> None:
    with open(_STATE_FILE, "w") as f:
        json.dump(states, f)


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
        st.session_state.pop("tokens", None)
        return None
