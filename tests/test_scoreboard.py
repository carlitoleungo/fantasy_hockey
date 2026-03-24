"""
Unit tests for data/scoreboard.py.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data import scoreboard

FIXTURES = Path(__file__).parent / "fixtures"
LEAGUE_KEY = "nhl.l.99999"
SESSION = MagicMock()


def load(filename: str) -> dict:
    with open(FIXTURES / filename) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# get_current_matchup
# ---------------------------------------------------------------------------

def test_get_current_matchup_week_dates():
    with patch("data.scoreboard._get", return_value=load("league_scoreboard.json")):
        result = scoreboard.get_current_matchup(SESSION, LEAGUE_KEY, week=20)

    assert result["week_start"] == "2026-03-23"
    assert result["week_end"] == "2026-03-29"


def test_get_current_matchup_returns_all_pairings():
    with patch("data.scoreboard._get", return_value=load("league_scoreboard.json")):
        result = scoreboard.get_current_matchup(SESSION, LEAGUE_KEY, week=20)

    assert len(result["matchups"]) == 2


def test_get_current_matchup_team_keys():
    with patch("data.scoreboard._get", return_value=load("league_scoreboard.json")):
        result = scoreboard.get_current_matchup(SESSION, LEAGUE_KEY, week=20)

    first = result["matchups"][0]
    assert first["team_a_key"] == "nhl.l.99999.t.1"
    assert first["team_b_key"] == "nhl.l.99999.t.2"

    second = result["matchups"][1]
    assert second["team_a_key"] == "nhl.l.99999.t.3"
    assert second["team_b_key"] == "nhl.l.99999.t.4"


def test_get_current_matchup_single_matchup_wrapped():
    """xmltodict returns a dict (not list) when @count == 1 — _as_list must normalise."""
    with patch("data.scoreboard._get", return_value=load("league_scoreboard_single.json")):
        result = scoreboard.get_current_matchup(SESSION, LEAGUE_KEY, week=20)

    assert len(result["matchups"]) == 1
    assert result["matchups"][0]["team_a_key"] == "nhl.l.99999.t.1"
    assert result["matchups"][0]["team_b_key"] == "nhl.l.99999.t.2"


def test_get_current_matchup_url():
    with patch("data.scoreboard._get", return_value=load("league_scoreboard.json")) as mock_get:
        scoreboard.get_current_matchup(SESSION, LEAGUE_KEY, week=5)

    url = mock_get.call_args[0][1]
    assert f"/league/{LEAGUE_KEY}/scoreboard" in url
    assert "week=5" in url


def test_get_current_matchup_raises_on_missing_dates():
    bad_response = {
        "fantasy_content": {
            "league": {
                "scoreboard": {
                    "matchups": {
                        "@count": "1",
                        "matchup": {
                            "teams": {
                                "team": [
                                    {"team_key": "nhl.l.99999.t.1"},
                                    {"team_key": "nhl.l.99999.t.2"},
                                ]
                            }
                        },
                    }
                }
            }
        }
    }
    with patch("data.scoreboard._get", return_value=bad_response):
        with pytest.raises(ValueError, match="week_start"):
            scoreboard.get_current_matchup(SESSION, LEAGUE_KEY, week=20)


def test_get_current_matchup_raises_on_empty_matchups():
    empty_response = {
        "fantasy_content": {
            "league": {
                "scoreboard": {
                    "matchups": {"@count": "0"}
                }
            }
        }
    }
    with patch("data.scoreboard._get", return_value=empty_response):
        with pytest.raises(ValueError, match="No matchups"):
            scoreboard.get_current_matchup(SESSION, LEAGUE_KEY, week=20)
