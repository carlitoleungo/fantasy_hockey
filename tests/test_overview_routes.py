"""
Tests for GET /overview and GET /overview/table (ticket 015).

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
    teams = [
        ("t1", "Alpha"),
        ("t2", "Beta"),
        ("t3", "Gamma"),
    ]
    stat_values = {
        # week 1: Alpha best Goals, Beta best Assists, Gamma best Shots
        1: {
            "Alpha": {"Goals": 10.0, "Assists": 5.0, "Shots": 30.0},
            "Beta":  {"Goals": 7.0,  "Assists": 9.0, "Shots": 25.0},
            "Gamma": {"Goals": 5.0,  "Assists": 6.0, "Shots": 35.0},
        },
        # week 2: clear winner across all stats
        2: {
            "Alpha": {"Goals": 8.0, "Assists": 8.0, "Shots": 28.0},
            "Beta":  {"Goals": 5.0, "Assists": 4.0, "Shots": 22.0},
            "Gamma": {"Goals": 3.0, "Assists": 3.0, "Shots": 18.0},
        },
    }
    for week, team_stats in stat_values.items():
        for key, name in teams:
            row = {
                "team_key": key,
                "team_name": name,
                "week": week,
                "games_played": 7,
            }
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
# TC1 — GET /overview with selected league and matchups data returns 200
# ---------------------------------------------------------------------------

def test_overview_returns_200_with_leaderboard(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert "Alpha" in body
    assert "Beta" in body
    assert "Gamma" in body
    assert "Goals" in body
    assert "Assists" in body
    assert "Shots" in body
    assert "avg_rank" in body.lower() or "Avg Rank" in body


# ---------------------------------------------------------------------------
# TC2 — GET /overview/table returns a fragment (no <html> wrapper)
# ---------------------------------------------------------------------------

def test_overview_table_returns_fragment(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get(
            "/overview/table?week=1",
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    body = response.text
    assert "<html" not in body
    assert "<table" in body


# ---------------------------------------------------------------------------
# TC3 — Fragment contains bg-green-100 and bg-red-100 in expected positions
# ---------------------------------------------------------------------------

def test_overview_table_has_color_classes(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get(
            "/overview/table?week=1",
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    body = response.text
    assert "bg-green-100" in body
    assert "bg-red-100" in body


# ---------------------------------------------------------------------------
# TC4 — GET /overview with NULL league_key → 302 to /
# ---------------------------------------------------------------------------

def test_overview_no_league_redirects_to_home(ctx):
    conn, client = ctx
    _insert_session(conn)  # no league_key

    response = client.get("/overview", cookies={"session_id": "sid-test"})

    assert response.status_code == 302
    assert response.headers["location"] == "/"


# ---------------------------------------------------------------------------
# TC5 — GET /overview with no session cookie → 302 to /auth/login
# ---------------------------------------------------------------------------

def test_overview_no_cookie_redirects_to_login(ctx):
    _, client = ctx
    response = client.get("/overview")
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# TC6 — GET /overview when get_matchups returns None → renders empty state
# ---------------------------------------------------------------------------

def test_overview_empty_matchups_renders_shell(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=None),
    ):
        response = client.get("/overview", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert "season starts" in response.text or "No matchup data" in response.text


# ---------------------------------------------------------------------------
# TC7 — Ticket 025: authenticated /overview "Compare two teams" link points at
#       the authenticated head-to-head route, not the demo one
# ---------------------------------------------------------------------------

def test_overview_compare_link_targets_authenticated_route(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview", cookies={"session_id": "sid-test"})

    body = response.text
    assert 'href="/overview/head-to-head"' in body
    assert 'href="/demo/overview/head-to-head"' not in body


# ---------------------------------------------------------------------------
# TC8 — Ticket 025: authenticated /overview/head-to-head "Back to Leaderboard"
#       link points at the authenticated overview route, not the demo one
# ---------------------------------------------------------------------------

def test_head_to_head_back_link_targets_authenticated_route(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get(
            "/overview/head-to-head", cookies={"session_id": "sid-test"}
        )

    body = response.text
    # Scope to the "Back to Leaderboard" anchor — base.html's nav also links
    # to /overview, so a bare href="/overview" substring is ambiguous.
    back_link = (
        'href="/overview" class="text-sm text-gray-500 hover:text-gray-700">'
        "&larr; Back to Leaderboard"
    )
    demo_back_link = (
        'href="/demo/overview" class="text-sm text-gray-500 hover:text-gray-700">'
        "&larr; Back to Leaderboard"
    )
    assert back_link in body
    assert demo_back_link not in body


# ---------------------------------------------------------------------------
# TC9 — Ticket 036a: /overview has not adopted shell_context yet, so base.html
# must fall back to the authenticated nav (no regression before 036b)
# ---------------------------------------------------------------------------

def test_overview_renders_authenticated_nav_by_default(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")
    df = _make_matchups_df()

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=df),
    ):
        response = client.get("/overview", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    nav = response.text.split("<nav", 1)[1].split("</nav>", 1)[0]
    positions = [nav.index(f'href="/{p}"') for p in ("overview", "waiver", "projection")]
    assert positions == sorted(positions)
    assert 'href="/auth/logout"' in nav
    assert 'href="/auth/login"' not in nav
