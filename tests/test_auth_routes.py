"""
Tests for GET /auth/login and GET /auth/callback.

Uses an in-memory SQLite DB injected via a dependency override on get_db
so no real DB file is created. requests.post is mocked so no live Yahoo
API calls are made.
"""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from web.main import app
from web.routes.auth import _db_dep


# ---------------------------------------------------------------------------
# In-memory DB fixture
# ---------------------------------------------------------------------------

def _make_in_memory_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE oauth_states (
            state TEXT PRIMARY KEY,
            expires_at REAL
        );
        CREATE TABLE user_sessions (
            session_id TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at REAL,
            created_at REAL
        );
    """)
    return conn


@pytest.fixture()
def db_and_client():
    """
    Yield (db_conn, TestClient) with the in-memory DB injected.
    The same connection is shared by the test body and route handlers so we
    can inspect DB state after route calls.
    """
    conn = _make_in_memory_db()

    def override_db():
        yield conn

    app.dependency_overrides[_db_dep] = override_db
    client = TestClient(app, follow_redirects=False)
    yield conn, client
    app.dependency_overrides.clear()
    conn.close()


# ---------------------------------------------------------------------------
# Test 1 — /auth/login returns 302 to Yahoo and writes a nonce to oauth_states
# ---------------------------------------------------------------------------

def test_login_redirects_to_yahoo_and_stores_nonce(db_and_client):
    conn, client = db_and_client

    fake_url = "https://api.login.yahoo.com/oauth2/request_auth?client_id=cid&state=abc"
    fake_state = "abc"
    with patch("web.routes.auth.get_auth_url", return_value=(fake_url, fake_state)):
        response = client.get("/auth/login")

    assert response.status_code == 302
    location = response.headers["location"]
    assert "login.yahoo.com" in location

    rows = conn.execute("SELECT * FROM oauth_states").fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["expires_at"] == pytest.approx(time.time() + 300, abs=5)


# ---------------------------------------------------------------------------
# Test 2 — /auth/callback with invalid state returns 400 and makes no Yahoo call
# ---------------------------------------------------------------------------

def test_callback_invalid_state_returns_400_no_yahoo_call(db_and_client):
    _, client = db_and_client

    with patch("web.routes.auth.exchange_code") as mock_exchange:
        response = client.get("/auth/callback?code=FAKE&state=INVALID")

    assert response.status_code == 400
    assert mock_exchange.call_count == 0


# ---------------------------------------------------------------------------
# Test 3 — Round-trip: valid nonce → 302 to / → session row written
# ---------------------------------------------------------------------------

def test_callback_valid_nonce_creates_session(db_and_client):
    conn, client = db_and_client

    # Pre-insert a valid nonce.
    state = "valid-state-nonce"
    conn.execute(
        "INSERT INTO oauth_states (state, expires_at) VALUES (?, ?)",
        (state, time.time() + 300),
    )
    conn.commit()

    fake_tokens = {
        "access_token": "acc123",
        "refresh_token": "ref456",
        "expires_at": time.time() + 3600,
    }

    with patch("web.routes.auth.exchange_code", return_value=fake_tokens):
        response = client.get(f"/auth/callback?code=REALCODE&state={state}")

    assert response.status_code == 302
    assert response.headers["location"] == "/"

    session_rows = conn.execute("SELECT * FROM user_sessions").fetchall()
    assert len(session_rows) == 1
    session = session_rows[0]
    assert session["access_token"] == "acc123"
    assert session["refresh_token"] == "ref456"


# ---------------------------------------------------------------------------
# Test 4 — Second call with the same (consumed) nonce returns 400
# ---------------------------------------------------------------------------

def test_callback_nonce_one_time_use(db_and_client):
    conn, client = db_and_client

    state = "one-time-nonce"
    conn.execute(
        "INSERT INTO oauth_states (state, expires_at) VALUES (?, ?)",
        (state, time.time() + 300),
    )
    conn.commit()

    fake_tokens = {
        "access_token": "acc",
        "refresh_token": "ref",
        "expires_at": time.time() + 3600,
    }

    with patch("web.routes.auth.exchange_code", return_value=fake_tokens):
        first = client.get(f"/auth/callback?code=CODE&state={state}")
    assert first.status_code == 302

    with patch("web.routes.auth.exchange_code") as mock_exchange:
        second = client.get(f"/auth/callback?code=CODE&state={state}")
    assert second.status_code == 400
    assert mock_exchange.call_count == 0
