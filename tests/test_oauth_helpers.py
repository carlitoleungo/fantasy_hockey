"""
Unit tests for pure helper functions in auth/oauth.py.
"""

import time

import pytest

from auth.oauth import _stamp_expiry, _is_valid


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
