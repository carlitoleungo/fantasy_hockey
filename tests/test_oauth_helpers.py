"""
Unit tests for pure helper functions in auth/oauth.py.
"""

import time

import pytest

from auth.oauth import (
    TOKEN_EXPIRY_BUFFER_SECONDS,
    _client_id,
    _client_secret,
    _is_valid,
    _redirect_uri,
    _stamp_expiry,
    make_session,
)


# ---------------------------------------------------------------------------
# _stamp_expiry
# ---------------------------------------------------------------------------

def test_stamp_expiry_adds_expires_at():
    before = time.time()
    tokens = {"access_token": "abc", "expires_in": 3600}
    result = _stamp_expiry(tokens)
    after = time.time()

    assert "expires_at" in result
    assert before + 3600 <= result["expires_at"] <= after + 3600


def test_stamp_expiry_returns_same_dict():
    tokens = {"access_token": "abc", "expires_in": 3600}
    result = _stamp_expiry(tokens)
    assert result is tokens


# ---------------------------------------------------------------------------
# _is_valid
# ---------------------------------------------------------------------------

def test_is_valid_returns_false_when_expired():
    tokens = {"expires_at": time.time() - 100}
    assert _is_valid(tokens) is False


def test_is_valid_returns_false_within_buffer():
    # TOKEN_EXPIRY_BUFFER_SECONDS - 1 is inside the buffer window
    tokens = {"expires_at": time.time() + TOKEN_EXPIRY_BUFFER_SECONDS - 1}
    assert _is_valid(tokens) is False


def test_is_valid_returns_true_when_ample_time_remains():
    # 3600 seconds from now is well outside the buffer
    tokens = {"expires_at": time.time() + 3600}
    assert _is_valid(tokens) is True


# ---------------------------------------------------------------------------
# make_session
# ---------------------------------------------------------------------------

def test_make_session_sets_authorization_header():
    session = make_session("test_token")
    assert session.headers["Authorization"] == "Bearer test_token"


# ---------------------------------------------------------------------------
# _client_id / _client_secret / _redirect_uri
# ---------------------------------------------------------------------------

def test_client_id_returns_env_value(monkeypatch):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test-client-id")
    assert _client_id() == "test-client-id"


def test_client_id_raises_when_env_unset(monkeypatch):
    monkeypatch.delenv("YAHOO_CLIENT_ID", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        _client_id()
    assert type(exc_info.value) is RuntimeError
    assert "YAHOO_CLIENT_ID" in str(exc_info.value)


def test_client_secret_returns_env_value(monkeypatch):
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "test-client-secret")
    assert _client_secret() == "test-client-secret"


def test_client_secret_raises_when_env_unset(monkeypatch):
    monkeypatch.delenv("YAHOO_CLIENT_SECRET", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        _client_secret()
    assert type(exc_info.value) is RuntimeError
    assert "YAHOO_CLIENT_SECRET" in str(exc_info.value)


def test_redirect_uri_returns_env_value(monkeypatch):
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://example.com/callback")
    assert _redirect_uri() == "https://example.com/callback"


def test_redirect_uri_raises_when_env_unset(monkeypatch):
    monkeypatch.delenv("YAHOO_REDIRECT_URI", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        _redirect_uri()
    assert type(exc_info.value) is RuntimeError
    assert "YAHOO_REDIRECT_URI" in str(exc_info.value)
