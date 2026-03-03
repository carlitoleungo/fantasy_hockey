"""
Yahoo OAuth 2.0 flow for the Fantasy Hockey Streamlit app.

Design notes:
- yahoo_oauth's OAuth2 class is designed for interactive terminal use and cannot
  handle Streamlit's redirect-based callback flow, so we implement the auth dance
  directly with requests. The pattern mirrors the notebook's get_oauth() approach:
  check validity → refresh if needed → return authenticated session.
- Credentials (client_id, client_secret) come from st.secrets and are never written
  to disk. Tokens (access_token, refresh_token, expires_at) are persisted to
  .streamlit/oauth_token.json, which is gitignored.
- st.session_state["tokens"] is the in-session cache. The token file provides
  persistence across sessions so users don't re-auth every time.
"""

import json
import os
import time
import urllib.parse

import requests
import streamlit as st

YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
TOKEN_FILE = ".streamlit/oauth_token.json"
TOKEN_EXPIRY_BUFFER_SECONDS = 60  # refresh this many seconds before actual expiry


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_auth_url() -> str:
    """Return the Yahoo authorization URL to send the user to."""
    params = urllib.parse.urlencode({
        "client_id": st.secrets["yahoo"]["client_id"],
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
    })
    return f"{YAHOO_AUTH_URL}?{params}"


def exchange_code(code: str) -> dict:
    """
    Exchange an authorization code (from Yahoo's redirect callback) for tokens.
    Persists the tokens to disk and returns them.
    Raises requests.HTTPError on failure.
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
    tokens = _stamp_expiry(response.json())
    _save_tokens(tokens)
    return tokens


def get_session() -> requests.Session | None:
    """
    Return a requests.Session with a valid Bearer token, or None if not logged in.

    Checks st.session_state first, falls back to the token file on disk.
    Transparently refreshes the access token if it has expired.
    This is the function the rest of the app should call before any API request.
    """
    tokens = st.session_state.get("tokens") or _load_tokens()
    if not tokens:
        return None

    if not _is_valid(tokens):
        tokens = _try_refresh(tokens)
        if tokens is None:
            return None

    # Keep session state in sync (covers the disk-fallback path)
    st.session_state["tokens"] = tokens

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return session


def try_restore_session() -> bool:
    """
    Called once at app startup. If valid tokens exist on disk, load them into
    session state so the user doesn't have to re-authenticate.
    Returns True if a valid session was restored, False otherwise.
    """
    if "tokens" in st.session_state:
        return True

    tokens = _load_tokens()
    if not tokens:
        return False

    if not _is_valid(tokens):
        tokens = _try_refresh(tokens)
        if tokens is None:
            return False

    st.session_state["tokens"] = tokens
    return True


def clear_session() -> None:
    """Log the user out: remove tokens from session state and from disk."""
    st.session_state.pop("tokens", None)
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _redirect_uri() -> str:
    return st.secrets["yahoo"].get("redirect_uri", "https://localhost:8501")


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


def _save_tokens(tokens: dict) -> None:
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)


def _load_tokens() -> dict | None:
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f)


def _try_refresh(tokens: dict) -> dict | None:
    """
    Attempt to refresh the access token using the refresh token.
    Returns new tokens on success, None on failure (clears stale disk state).
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
        new_tokens = _stamp_expiry(response.json())
        _save_tokens(new_tokens)
        return new_tokens
    except requests.HTTPError:
        # Refresh token is invalid or revoked — clear stale state
        st.session_state.pop("tokens", None)
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return None
