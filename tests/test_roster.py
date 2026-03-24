"""
Unit tests for data/roster.py.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from data import roster as roster_module

FIXTURES = Path(__file__).parent / "fixtures"
LEAGUE_KEY = "nhl.l.99999"
SESSION = MagicMock()
TEAM_KEY = "nhl.l.99999.t.1"


def load(filename: str) -> dict:
    with open(FIXTURES / filename) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# get_team_roster
# ---------------------------------------------------------------------------

def test_get_team_roster_excludes_ir():
    """IR+ player (nhl.p.5) must not appear in the result."""
    with patch("data.roster._get", return_value=load("team_roster.json")):
        result = roster_module.get_team_roster(SESSION, TEAM_KEY, week=20)

    keys = [p["player_key"] for p in result]
    assert "nhl.p.5" not in keys


def test_get_team_roster_includes_bench():
    """BN player (nhl.p.4 / William Nylander) must be included."""
    with patch("data.roster._get", return_value=load("team_roster.json")):
        result = roster_module.get_team_roster(SESSION, TEAM_KEY, week=20)

    slots = [p["roster_slot"] for p in result]
    assert "BN" in slots


def test_get_team_roster_count():
    """Fixture has 5 players: 3 active + 1 BN + 1 IR+ → should return 4."""
    with patch("data.roster._get", return_value=load("team_roster.json")):
        result = roster_module.get_team_roster(SESSION, TEAM_KEY, week=20)

    assert len(result) == 4


def test_get_team_roster_fields():
    with patch("data.roster._get", return_value=load("team_roster.json")):
        result = roster_module.get_team_roster(SESSION, TEAM_KEY, week=20)

    mcavid = next(p for p in result if p["player_key"] == "nhl.p.1")
    assert mcavid["player_name"] == "Connor McDavid"
    assert mcavid["team_abbr"] == "EDM"
    assert mcavid["display_position"] == "C"
    assert mcavid["roster_slot"] == "C"


def test_get_team_roster_single_player_handled():
    """xmltodict returns a dict (not list) when @count == 1 — _as_list must normalise."""
    with patch("data.roster._get", return_value=load("team_roster_single.json")):
        result = roster_module.get_team_roster(SESSION, TEAM_KEY, week=20)

    assert len(result) == 1
    assert result[0]["player_key"] == "nhl.p.1"


def test_get_team_roster_all_ir_slots_excluded():
    """All IR_SLOTS variants are excluded."""
    response = {
        "fantasy_content": {
            "team": {
                "roster": {
                    "players": {
                        "@count": "4",
                        "player": [
                            {"player_key": "p.1", "name": {"full": "A"}, "editorial_team_abbr": "BOS",
                             "display_position": "C", "selected_position": {"position": "IR"}},
                            {"player_key": "p.2", "name": {"full": "B"}, "editorial_team_abbr": "BOS",
                             "display_position": "D", "selected_position": {"position": "IR+"}},
                            {"player_key": "p.3", "name": {"full": "C"}, "editorial_team_abbr": "BOS",
                             "display_position": "LW", "selected_position": {"position": "IL"}},
                            {"player_key": "p.4", "name": {"full": "D"}, "editorial_team_abbr": "BOS",
                             "display_position": "G", "selected_position": {"position": "IL+"}},
                        ],
                    }
                }
            }
        }
    }
    with patch("data.roster._get", return_value=response):
        result = roster_module.get_team_roster(SESSION, TEAM_KEY, week=20)

    assert result == []


def test_get_team_roster_url():
    with patch("data.roster._get", return_value=load("team_roster.json")) as mock_get:
        roster_module.get_team_roster(SESSION, TEAM_KEY, week=7)

    url = mock_get.call_args[0][1]
    assert f"/team/{TEAM_KEY}/roster" in url
    assert "week=7" in url


def test_get_team_roster_empty_returns_empty_list():
    response = {
        "fantasy_content": {
            "team": {
                "roster": {
                    "players": {"@count": "0"}
                }
            }
        }
    }
    with patch("data.roster._get", return_value=response):
        result = roster_module.get_team_roster(SESSION, TEAM_KEY, week=20)

    assert result == []
