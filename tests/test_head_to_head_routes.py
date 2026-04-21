"""
Tests for GET /overview/head-to-head and GET /overview/head-to-head/table (ticket 016).

Uses an in-memory SQLite DB injected via dependency override on db_dep.
get_user_hockey_leagues, make_session, and get_matchups are mocked so no
live Yahoo API calls are made.
"""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fastapi.testclient import TestClient

from analysis.matchup_sim import simulate, tally
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


def _insert_session(conn, session_id="sid-h2h", league_key=None):
    conn.execute(
        "INSERT INTO user_sessions"
        " (session_id, access_token, refresh_token, expires_at, created_at, league_key)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, "acc-token", "ref-token", time.time() + 3600, time.time(), league_key),
    )
    conn.commit()


def _make_matchups_df() -> pd.DataFrame:
    """3 teams × 3 weeks × 3 stats fixture."""
    rows = []
    teams = [("t1", "Alpha"), ("t2", "Beta"), ("t3", "Gamma")]
    stat_values = {
        1: {
            "Alpha": {"Goals": 10.0, "Assists": 5.0, "Shots": 30.0},
            "Beta":  {"Goals": 7.0,  "Assists": 9.0, "Shots": 25.0},
            "Gamma": {"Goals": 5.0,  "Assists": 6.0, "Shots": 35.0},
        },
        2: {
            "Alpha": {"Goals": 8.0, "Assists": 8.0, "Shots": 28.0},
            "Beta":  {"Goals": 5.0, "Assists": 4.0, "Shots": 22.0},
            "Gamma": {"Goals": 3.0, "Assists": 3.0, "Shots": 18.0},
        },
        3: {
            "Alpha": {"Goals": 6.0, "Assists": 7.0, "Shots": 24.0},
            "Beta":  {"Goals": 9.0, "Assists": 6.0, "Shots": 20.0},
            "Gamma": {"Goals": 4.0, "Assists": 2.0, "Shots": 26.0},
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
# TC1 — GET /overview/head-to-head with selected league and matchups → 200
# ---------------------------------------------------------------------------

def test_head_to_head_returns_200_with_selectors(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get(
            "/overview/head-to-head", cookies={"session_id": "sid-h2h"}
        )

    assert response.status_code == 200
    body = response.text
    # Two team dropdowns with all team names
    assert body.count("Alpha") >= 2
    assert body.count("Beta") >= 2
    assert body.count("Gamma") >= 2
    # From/to week selectors
    assert "Week 1" in body
    assert "Week 3" in body
    # Initial comparison table present
    assert "<table" in body


# ---------------------------------------------------------------------------
# TC2 — GET /overview/head-to-head/table returns a fragment (no <html>)
# ---------------------------------------------------------------------------

def test_head_to_head_table_returns_fragment(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get(
            "/overview/head-to-head/table?team_a=Alpha&team_b=Beta&from_week=1&to_week=3",
            cookies={"session_id": "sid-h2h"},
        )

    assert response.status_code == 200
    body = response.text
    assert "<html" not in body
    assert "<table" in body


# ---------------------------------------------------------------------------
# TC3 — Fragment has correct winner highlighting and tally row
# ---------------------------------------------------------------------------

def test_head_to_head_table_winner_highlighting(ctx):
    """
    Weeks 1–3: Alpha averages Goals=(10+8+6)/3=8.0, Beta=(7+5+9)/3=7.0 → Alpha wins Goals.
    Confirms bg-green-100 appears on winner cells and tally row is present.
    """
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get(
            "/overview/head-to-head/table?team_a=Alpha&team_b=Beta&from_week=1&to_week=3",
            cookies={"session_id": "sid-h2h"},
        )

    assert response.status_code == 200
    body = response.text
    assert "bg-green-100" in body
    # Tally row present
    assert "wins" in body
    assert "ties" in body


# ---------------------------------------------------------------------------
# TC4 — Winner column and tally match matchup_sim output for known fixture
# ---------------------------------------------------------------------------

def test_head_to_head_table_matches_sim_output(ctx):
    """
    Verify that the rendered HTML winners and tally match simulate()/tally() output
    directly — i.e., the route and template agree with the analysis layer.
    """
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    # Compute expected values directly
    sim_df = simulate(df, "Alpha", "Beta", 1, 3)
    expected_tally = tally(sim_df, "Alpha", "Beta")

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get(
            "/overview/head-to-head/table?team_a=Alpha&team_b=Beta&from_week=1&to_week=3",
            cookies={"session_id": "sid-h2h"},
        )

    body = response.text
    # Each winner value from simulate() must appear in the rendered HTML
    for _, row in sim_df.iterrows():
        assert row["winner"] in body

    # Tally counts must appear in the rendered tally line
    assert str(expected_tally["Alpha"]) in body
    assert str(expected_tally["Beta"]) in body
    assert str(expected_tally["Tie"]) in body


# ---------------------------------------------------------------------------
# TC5 — bg-gray-100 appears on tied categories
# ---------------------------------------------------------------------------

def test_head_to_head_table_tie_cells_gray(ctx):
    """
    Build a fixture where one category is exactly tied between the two teams,
    and verify bg-gray-100 appears in the rendered fragment.
    """
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    # Alpha and Beta tied on Goals (both 5.0); Alpha wins Assists
    rows = [
        {"team_key": "t1", "team_name": "Alpha", "week": 1, "games_played": 7,
         "Goals": 5.0, "Assists": 8.0},
        {"team_key": "t2", "team_name": "Beta",  "week": 1, "games_played": 7,
         "Goals": 5.0, "Assists": 3.0},
    ]
    df = pd.DataFrame(rows)

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get(
            "/overview/head-to-head/table?team_a=Alpha&team_b=Beta&from_week=1&to_week=1",
            cookies={"session_id": "sid-h2h"},
        )

    assert response.status_code == 200
    body = response.text
    assert "bg-gray-100" in body
    assert "Tie" in body


# ---------------------------------------------------------------------------
# TC6 — GET /overview/head-to-head with NULL league_key → 302 to /
# ---------------------------------------------------------------------------

def test_head_to_head_no_league_redirects_to_home(ctx):
    conn, client = ctx
    _insert_session(conn)  # no league_key

    response = client.get(
        "/overview/head-to-head", cookies={"session_id": "sid-h2h"}
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/"


# ---------------------------------------------------------------------------
# TC7 — GET /overview/head-to-head with no session → 302 to /auth/login
# ---------------------------------------------------------------------------

def test_head_to_head_no_cookie_redirects_to_login(ctx):
    _, client = ctx
    response = client.get("/overview/head-to-head")
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# TC8 — from_week > to_week is swapped before calling simulate
# ---------------------------------------------------------------------------

def test_head_to_head_table_swaps_inverted_week_range(ctx):
    """
    from_week=3&to_week=1 must produce the same output as from_week=1&to_week=3
    (route swaps before calling simulate).
    """
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        r_inverted = client.get(
            "/overview/head-to-head/table?team_a=Alpha&team_b=Beta&from_week=3&to_week=1",
            cookies={"session_id": "sid-h2h"},
        )
        r_normal = client.get(
            "/overview/head-to-head/table?team_a=Alpha&team_b=Beta&from_week=1&to_week=3",
            cookies={"session_id": "sid-h2h"},
        )

    assert r_inverted.status_code == 200
    assert r_inverted.text == r_normal.text


# ---------------------------------------------------------------------------
# TC9 — Empty matchups renders shell with "Not enough team data" message
# ---------------------------------------------------------------------------

def test_head_to_head_empty_matchups_renders_shell(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=None),
    ):
        response = client.get(
            "/overview/head-to-head", cookies={"session_id": "sid-h2h"}
        )

    assert response.status_code == 200
    assert "Not enough team data" in response.text


# ---------------------------------------------------------------------------
# TC10 — In-page link present on leaderboard; back link present on head-to-head
# ---------------------------------------------------------------------------

def test_leaderboard_has_compare_link(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview", cookies={"session_id": "sid-h2h"})

    assert 'href="/overview/head-to-head"' in response.text


def test_head_to_head_has_back_link(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get(
            "/overview/head-to-head", cookies={"session_id": "sid-h2h"}
        )

    assert 'href="/overview"' in response.text
