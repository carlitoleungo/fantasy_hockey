"""
Unit tests for pure helper functions in auth/oauth.py.

Streamlit is mocked before importing auth.oauth because the module has a
top-level `import streamlit as st`, but the functions under test never call
st.secrets — they work on plain dicts and the local state file.

The nonce state file is redirected to tmp_path via the `state_file` fixture,
matching the pattern used in tests/test_cache.py for CACHE_DIR.
"""

import json
import sys
import time
from unittest.mock import MagicMock

sys.modules["streamlit"] = MagicMock()

import pytest

import auth.oauth as oauth_module
from auth.oauth import _stamp_expiry, _is_valid, _STATE_TTL, validate_and_consume_state


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
    # 30 seconds from now is inside the 60-second buffer window
    tokens = {"expires_at": time.time() + 30}
    assert _is_valid(tokens) is False


def test_is_valid_returns_true_when_ample_time_remains():
    # 3600 seconds from now is well outside the buffer
    tokens = {"expires_at": time.time() + 3600}
    assert _is_valid(tokens) is True


# ---------------------------------------------------------------------------
# validate_and_consume_state — nonce lifecycle
# ---------------------------------------------------------------------------

@pytest.fixture()
def state_file(tmp_path, monkeypatch):
    """Redirect _STATE_FILE to a temp path so tests don't touch .streamlit/."""
    state_path = str(tmp_path / "oauth_states.json")
    monkeypatch.setattr(oauth_module, "_STATE_FILE", state_path)
    return state_path


def test_validate_unknown_nonce_returns_false(state_file):
    assert validate_and_consume_state("not_a_real_nonce") is False


def test_validate_known_nonce_true_then_false(state_file):
    """A valid nonce is consumed on first use; the second call returns False."""
    nonce = "test_nonce_abc123"
    oauth_module._save_state(nonce)

    assert validate_and_consume_state(nonce) is True
    assert validate_and_consume_state(nonce) is False


def test_validate_expired_nonce_returns_false(state_file):
    """A nonce whose expiry is in the past is rejected."""
    nonce = "expired_nonce_xyz"
    with open(state_file, "w") as f:
        json.dump({nonce: time.time() - 1}, f)

    assert validate_and_consume_state(nonce) is False
