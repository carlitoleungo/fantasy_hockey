"""
Tests for GET /waiver and GET /demo/waiver (ticket 018).

Uses an in-memory SQLite DB injected via dependency override on db_dep.
make_session, get_user_hockey_leagues, get_matchups, and get_stat_categories
are mocked so no live Yahoo API calls are made.
"""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pandas as pd
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


def _make_matchups_df() -> pd.DataFrame:
    """3 teams × 2 weeks × 3 stats fixture."""
    rows = []
    teams = [("t1", "Alpha"), ("t2", "Beta"), ("t3", "Gamma")]
    stat_values = {
        1: {
            "Alpha": {"Goals": 10.0, "Assists": 5.0, "Shots on Goal": 30.0},
            "Beta":  {"Goals": 7.0,  "Assists": 9.0, "Shots on Goal": 25.0},
            "Gamma": {"Goals": 5.0,  "Assists": 6.0, "Shots on Goal": 35.0},
        },
        2: {
            "Alpha": {"Goals": 8.0, "Assists": 8.0, "Shots on Goal": 28.0},
            "Beta":  {"Goals": 5.0, "Assists": 4.0, "Shots on Goal": 22.0},
            "Gamma": {"Goals": 3.0, "Assists": 3.0, "Shots on Goal": 18.0},
        },
    }
    for week, team_stats in stat_values.items():
        for key, name in teams:
            row = {"team_key": key, "team_name": name, "week": week, "games_played": 7}
            row.update(team_stats[name])
            rows.append(row)
    return pd.DataFrame(rows)


LEAGUE_A = {"league_key": "419.l.11111", "league_name": "Alpha League", "season": "2025"}


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
# TC1 — GET /waiver with fixture session and 3×2×3 matchups returns 200
#        with all 6 position radio values and all 3 stat checkbox values
# ---------------------------------------------------------------------------

def test_waiver_shell_returns_200_with_controls(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.waiver.get_matchups", return_value=df),
        patch("web.routes.waiver.get_stat_categories", return_value=[]),
    ):
        response = client.get("/waiver", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text

    # All 6 position radio input values present
    for pos in ["All", "C", "LW", "RW", "D", "G"]:
        assert f'value="{pos}"' in body, f"Missing position value: {pos}"

    # All 3 stat checkbox values present
    for stat in ["Goals", "Assists", "Shots on Goal"]:
        assert f'value="{stat}"' in body, f"Missing stat checkbox: {stat}"


# ---------------------------------------------------------------------------
# TC2 — GET /waiver with NULL league_key → 302 to /
# ---------------------------------------------------------------------------

def test_waiver_no_league_redirects_to_home(ctx):
    conn, client = ctx
    _insert_session(conn)  # no league_key

    response = client.get("/waiver", cookies={"session_id": "sid-test"})

    assert response.status_code == 302
    assert response.headers["location"] == "/"


# ---------------------------------------------------------------------------
# TC3 — GET /waiver without session cookie → 302 to /auth/login
# ---------------------------------------------------------------------------

def test_waiver_no_cookie_redirects_to_login(ctx):
    _, client = ctx
    response = client.get("/waiver")
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# TC4 — GET /demo/waiver (no session) → 200 with demo form action
# ---------------------------------------------------------------------------

def test_demo_waiver_shell_returns_200(ctx):
    _, client = ctx

    demo_df = _make_matchups_df()

    with (
        patch("data.demo.get_matchups", return_value=demo_df),
        patch("data.demo.get_stat_categories", return_value=[]),
    ):
        response = client.get("/demo/waiver")

    assert response.status_code == 200
    body = response.text
    assert "/demo/api/waiver/players" in body


# ---------------------------------------------------------------------------
# TC5 — Form has correct HTMX attributes
# ---------------------------------------------------------------------------

def test_waiver_form_has_htmx_attributes(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.waiver.get_matchups", return_value=df),
        patch("web.routes.waiver.get_stat_categories", return_value=[]),
    ):
        response = client.get("/waiver", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert 'hx-post="/api/waiver/players"' in body
    assert 'hx-target="#waiver-table-container"' in body
    assert 'hx-trigger="change"' in body


# ---------------------------------------------------------------------------
# TC6 — Empty state container is present
# ---------------------------------------------------------------------------

def test_waiver_has_empty_state_container(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.waiver.get_matchups", return_value=df),
        patch("web.routes.waiver.get_stat_categories", return_value=[]),
    ):
        response = client.get("/waiver", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert 'id="waiver-table-container"' in body
    assert "Select one or more stat categories above to rank available players." in body


# ---------------------------------------------------------------------------
# TC7 — GET /waiver when get_matchups returns None → renders shell, no 500
# ---------------------------------------------------------------------------

def test_waiver_empty_matchups_renders_shell(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.waiver.get_matchups", return_value=None),
        patch("web.routes.waiver.get_stat_categories", return_value=[]),
    ):
        response = client.get("/waiver", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert "season may not have started" in response.text
