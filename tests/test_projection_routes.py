"""
Tests for GET /projection (ticket 029 — Week Projection shell).

Uses an in-memory SQLite DB injected via dependency override on db_dep.
make_session, get_user_hockey_leagues, and get_teams are mocked so no live
Yahoo API calls are made. The /projection/matchup fragment is ticket 030 and
is intentionally not exercised here.
"""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient

from db.connection import db_dep
from web.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE user_sessions (
            session_id   TEXT PRIMARY KEY,
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


LEAGUE_A = {"league_key": "419.l.11111", "league_name": "Alpha League", "season": "2025"}

TEAMS = [
    {"team_key": "419.l.11111.t.1", "team_id": "1", "team_name": "Alpha", "manager_name": "Ann"},
    {"team_key": "419.l.11111.t.2", "team_id": "2", "team_name": "Beta", "manager_name": "Bob"},
    {"team_key": "419.l.11111.t.3", "team_id": "3", "team_name": "Gamma", "manager_name": "Cal"},
]


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


def _patched_get(client, cookies):
    with (
        patch("web.routes.projection.make_session", return_value=MagicMock()),
        patch("web.routes.projection.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.projection.get_teams", return_value=TEAMS),
    ):
        return client.get("/projection", cookies=cookies)


# ---------------------------------------------------------------------------
# AC1 — 200 with <h1> "Week Projection"
# ---------------------------------------------------------------------------

def test_projection_shell_returns_200_with_header(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    response = _patched_get(client, {"session_id": "sid-test"})
    assert response.status_code == 200
    assert "<h1" in response.text
    assert "Week Projection" in response.text


# ---------------------------------------------------------------------------
# AC2 — team <select> with one option per team; matchup container targeted by
#        hx-get to matchup_url carrying the selected team
# ---------------------------------------------------------------------------

def test_projection_shell_has_team_select_and_matchup_target(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    response = _patched_get(client, {"session_id": "sid-test"})
    assert response.status_code == 200
    body = response.text

    # One option per team name
    for team in TEAMS:
        assert f'value="{team["team_key"]}"' in body
        assert team["team_name"] in body

    # A <select> that drives the matchup container via hx-get to matchup_url
    assert "<select" in body
    assert 'name="team_key"' in body
    assert 'hx-get="/projection/matchup"' in body
    assert 'hx-target="#projection-matchup"' in body

    # Matchup container present
    assert 'id="projection-matchup"' in body


# ---------------------------------------------------------------------------
# AC3 — matchup container issues hx-get on load with the default-selected team
# ---------------------------------------------------------------------------

def test_projection_matchup_container_loads_default_team(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    response = _patched_get(client, {"session_id": "sid-test"})
    assert response.status_code == 200
    body = response.text

    # Container auto-fetches on load with the first team's key
    assert 'hx-trigger="load"' in body
    assert f'hx-get="/projection/matchup?team_key={TEAMS[0]["team_key"]}"' in body
    # First option is the default-selected one
    assert f'value="{TEAMS[0]["team_key"]}" selected' in body


# ---------------------------------------------------------------------------
# AC4 — nav shows a "Projection" link (after Waiver) pointing to /projection
# ---------------------------------------------------------------------------

def test_projection_nav_link_present_and_after_waiver(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    response = _patched_get(client, {"session_id": "sid-test"})
    assert response.status_code == 200
    body = response.text
    assert '<a href="/projection"' in body
    # Ordering: Waiver link appears before the Projection link
    assert body.index('href="/waiver"') < body.index('href="/projection"')


# ---------------------------------------------------------------------------
# AC5 — no league data (empty teams) → 200 + friendly empty-state, no selector
# ---------------------------------------------------------------------------

def test_projection_empty_league_shows_empty_state(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    with (
        patch("web.routes.projection.make_session", return_value=MagicMock()),
        patch("web.routes.projection.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.projection.get_teams", return_value=[]),
    ):
        response = client.get("/projection", cookies={"session_id": "sid-test"})
    assert response.status_code == 200
    body = response.text
    assert "season may not have started" in body
    assert "<select" not in body


# ---------------------------------------------------------------------------
# Session guards — mirror /waiver behaviour
# ---------------------------------------------------------------------------

def test_projection_no_league_redirects_to_home(ctx):
    conn, client = ctx
    _insert_session(conn)  # no league_key
    response = client.get("/projection", cookies={"session_id": "sid-test"})
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_projection_no_cookie_redirects_to_login(ctx):
    _, client = ctx
    response = client.get("/projection")
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"
