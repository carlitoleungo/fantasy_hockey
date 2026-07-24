"""
QA supplementary tests for the ticket-034 roster-breakdown split.

The Engineer's tests cover the happy path (a mixed roster of skaters and
goalies, abbreviated headers and names). These close the edge-case gaps in the
new partition logic:

  * a single-token player name must not be abbreviated (and must not raise)
  * a goalie-only roster must not emit an empty "Skaters" table
  * multi-position players are classified correctly: "LW,RW" is a skater and
    "C,G" is a goalie (`is_goalie` matches whole comma tokens, so it survives
    a position string with more than one entry)
  * a league with no enabled goaltending categories still shows its goalies
    (documented behaviour: Player/GR only, players are not hidden)

All data-layer functions are mocked — no live Yahoo/NHL API calls.
Patch targets are `web.routes.projection.*` (the importing module's namespace),
per docs/DECISIONS.md 2026-03-03 / docs/LEARNINGS.md.
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
T1 = "419.l.11111.t.1"
T2 = "419.l.11111.t.2"

TEAMS = [
    {"team_key": T1, "team_id": "1", "team_name": "Alpha", "manager_name": "Ann"},
    {"team_key": T2, "team_id": "2", "team_name": "Beta", "manager_name": "Bob"},
]
SETTINGS = {"current_week": 14, "start_week": 1, "end_week": 24}
STAT_CATEGORIES = [
    {"stat_id": "1", "stat_name": "Goals", "abbreviation": "G",
     "stat_group": "offense", "is_enabled": True},
    {"stat_id": "23", "stat_name": "Goals Against Average", "abbreviation": "GAA",
     "stat_group": "goaltending", "is_enabled": True},
]
SKATERS_ONLY_CATEGORIES = [STAT_CATEGORIES[0]]
SCOREBOARD = {
    "week_start": "2026-03-23",
    "week_end": "2026-03-29",
    "matchups": [{"team_a_key": T1, "team_b_key": T2}],
}
LIVE_STATS = [
    {"team_key": T1, "team_name": "Alpha", "week": 14, "games_played": 3,
     "Goals": 5.0, "Goals Against Average": 2.5},
    {"team_key": T2, "team_name": "Beta", "week": 14, "games_played": 3,
     "Goals": 5.0, "Goals Against Average": 2.5},
]
OPP_ROSTER = [
    {"player_key": "p.opp", "player_name": "Opp Skater", "team_abbr": "BOS",
     "display_position": "LW", "roster_slot": "LW"},
]
LASTMONTH = {
    "p.opp": {"Goals": 5.0, "games_played": 10},
    "p.one": {"Goals": 10.0, "games_played": 10},
    "p.wing": {"Goals": 10.0, "games_played": 10},
    "p.hybrid": {"Goals Against Average": 3.10, "games_played": 10},
    "p.goalie": {"Goals Against Average": 2.75, "games_played": 10},
}
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
def client():
    conn = _make_db()

    def override_db():
        yield conn

    app.dependency_overrides[db_dep] = override_db
    test_client = TestClient(app, follow_redirects=False)
    yield test_client
    app.dependency_overrides.clear()
    conn.close()


def _run(client, my_roster, categories=STAT_CATEGORIES):
    with (
        patch("web.routes.projection.make_session", return_value=MagicMock()),
        patch("web.routes.projection.get_settings_and_categories",
              return_value=(SETTINGS, categories)),
        patch("web.routes.projection.get_teams", return_value=TEAMS),
        patch("web.routes.projection.get_all_teams_week_stats", return_value=LIVE_STATS),
        patch("web.routes.projection.scoreboard_module.get_current_matchup",
              return_value=SCOREBOARD),
        patch("web.routes.projection.roster_module.get_team_roster",
              side_effect=[my_roster, OPP_ROSTER]),
        patch("web.routes.projection.players_module.get_players_lastmonth_stats",
              return_value=LASTMONTH),
        patch("web.routes.projection.schedule_module.get_remaining_games",
              return_value=GAMES_REMAINING),
    ):
        return client.get(f"/projection/matchup?team_key={T1}",
                          cookies={"session_id": "sid-test"})


def _sections(body: str) -> list[tuple[str, str]]:
    """[(section_label, table_html)] for every roster-breakdown table."""
    tail = body.split("Roster Breakdown", 1)[1]
    return re.findall(
        r'<p[^>]*>(Skaters|Goalies)</p>\s*<div[^>]*>\s*(<table.*?</table>)', tail, re.S
    )


def _headers(table_html: str) -> list[str]:
    return re.findall(r"<th(?:\s[^>]*)?>\s*(.*?)\s*</th>", table_html, re.S)


def test_single_token_player_name_is_not_abbreviated(client):
    """A mononym has no surname to fall back on — render it whole, don't crash."""
    roster = [
        {"player_key": "p.one", "player_name": "Cal", "team_abbr": "EDM",
         "display_position": "C", "roster_slot": "C"},
    ]
    resp = _run(client, roster)
    assert resp.status_code == 200
    skaters = _sections(resp.text)[0][1]
    squashed = re.sub(r"\s+", " ", skaters)
    assert ">Cal<" in re.sub(r"\s+", "", skaters)
    assert "C. " not in squashed
    assert 'title="Cal"' in skaters


