"""
QA supplementary tests for GET /projection/matchup (ticket 030).

The Engineer's tests (test_projection_matchup_route.py) assert that bg-green-100
appears somewhere in the category table for the my-team-wins case. These tests
close the gap: they verify the winner highlight lands on the CORRECT column for
the opponent-win case and that a tie applies no green highlight to either cell.

All data-layer functions are mocked — no live Yahoo/NHL API calls.
"""

from __future__ import annotations

import re
import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from db.connection import db_dep
from web.main import app

LEAGUE_KEY = "419.l.11111"
T1 = "419.l.11111.t.1"  # Alpha (my team)
T2 = "419.l.11111.t.2"  # Beta (opponent)

TEAMS = [
    {"team_key": T1, "team_id": "1", "team_name": "Alpha", "manager_name": "Ann"},
    {"team_key": T2, "team_id": "2", "team_name": "Beta", "manager_name": "Bob"},
]
SETTINGS = {"current_week": 14, "start_week": 1, "end_week": 24}
STAT_CATEGORIES = [
    {"stat_id": "1", "stat_name": "Goals", "abbreviation": "G",
     "stat_group": "skaters", "is_enabled": True},
]
SCOREBOARD = {
    "week_start": "2026-03-23",
    "week_end": "2026-03-29",
    "matchups": [{"team_a_key": T1, "team_b_key": T2}],
}
LIVE_STATS = [
    {"team_key": T1, "team_name": "Alpha", "week": 14, "games_played": 3, "Goals": 5.0},
    {"team_key": T2, "team_name": "Beta", "week": 14, "games_played": 3, "Goals": 5.0},
]
MY_ROSTER = [
    {"player_key": "p.mine", "player_name": "My Skater", "team_abbr": "EDM",
     "display_position": "C", "roster_slot": "C"},
]
OPP_ROSTER = [
    {"player_key": "p.opp", "player_name": "Opp Skater", "team_abbr": "BOS",
     "display_position": "LW", "roster_slot": "LW"},
]
GAMES_REMAINING = {"EDM": 3, "BOS": 2}


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE user_sessions (
            session_id TEXT PRIMARY KEY, access_token TEXT, refresh_token TEXT,
            expires_at REAL, created_at REAL, league_key TEXT
        );
        CREATE TABLE oauth_states (state TEXT PRIMARY KEY, expires_at REAL);
        """
    )
    conn.execute(
        "INSERT INTO user_sessions VALUES (?, ?, ?, ?, ?, ?)",
        ("sid-test", "acc", "ref", time.time() + 3600, time.time(), LEAGUE_KEY),
    )
    conn.commit()
    return conn


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


def _run(client, lastmonth):
    with (
        patch("web.routes.projection.make_session", return_value=MagicMock()),
        patch("web.routes.projection.get_settings_and_categories",
              return_value=(SETTINGS, STAT_CATEGORIES)),
        patch("web.routes.projection.get_teams", return_value=TEAMS),
        patch("web.routes.projection.get_all_teams_week_stats", return_value=LIVE_STATS),
        patch("web.routes.projection.scoreboard_module.get_current_matchup",
              return_value=SCOREBOARD),
        patch("web.routes.projection.roster_module.get_team_roster",
              side_effect=[MY_ROSTER, OPP_ROSTER]),
        patch("web.routes.projection.players_module.get_players_lastmonth_stats",
              return_value=lastmonth),
        patch("web.routes.projection.schedule_module.get_remaining_games",
              return_value=GAMES_REMAINING),
    ):
        return client.get(f"/projection/matchup?team_key={T1}",
                          cookies={"session_id": "sid-test"})


def _category_row(body: str, category: str) -> str:
    """Return the <tr> for a given category row in the comparison table."""
    # The comparison table rows contain two <td> cells after the category cell.
    m = re.search(
        r"<tr[^>]*>\s*<td[^>]*>\s*" + re.escape(category) + r"\s*</td>(.*?)</tr>",
        body,
        re.S,
    )
    assert m, f"category row for {category!r} not found"
    return m.group(1)


def test_opponent_win_highlights_opponent_column(ctx):
    """When the opponent wins a category, the green highlight is on the opponent
    cell and the my-team cell is greyed — not the reverse."""
    _, client = ctx
    # My proj Goals = 5 + 0/10*3 = 5.0 ; Opp proj = 5 + 100/10*2 = 25.0 -> opp wins
    lastmonth = {
        "p.mine": {"Goals": 0.0, "games_played": 10},
        "p.opp": {"Goals": 100.0, "games_played": 10},
    }
    resp = _run(client, lastmonth)
    assert resp.status_code == 200
    row = _category_row(resp.text, "Goals")
    cells = re.findall(r"<td[^>]*>.*?</td>", row, re.S)
    assert len(cells) == 2, row
    my_cell, opp_cell = cells
    # my cell shows 5.0 and is greyed; opp cell shows 25.0 and is highlighted
    assert "5.0" in my_cell and "text-gray-400" in my_cell and "bg-green-100" not in my_cell
    assert "25.0" in opp_cell and "bg-green-100" in opp_cell


def test_tie_category_has_no_green_highlight(ctx):
    """A tied category greys/neutralises both cells; neither gets bg-green-100."""
    _, client = ctx
    # Both project to 5 + 50/10*rem: my = 5+15=20 (rem 3), opp = 5+10=15 (rem 2)?
    # To force an exact tie, zero out contributions so both stay at current 5.0.
    lastmonth = {
        "p.mine": {"Goals": 0.0, "games_played": 10},
        "p.opp": {"Goals": 0.0, "games_played": 10},
    }
    resp = _run(client, lastmonth)
    assert resp.status_code == 200
    row = _category_row(resp.text, "Goals")
    assert "bg-green-100" not in row
    cells = re.findall(r"<td[^>]*>.*?</td>", row, re.S)
    assert len(cells) == 2
    assert "5.0" in cells[0] and "5.0" in cells[1]
