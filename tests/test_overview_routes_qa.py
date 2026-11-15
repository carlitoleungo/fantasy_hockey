"""
QA-targeted tests for ticket 015 — gaps not covered by the engineer's test file.

Covers:
  - Row order (sorted by avg_rank ascending)
  - Positional correctness of the rank shading (s4 … none) per cell
  - team_name and avg_rank cells are never shaded
  - Actual stat values appear in rendered HTML
  - HTMX attributes (hx-get / hx-target) present in shell template
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fastapi.testclient import TestClient

from db.connection import db_dep
from tests.helpers import insert_session, make_db
from web.main import app


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _insert_session(conn, session_id="sid-qa", league_key=None):
    insert_session(conn, session_id, league_key)


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
    conn = make_db()

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

def _week2_fragment(ctx) -> str:
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
    return response.text


def test_table_renders_stat_values(ctx):
    """Weekly totals render as integers (counting stats), not 8.0."""
    body = _week2_fragment(ctx)
    assert '<td class="s4">8</td>' in body     # Alpha Goals / Assists
    assert '<td class="s4">28</td>' in body    # Alpha Shots
    assert '<td class="s2">5</td>' in body     # Beta Goals
    assert "<td>3</td>" in body                # Gamma Goals / Assists (last: no shade)
    assert "8.0<" not in body


# ---------------------------------------------------------------------------
# QA-TC3 — Shade levels land on the right rows (week 2)
# ---------------------------------------------------------------------------

def test_table_shading_correct_position(ctx):
    """
    Week 2: Alpha leads every stat (s4, bold), Beta is second (s2), Gamma is
    last (no shade). Rows are ordered by avg rank, so Alpha's s4 cells come
    first and Gamma's row has no shaded cells.
    """
    body = _week2_fragment(ctx)
    desktop = body[: body.index('class="pg-head"')]
    alpha, beta, gamma = (desktop.index(n) for n in ("Alpha", "Beta", "Gamma"))
    assert alpha < beta < gamma
    assert desktop[alpha:beta].count('class="s4"') == 3
    assert desktop[beta:gamma].count('class="s2"') == 3
    gamma_row = desktop[gamma: desktop.index("</tr>", gamma)]
    assert 'class="s' not in gamma_row


# ---------------------------------------------------------------------------
# QA-TC4 — team name cells are never shaded
# ---------------------------------------------------------------------------

def test_team_name_cell_not_shaded(ctx):
    body = _week2_fragment(ctx)
    assert '<td class="l sticky-col"><span class="lb-team">Alpha</span></td>' in body


# ---------------------------------------------------------------------------
# QA-TC5 — avg_rank cells are never shaded; leader gets the accent block
# ---------------------------------------------------------------------------

def test_avg_rank_cell_not_shaded(ctx):
    body = _week2_fragment(ctx)
    # avg_rank values for the 3-team fixture (week 2): 1.00, 2.00, 3.00
    assert '<td class="avg">1.00</td>' in body
    assert '<td class="avg">3.00</td>' in body
    assert '<span class="pos pos-top">1</span>' in body


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
