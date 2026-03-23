"""
Unit tests for data/client.py.

The Yahoo API layer is tested by patching _get() to return fixture dicts
(the already-parsed xmltodict output). This tests all the dict-navigation and
transformation logic without needing HTTP or XML parsing.

Fixture files live in tests/fixtures/ and represent what xmltodict produces
from real Yahoo API XML responses.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data import client

FIXTURES = Path(__file__).parent / "fixtures"
LEAGUE_KEY = "nhl.l.99999"

# A session object — only needed as a pass-through argument since _get is mocked
SESSION = MagicMock()


def load(filename: str) -> dict:
    with open(FIXTURES / filename) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# get_league_settings()
# ---------------------------------------------------------------------------

def test_get_league_settings_returns_int_weeks():
    with patch("data.client._get", return_value=load("league_settings.json")):
        result = client.get_league_settings(SESSION, LEAGUE_KEY)

    assert result["current_week"] == 5
    assert result["start_week"] == 1
    assert result["end_week"] == 25
    assert all(isinstance(v, int) for v in result.values())


def test_get_league_settings_calls_correct_url():
    with patch("data.client._get", return_value=load("league_settings.json")) as mock_get:
        client.get_league_settings(SESSION, LEAGUE_KEY)

    url = mock_get.call_args[0][1]
    assert f"/league/{LEAGUE_KEY}/settings" in url


# ---------------------------------------------------------------------------
# get_stat_categories()
# ---------------------------------------------------------------------------

def test_get_stat_categories_count():
    with patch("data.client._get", return_value=load("league_settings.json")):
        result = client.get_stat_categories(SESSION, LEAGUE_KEY)

    # Fixture has 4 stats: Goals, Assists, Points (display), Shots on Goal
    assert len(result) == 4


def test_get_stat_categories_enabled_flags():
    with patch("data.client._get", return_value=load("league_settings.json")):
        result = client.get_stat_categories(SESSION, LEAGUE_KEY)

    by_name = {c["stat_name"]: c for c in result}
    assert by_name["Goals"]["is_enabled"] is True
    assert by_name["Assists"]["is_enabled"] is True
    assert by_name["Points"]["is_enabled"] is False      # is_only_display_stat = "1"
    assert by_name["Shots on Goal"]["is_enabled"] is True


def test_get_stat_categories_fields():
    with patch("data.client._get", return_value=load("league_settings.json")):
        result = client.get_stat_categories(SESSION, LEAGUE_KEY)

    goals = next(c for c in result if c["stat_name"] == "Goals")
    assert goals["stat_id"] == "1"
    assert goals["abbreviation"] == "G"
    assert goals["stat_group"] == "offense"


def test_get_stat_categories_multi_position_type():
    """
    Assists fixture uses a list for stat_position_type (multiple position types).
    Ensures _as_list() is called and is_only_display_stat is checked across all.
    """
    with patch("data.client._get", return_value=load("league_settings.json")):
        result = client.get_stat_categories(SESSION, LEAGUE_KEY)

    assists = next(c for c in result if c["stat_name"] == "Assists")
    assert assists["is_enabled"] is True


def test_get_stat_categories_calls_correct_url():
    with patch("data.client._get", return_value=load("league_settings.json")) as mock_get:
        client.get_stat_categories(SESSION, LEAGUE_KEY)

    url = mock_get.call_args[0][1]
    assert f"/league/{LEAGUE_KEY}/settings" in url


# ---------------------------------------------------------------------------
# get_teams()
# ---------------------------------------------------------------------------

def test_get_teams_returns_two_teams():
    with patch("data.client._get", return_value=load("league_teams.json")):
        result = client.get_teams(SESSION, LEAGUE_KEY)

    assert len(result) == 2


def test_get_teams_fields():
    with patch("data.client._get", return_value=load("league_teams.json")):
        result = client.get_teams(SESSION, LEAGUE_KEY)

    alpha = next(t for t in result if t["team_name"] == "Team Alpha")
    assert alpha["team_key"] == "nhl.l.99999.t.1"
    assert alpha["team_id"] == "1"
    assert alpha["manager_name"] == "Alice"


def test_get_teams_single_team_is_wrapped_in_list():
    """
    When @count == 1, xmltodict returns a dict not a list.
    _as_list() must normalise it to a one-element list.
    """
    with patch("data.client._get", return_value=load("league_teams_single.json")):
        result = client.get_teams(SESSION, LEAGUE_KEY)

    assert len(result) == 1
    assert result[0]["team_name"] == "Team Alpha"


def test_get_teams_calls_correct_url():
    with patch("data.client._get", return_value=load("league_teams.json")) as mock_get:
        client.get_teams(SESSION, LEAGUE_KEY)

    url = mock_get.call_args[0][1]
    assert f"/league/{LEAGUE_KEY}/teams" in url


# ---------------------------------------------------------------------------
# get_team_week_stats()
# ---------------------------------------------------------------------------

STAT_CATEGORIES = [
    {"stat_id": "1", "stat_name": "Goals",        "abbreviation": "G",   "stat_group": "offense", "is_enabled": True},
    {"stat_id": "2", "stat_name": "Assists",       "abbreviation": "A",   "stat_group": "offense", "is_enabled": True},
    {"stat_id": "3", "stat_name": "Points",        "abbreviation": "Pts", "stat_group": "offense", "is_enabled": False},
    {"stat_id": "7", "stat_name": "Shots on Goal", "abbreviation": "SOG", "stat_group": "offense", "is_enabled": True},
]


def test_get_team_week_stats_enabled_values():
    with patch("data.client._get", return_value=load("team_week_stats.json")):
        result = client.get_team_week_stats(SESSION, "nhl.l.99999.t.1", 1, STAT_CATEGORIES)

    assert result["Goals"] == 10.0
    assert result["Assists"] == 25.0


def test_get_team_week_stats_dash_coerced_to_zero():
    """stat_id '7' (Shots on Goal) has value '-' in the fixture."""
    with patch("data.client._get", return_value=load("team_week_stats.json")):
        result = client.get_team_week_stats(SESSION, "nhl.l.99999.t.1", 1, STAT_CATEGORIES)

    assert result["Shots on Goal"] == 0.0


def test_get_team_week_stats_games_played_extracted():
    """stat_id '0' should become games_played (int), not a stat column."""
    with patch("data.client._get", return_value=load("team_week_stats.json")):
        result = client.get_team_week_stats(SESSION, "nhl.l.99999.t.1", 1, STAT_CATEGORIES)

    assert result["games_played"] == 5


def test_get_team_week_stats_display_stat_excluded():
    """Points (stat_id '3') has is_enabled=False and must not appear in the output."""
    with patch("data.client._get", return_value=load("team_week_stats.json")):
        result = client.get_team_week_stats(SESSION, "nhl.l.99999.t.1", 1, STAT_CATEGORIES)

    assert "Points" not in result


def test_get_team_week_stats_unknown_stat_excluded():
    """stat_id '99' is in the fixture but not in stat_categories — must be ignored."""
    with patch("data.client._get", return_value=load("team_week_stats.json")):
        result = client.get_team_week_stats(SESSION, "nhl.l.99999.t.1", 1, STAT_CATEGORIES)

    # No 'Unknown Stat ID' keys — unlike the notebook, we silently skip unknowns
    assert not any("Unknown" in str(k) for k in result)
    assert "99" not in result


def test_get_team_week_stats_identity_fields():
    with patch("data.client._get", return_value=load("team_week_stats.json")):
        result = client.get_team_week_stats(SESSION, "nhl.l.99999.t.1", 1, STAT_CATEGORIES)

    assert result["team_key"] == "nhl.l.99999.t.1"
    assert result["week"] == 1


def test_get_team_week_stats_calls_correct_url():
    with patch("data.client._get", return_value=load("team_week_stats.json")) as mock_get:
        client.get_team_week_stats(SESSION, "nhl.l.99999.t.1", 3, STAT_CATEGORIES)

    url = mock_get.call_args[0][1]
    assert "/team/nhl.l.99999.t.1/stats" in url
    assert "week=3" in url


def test_get_team_week_stats_single_stat_handled():
    """
    If xmltodict collapses the stat list to a single dict (one-stat league,
    unlikely but theoretically possible), _as_list() must handle it.
    """
    single_stat_response = {
        "fantasy_content": {
            "team": {
                "team_key": "nhl.l.99999.t.1",
                "team_stats": {
                    "stats": {
                        "stat": {"stat_id": "1", "value": "7"}
                    }
                }
            }
        }
    }
    with patch("data.client._get", return_value=single_stat_response):
        result = client.get_team_week_stats(SESSION, "nhl.l.99999.t.1", 1, STAT_CATEGORIES)

    assert result["Goals"] == 7.0


def test_get_team_week_stats_none_coerced_to_zero():
    """stat value of None (not just '-') should be coerced to 0."""
    response = {
        "fantasy_content": {
            "team": {
                "team_key": "nhl.l.99999.t.1",
                "team_stats": {
                    "stats": {
                        "stat": [
                            {"stat_id": "0", "value": None},
                            {"stat_id": "1", "value": None},
                            {"stat_id": "2", "value": "15"},
                        ]
                    }
                }
            }
        }
    }
    with patch("data.client._get", return_value=response):
        result = client.get_team_week_stats(SESSION, "nhl.l.99999.t.1", 1, STAT_CATEGORIES)

    assert result["games_played"] == 0
    assert result["Goals"] == 0.0
    assert result["Assists"] == 15.0


# ---------------------------------------------------------------------------
# get_all_teams_week_stats()
# ---------------------------------------------------------------------------

def test_get_all_teams_week_stats_returns_all_teams():
    with patch("data.client._get", return_value=load("league_teams_stats_week.json")):
        result = client.get_all_teams_week_stats(SESSION, LEAGUE_KEY, 1, STAT_CATEGORIES)

    assert len(result) == 2
    names = {r["team_name"] for r in result}
    assert names == {"Team Alpha", "Team Beta"}


def test_get_all_teams_week_stats_values():
    with patch("data.client._get", return_value=load("league_teams_stats_week.json")):
        result = client.get_all_teams_week_stats(SESSION, LEAGUE_KEY, 1, STAT_CATEGORIES)

    alpha = next(r for r in result if r["team_name"] == "Team Alpha")
    assert alpha["Goals"] == 10.0
    assert alpha["Assists"] == 25.0
    assert alpha["games_played"] == 5
    assert alpha["Shots on Goal"] == 0.0  # '-' coerced

    beta = next(r for r in result if r["team_name"] == "Team Beta")
    assert beta["Goals"] == 8.0
    assert beta["Shots on Goal"] == 120.0


def test_get_all_teams_week_stats_excludes_display_stats():
    with patch("data.client._get", return_value=load("league_teams_stats_week.json")):
        result = client.get_all_teams_week_stats(SESSION, LEAGUE_KEY, 1, STAT_CATEGORIES)

    for row in result:
        assert "Points" not in row


def test_get_all_teams_week_stats_single_team():
    with patch("data.client._get", return_value=load("league_teams_stats_week_single.json")):
        result = client.get_all_teams_week_stats(SESSION, LEAGUE_KEY, 1, STAT_CATEGORIES)

    assert len(result) == 1
    assert result[0]["team_name"] == "Team Alpha"


def test_get_all_teams_week_stats_none_values():
    with patch("data.client._get", return_value=load("league_teams_stats_week_nulls.json")):
        result = client.get_all_teams_week_stats(SESSION, LEAGUE_KEY, 1, STAT_CATEGORIES)

    assert result[0]["games_played"] == 0
    assert result[0]["Goals"] == 0.0
    assert result[0]["Assists"] == 15.0


def test_get_all_teams_week_stats_calls_correct_url():
    with patch("data.client._get", return_value=load("league_teams_stats_week.json")) as mock_get:
        client.get_all_teams_week_stats(SESSION, LEAGUE_KEY, 3, STAT_CATEGORIES)

    url = mock_get.call_args[0][1]
    assert f"/league/{LEAGUE_KEY}/teams/stats" in url
    assert "week=3" in url


def test_get_all_teams_week_stats_includes_week_in_rows():
    with patch("data.client._get", return_value=load("league_teams_stats_week.json")):
        result = client.get_all_teams_week_stats(SESSION, LEAGUE_KEY, 5, STAT_CATEGORIES)

    for row in result:
        assert row["week"] == 5
