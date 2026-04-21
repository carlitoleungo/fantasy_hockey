"""
QA-targeted tests for ticket 015 — gaps not covered by the engineer's test file.

Covers:
  - Row order (sorted by avg_rank ascending)
  - Positional correctness of bg-green-100 / bg-red-100 per cell
  - team_name and avg_rank cells must NOT carry color classes
  - Actual stat values appear in rendered HTML
  - HTMX attributes (hx-get / hx-target) present in shell template
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
# Shared helpers
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


def _insert_session(conn, session_id="sid-qa", league_key=None):
    conn.execute(
        "INSERT INTO user_sessions"
        " (session_id, access_token, refresh_token, expires_at, created_at, league_key)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, "acc-token", "ref-token", time.time() + 3600, time.time(), league_key),
    )
    conn.commit()


def _make_matchups_df() -> pd.DataFrame:
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
# QA-TC1 — Row order: best team (lowest avg_rank) is first in rendered table
# ---------------------------------------------------------------------------

def test_table_rows_sorted_by_avg_rank_ascending(ctx):
    """Week 2: Alpha wins all three stats → avg_rank=1.0 → should be first row."""
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview/table?week=2", cookies={"session_id": "sid-qa"})

    assert response.status_code == 200
    body = response.text
    alpha_pos = body.index("Alpha")
    beta_pos = body.index("Beta")
    gamma_pos = body.index("Gamma")
    assert alpha_pos < beta_pos < gamma_pos, (
        f"Expected Alpha < Beta < Gamma in HTML, got positions {alpha_pos}, {beta_pos}, {gamma_pos}"
    )


# ---------------------------------------------------------------------------
# QA-TC2 — Stat values appear in rendered HTML (not just column headers)
# ---------------------------------------------------------------------------

def test_table_renders_stat_values(ctx):
    """Actual numeric values from the fixture must appear in the fragment."""
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview/table?week=2", cookies={"session_id": "sid-qa"})

    body = response.text
    assert "8.0" in body    # Alpha Goals / Assists
    assert "28.0" in body   # Alpha Shots
    assert "5.0" in body    # Beta Goals
    assert "3.0" in body    # Gamma Goals / Assists


# ---------------------------------------------------------------------------
# QA-TC3 — Correct cells get color classes (positional check, week 2)
# ---------------------------------------------------------------------------

def test_table_color_classes_correct_position(ctx):
    """
    Week 2: Alpha wins every stat (rank 1 → bg-green-100), Gamma loses every
    stat (rank 3 == team_count → bg-red-100). Alpha's row must appear before
    the first bg-green-100; Gamma's team name must appear before bg-red-100.
    """
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview/table?week=2", cookies={"session_id": "sid-qa"})

    body = response.text

    # Alpha's team_name cell comes before bg-green-100 (its stat cells)
    assert body.index("Alpha") < body.index("bg-green-100"), (
        "bg-green-100 should appear after Alpha's team-name cell"
    )
    # Gamma's team_name cell comes before bg-red-100 (its stat cells)
    assert body.index("Gamma") < body.index("bg-red-100"), (
        "bg-red-100 should appear after Gamma's team-name cell"
    )
    # Alpha row (green) renders before Gamma row (red) since sorted ascending
    assert body.index("bg-green-100") < body.index("bg-red-100"), (
        "Alpha row (green) should render before Gamma row (red)"
    )


# ---------------------------------------------------------------------------
# QA-TC4 — team_name cells must NOT carry any bg-green / bg-red class
# ---------------------------------------------------------------------------

def test_team_name_cell_not_color_coded(ctx):
    """The team_name <td> must not receive a rank_color class."""
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview/table?week=2", cookies={"session_id": "sid-qa"})

    body = response.text
    # Color class must not appear on the team_name cell itself
    assert 'bg-green-100">Alpha' not in body, "team_name cell for Alpha must not have bg-green-100"
    assert 'bg-red-100">Gamma' not in body, "team_name cell for Gamma must not have bg-red-100"


# ---------------------------------------------------------------------------
# QA-TC5 — avg_rank cells must NOT carry any bg-green / bg-red class
# ---------------------------------------------------------------------------

def test_avg_rank_cell_not_color_coded(ctx):
    """The avg_rank final column must never get a rank_color class."""
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview/table?week=2", cookies={"session_id": "sid-qa"})

    body = response.text
    # avg_rank values for the 3-team fixture (week 2): 1.00, 2.00, 3.00
    assert 'bg-green-100">1.00' not in body, "avg_rank cell must not carry bg-green-100"
    assert 'bg-red-100">3.00' not in body, "avg_rank cell must not carry bg-red-100"


# ---------------------------------------------------------------------------
# QA-TC6 — Shell template has correct HTMX attributes
# ---------------------------------------------------------------------------

def test_shell_has_htmx_attributes(ctx):
    """GET /overview must render hx-get="/overview/table" and hx-target="#leaderboard-table"."""
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview", cookies={"session_id": "sid-qa"})

    body = response.text
    assert 'hx-get="/overview/table"' in body, "Week selector must have hx-get targeting fragment"
    assert 'hx-target="#leaderboard-table"' in body, "Week selector must target #leaderboard-table"


# ---------------------------------------------------------------------------
# QA-TC7 — "Overview" nav link present in page shell
# ---------------------------------------------------------------------------

def test_overview_nav_link_present(ctx):
    """GET /overview HTML must contain an Overview nav link and preserve existing links."""
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview", cookies={"session_id": "sid-qa"})

    body = response.text
    assert 'href="/overview"' in body
    assert 'href="/auth/logout"' in body
    assert 'href="/"' in body
    # Overview link must appear before logout link in the nav
    assert body.index('href="/overview"') < body.index('href="/auth/logout"'), (
        "Overview link must precede logout link in the nav"
    )
