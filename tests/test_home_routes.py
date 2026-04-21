"""
Tests for GET / and POST /leagues/select (tickets 011, 014).

Uses an in-memory SQLite DB injected via dependency override on db_dep.
get_user_hockey_leagues and make_session are mocked so no live Yahoo API
calls are made.
"""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient  # noqa: E402

from db.connection import db_dep  # noqa: E402
from web.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE user_sessions (
            session_id  TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at   REAL,
            created_at   REAL,
            league_key   TEXT
        );
        CREATE TABLE oauth_states (
            state TEXT PRIMARY KEY,
            expires_at REAL
        );
    """)
    return conn


def _insert_session(conn, session_id="sid-test", league_key=None):
    conn.execute(
        "INSERT INTO user_sessions"
        " (session_id, access_token, refresh_token, expires_at, created_at, league_key)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, "acc-token", "ref-token", time.time() + 3600, time.time(), league_key),
    )
    conn.commit()


LEAGUE_2025_A = {
    "league_key": "419.l.11111",
    "league_name": "Alpha League",
    "season": "2025",
}
LEAGUE_2025_B = {
    "league_key": "419.l.22222",
    "league_name": "Beta League",
    "season": "2025",
}
LEAGUE_2024_OLD = {
    "league_key": "411.l.99999",
    "league_name": "Old League",
    "season": "2024",
}


@pytest.fixture()
def ctx():
    conn = _make_db()

    def override_db():
        yield conn

    app.dependency_overrides[db_dep] = override_db
    client = TestClient(app, follow_redirects=False)
    yield conn, client
    app.dependency_overrides.clear()
    conn.close()


# ---------------------------------------------------------------------------
# TC1 — GET / with valid session: returns 200 and filters to current season
# ---------------------------------------------------------------------------

def test_home_filters_to_current_season(ctx):
    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B, LEAGUE_2024_OLD],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert "Alpha League" in body
    assert "Beta League" in body
    assert "Old League" not in body
    assert "2025" in body


# ---------------------------------------------------------------------------
# TC2 — GET / with empty league list: returns 200 with empty-state message
# ---------------------------------------------------------------------------

def test_home_empty_leagues(ctx):
    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch("web.routes.home.get_user_hockey_leagues", return_value=[]),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert "No active NHL leagues found for your account." in response.text


# ---------------------------------------------------------------------------
# TC3 — GET / with a pre-selected league: highlight shown for that league
# ---------------------------------------------------------------------------

def test_home_shows_selected_league_indicator(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    # The template emits "✓ Selected" (HTML entity ✓) next to the active league
    assert "Selected" in body
    # Confirm the selected league key appears in a highlighted context
    assert "419.l.11111" in body


# ---------------------------------------------------------------------------
# TC4 — POST /leagues/select: updates DB row and redirects 302 to /
# ---------------------------------------------------------------------------

def test_select_league_updates_db_and_redirects(ctx):
    conn, client = ctx
    _insert_session(conn)

    response = client.post(
        "/leagues/select",
        data={"league_key": "419.l.11111"},
        cookies={"session_id": "sid-test"},
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/"

    row = conn.execute(
        "SELECT league_key FROM user_sessions WHERE session_id = 'sid-test'"
    ).fetchone()
    assert row["league_key"] == "419.l.11111"


# ---------------------------------------------------------------------------
# TC5 — GET / with no cookie: 302 to /auth/login
# ---------------------------------------------------------------------------

def test_home_no_cookie_redirects_to_login(ctx):
    _, client = ctx
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# TC6 — POST /leagues/select with no cookie: 302 to /auth/login
# ---------------------------------------------------------------------------

def test_select_league_no_cookie_redirects_to_login(ctx):
    _, client = ctx
    response = client.post("/leagues/select", data={"league_key": "419.l.11111"})
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# TC7 — GET / when Yahoo API raises HTTPError: 502 error page (not 500)
# ---------------------------------------------------------------------------

def test_home_yahoo_api_error_returns_502(ctx):
    import requests as req_lib

    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            side_effect=req_lib.HTTPError("Yahoo API error"),
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 502


# ---------------------------------------------------------------------------
# TC8 — GET / renders nav header with app-name anchor and logout link (014)
# ---------------------------------------------------------------------------

def test_home_renders_nav_header(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert 'href="/"' in body
    assert "Fantasy Hockey" in body
    assert '<a href="/auth/logout"' in body


# ---------------------------------------------------------------------------
# TC9 — GET / with selected league renders league name in header (014)
# ---------------------------------------------------------------------------

def test_home_header_shows_selected_league_name(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert "Alpha League" in response.text


# ---------------------------------------------------------------------------
# TC10 — GET / with no selected league renders header without league label (014)
# ---------------------------------------------------------------------------

def test_home_header_no_league_label_when_unselected(ctx):
    conn, client = ctx
    _insert_session(conn)  # no league_key

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert 'href="/"' in body
    assert "Fantasy Hockey" in body
    # No separator character should appear in the header when no league is selected
    assert "&middot;" not in body