def test_goalie_only_roster_renders_no_skaters_table(client):
    """A team with no skaters must not emit an empty Skaters table."""
    roster = [
        {"player_key": "p.goalie", "player_name": "Jake Allen", "team_abbr": "EDM",
         "display_position": "G", "roster_slot": "G"},
    ]
    resp = _run(client, roster)
    assert resp.status_code == 200
    labels = [label for label, _ in _sections(resp.text)]
    # My team: goalies only. Opponent (skater only): skaters only.
    assert labels == ["Goalies", "Skaters"]


def test_is_goalie_matches_whole_position_tokens(client):
    """`LW,RW` is a skater; `C,G` is a goalie. Nothing else exercises a
    display_position with more than one token against the partition."""
    roster = [
        {"player_key": "p.wing", "player_name": "Winger Guy", "team_abbr": "EDM",
         "display_position": "LW,RW", "roster_slot": "LW"},
        {"player_key": "p.hybrid", "player_name": "Hybrid Guy", "team_abbr": "EDM",
         "display_position": "C,G", "roster_slot": "G"},
    ]
    resp = _run(client, roster)
    assert resp.status_code == 200
    sections = _sections(resp.text)
    my_skaters = sections[0][1]
    my_goalies = sections[1][1]
    assert "W. Guy" in re.sub(r"\s+", " ", my_skaters)
    assert "H. Guy" not in re.sub(r"\s+", " ", my_skaters)
    assert "H. Guy" in re.sub(r"\s+", " ", my_goalies)
    assert "3.10" in my_goalies


def test_league_without_goaltending_categories_still_lists_goalies(client):
    """Documented behaviour: with no enabled goaltending category the goalie
    table degrades to Player/GR rather than dropping the players."""
    roster = [
        {"player_key": "p.goalie", "player_name": "Jake Allen", "team_abbr": "EDM",
         "display_position": "G", "roster_slot": "G"},
        {"player_key": "p.wing", "player_name": "Winger Guy", "team_abbr": "EDM",
         "display_position": "LW", "roster_slot": "LW"},
    ]
    resp = _run(client, roster, categories=SKATERS_ONLY_CATEGORIES)
    assert resp.status_code == 200
    sections = _sections(resp.text)
    labels = [label for label, _ in sections]
    assert labels == ["Skaters", "Goalies", "Skaters"]
    assert _headers(sections[1][1]) == ["Player", "GR"]
    assert "J. Allen" in re.sub(r"\s+", " ", sections[1][1])
