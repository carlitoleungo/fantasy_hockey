"""
Tests for web/middleware/session.py — require_user dependency.

Each test creates a fresh in-memory DB and a minimal FastAPI app so tests
are fully isolated and make no live API or DB calls.
"""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest
import requests as req_lib
from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient

from db.connection import db_dep
from web.middleware.session import CurrentUser, RequiresLogin, require_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE user_sessions (
            session_id TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at REAL,
            created_at REAL
        );
    """)
    return conn


def _make_app(conn: sqlite3.Connection) -> FastAPI:
    test_app = FastAPI()

    @test_app.exception_handler(RequiresLogin)
    def handle_requires_login(request: Request, exc: RequiresLogin) -> RedirectResponse:
        return RedirectResponse("/auth/login", status_code=302)

    def override_db():
        yield conn

    test_app.dependency_overrides[db_dep] = override_db

    @test_app.get("/api/test")
    def protected(current_user: CurrentUser = Depends(require_user)):
        return {"ok": True, "session_id": current_user.session_id}

    @test_app.get("/auth/login")
    def login():
        return {"page": "login"}

    @test_app.get("/auth/callback")
    def callback():
        return {"page": "callback"}

    @test_app.get("/demo")
    def demo():
        return {"page": "demo"}

    return test_app


def _insert_session(conn, session_id, expires_at, access_token="acc", refresh_token="ref"):
    conn.execute(
        "INSERT INTO user_sessions (session_id, access_token, refresh_token, expires_at, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (session_id, access_token, refresh_token, expires_at, time.time()),
    )
    conn.commit()


def _fresh_token_response(access_token="new_acc", refresh_token="new_ref"):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 3600,
    }
    mock_resp.raise_for_status.return_value = None
    return mock_resp


@pytest.fixture()
def ctx(monkeypatch):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test_cid")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "test_csecret")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "http://localhost/auth/callback")
    conn = _make_db()
    app = _make_app(conn)
    client = TestClient(app, follow_redirects=False)
    yield conn, client
    conn.close()


# ---------------------------------------------------------------------------
# AC 1 — No session cookie → 302 to /auth/login
# ---------------------------------------------------------------------------

def test_no_cookie_redirects_to_login(ctx):
    _, client = ctx
    response = client.get("/api/test")
    assert response.status_code == 302
    assert response.headers["location"].endswith("/auth/login")


# ---------------------------------------------------------------------------
# AC 1b — Unknown session_id → 302 to /auth/login
# ---------------------------------------------------------------------------

def test_unknown_session_id_redirects(ctx):
    _, client = ctx
    response = client.get("/api/test", cookies={"session_id": "does-not-exist"})
    assert response.status_code == 302
    assert response.headers["location"].endswith("/auth/login")


# ---------------------------------------------------------------------------
# AC 2 — Valid non-expiring token → 200, zero requests.post calls
# ---------------------------------------------------------------------------

def test_valid_token_no_refresh(ctx):
    conn, client = ctx
    _insert_session(conn, "sid-valid", time.time() + 120)

    with patch("auth.oauth.requests.post") as mock_post:
        response = client.get("/api/test", cookies={"session_id": "sid-valid"})

    assert response.status_code == 200
    assert mock_post.call_count == 0


# ---------------------------------------------------------------------------
# AC 3 — Token expiring in 30 s (within 60 s buffer) → refresh called once,
#         new tokens written to DB, 200
# ---------------------------------------------------------------------------

def test_expiring_token_triggers_refresh(ctx):
    conn, client = ctx
    _insert_session(conn, "sid-expiring", time.time() + 30, access_token="old_acc")

    with patch("auth.oauth.requests.post", return_value=_fresh_token_response()) as mock_post:
        response = client.get("/api/test", cookies={"session_id": "sid-expiring"})

    assert response.status_code == 200
    assert mock_post.call_count == 1

    row = conn.execute(
        "SELECT access_token FROM user_sessions WHERE session_id = 'sid-expiring'"
    ).fetchone()
    assert row["access_token"] == "new_acc"


# ---------------------------------------------------------------------------
# AC 4 — Yahoo rejects refresh (401) → 302 to /auth/login, session row gone
# ---------------------------------------------------------------------------

def test_refresh_failure_redirects_and_deletes_session(ctx):
    conn, client = ctx
    _insert_session(conn, "sid-bad-refresh", time.time() + 30)

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = req_lib.HTTPError("401")

    with patch("auth.oauth.requests.post", return_value=mock_resp):
        response = client.get("/api/test", cookies={"session_id": "sid-bad-refresh"})

    assert response.status_code == 302
    assert response.headers["location"].endswith("/auth/login")

    row = conn.execute(
        "SELECT * FROM user_sessions WHERE session_id = 'sid-bad-refresh'"
    ).fetchone()
    assert row is None


# ---------------------------------------------------------------------------
# AC 4b — Network-level failure on refresh → same as auth failure
# ---------------------------------------------------------------------------

def test_network_error_on_refresh_redirects(ctx):
    conn, client = ctx
    _insert_session(conn, "sid-network-err", time.time() + 30)

    with patch("auth.oauth.requests.post", side_effect=req_lib.ConnectionError("timeout")):
        response = client.get("/api/test", cookies={"session_id": "sid-network-err"})

    assert response.status_code == 302
    assert response.headers["location"].endswith("/auth/login")

    row = conn.execute(
        "SELECT * FROM user_sessions WHERE session_id = 'sid-network-err'"
    ).fetchone()
    assert row is None


# ---------------------------------------------------------------------------
# AC 5 — Exempt routes respond normally without a session cookie
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/auth/login", "/auth/callback", "/demo"])
def test_exempt_routes_no_cookie(ctx, path):
    _, client = ctx
    response = client.get(path)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Boundary — expires_at = now+59 must refresh; now+61 must not
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("expires_delta,expect_refresh", [
    (59, True),
    (61, False),
])
def test_token_expiry_boundary(ctx, expires_delta, expect_refresh):
    conn, client = ctx
    sid = f"sid-boundary-{expires_delta}"
    _insert_session(conn, sid, time.time() + expires_delta)

    with patch("auth.oauth.requests.post", return_value=_fresh_token_response()) as mock_post:
        response = client.get("/api/test", cookies={"session_id": sid})

    assert response.status_code == 200
    assert mock_post.call_count == (1 if expect_refresh else 0)


# ---------------------------------------------------------------------------
# Boundary — two sequential requests with a healthy token → zero refreshes
# ---------------------------------------------------------------------------

def test_no_refresh_on_sequential_healthy_requests(ctx):
    conn, client = ctx
    _insert_session(conn, "sid-healthy", time.time() + 3600)

    with patch("auth.oauth.requests.post") as mock_post:
        r1 = client.get("/api/test", cookies={"session_id": "sid-healthy"})
        r2 = client.get("/api/test", cookies={"session_id": "sid-healthy"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert mock_post.call_count == 0
