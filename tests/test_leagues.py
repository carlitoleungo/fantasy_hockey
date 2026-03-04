"""
Unit tests for data/leagues.py.

Patches data.client._get to return fixture dicts — no HTTP calls, no live API.
Tests cover field extraction, the _as_list() single-item edge case, URL
construction, NHL filtering, and season propagation.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from data import leagues

FIXTURES = Path(__file__).parent / "fixtures"

# A session object — only needed as a pass-through argument since _get is mocked
SESSION = MagicMock()


def load(filename: str) -> dict:
    with open(FIXTURES / filename) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# get_games()
# ---------------------------------------------------------------------------

def test_get_games_returns_two_games():
    with patch("data.leagues._get", return_value=load("user_games.json")):
        result = leagues.get_games(SESSION)

    assert len(result) == 2


def test_get_games_fields():
    with patch("data.leagues._get", return_value=load("user_games.json")):
        result = leagues.get_games(SESSION)

    nhl = next(g for g in result if g["game_code"] == "nhl")
    assert nhl["game_key"] == "453"
    assert nhl["season"] == "2024"


def test_get_games_contains_mlb_and_nhl():
    with patch("data.leagues._get", return_value=load("user_games.json")):
        result = leagues.get_games(SESSION)

    codes = {g["game_code"] for g in result}
    assert codes == {"nhl", "mlb"}


def test_get_games_sorted_by_season_descending():
    with patch("data.leagues._get", return_value=load("user_games.json")):
        result = leagues.get_games(SESSION)

    seasons = [g["season"] for g in result]
    assert seasons == sorted(seasons, reverse=True)


def test_get_games_single_game_normalised_to_list():
    """xmltodict returns a dict (not list) when there is exactly one game."""
    with patch("data.leagues._get", return_value=load("user_games_single.json")):
        result = leagues.get_games(SESSION)

    assert len(result) == 1
    assert result[0]["game_code"] == "nhl"
    assert result[0]["game_key"] == "453"


def test_get_games_calls_correct_url():
    with patch("data.leagues._get", return_value=load("user_games.json")) as mock_get:
        leagues.get_games(SESSION)

    url = mock_get.call_args[0][1]
    assert "users;use_login=1/games" in url


# ---------------------------------------------------------------------------
# get_leagues()
# ---------------------------------------------------------------------------

def test_get_leagues_returns_two_leagues():
    with patch("data.leagues._get", return_value=load("user_leagues.json")):
        result = leagues.get_leagues(SESSION, "453")

    assert len(result) == 2


def test_get_leagues_fields():
    with patch("data.leagues._get", return_value=load("user_leagues.json")):
        result = leagues.get_leagues(SESSION, "453")

    first = result[0]
    assert first["league_key"] == "nhl.l.12345"
    assert first["league_id"] == "12345"
    assert first["league_name"] == "Carlin's Hockey League"
    assert first["scoring_type"] == "head"
    assert first["start_week"] == "1"
    assert first["start_date"] == "2024-10-08"
    assert first["end_date"] == "2025-04-13"


def test_get_leagues_single_league_normalised_to_list():
    """xmltodict returns a dict (not list) when @count == 1."""
    with patch("data.leagues._get", return_value=load("user_leagues_single.json")):
        result = leagues.get_leagues(SESSION, "453")

    assert len(result) == 1
    assert result[0]["league_key"] == "nhl.l.12345"


def test_get_leagues_calls_correct_url():
    with patch("data.leagues._get", return_value=load("user_leagues.json")) as mock_get:
        leagues.get_leagues(SESSION, "453")

    url = mock_get.call_args[0][1]
    assert "game_keys=453" in url
    assert "leagues" in url


def test_get_leagues_uses_user_login_filter():
    with patch("data.leagues._get", return_value=load("user_leagues.json")) as mock_get:
        leagues.get_leagues(SESSION, "453")

    url = mock_get.call_args[0][1]
    assert "use_login=1" in url


# ---------------------------------------------------------------------------
# get_user_hockey_leagues()
# ---------------------------------------------------------------------------

def _games_then_leagues(session, url):
    """Route mock _get calls to the right fixture based on URL shape."""
    if "game_keys" in url:
        return load("user_leagues.json")
    return load("user_games.json")


def test_get_user_hockey_leagues_filters_to_nhl():
    """user_games.json has NHL + MLB; only NHL leagues should be returned."""
    with patch("data.leagues._get", side_effect=_games_then_leagues):
        result = leagues.get_user_hockey_leagues(SESSION)

    # user_games.json has 1 NHL game; user_leagues.json has 2 leagues
    assert len(result) == 2
    assert all(r["league_key"].startswith("nhl.") for r in result)


def test_get_user_hockey_leagues_includes_season():
    with patch("data.leagues._get", side_effect=_games_then_leagues):
        result = leagues.get_user_hockey_leagues(SESSION)

    assert all("season" in r for r in result)
    assert result[0]["season"] == "2024"


def test_get_user_hockey_leagues_includes_all_league_fields():
    with patch("data.leagues._get", side_effect=_games_then_leagues):
        result = leagues.get_user_hockey_leagues(SESSION)

    required = {"league_key", "league_id", "league_name", "scoring_type",
                "start_week", "start_date", "end_date", "season"}
    assert required.issubset(result[0].keys())


def test_get_user_hockey_leagues_empty_when_no_nhl_games():
    non_nhl_only = {
        "fantasy_content": {
            "users": {
                "user": {
                    "games": {
                        "game": {
                            "game_key": "422",
                            "code": "mlb",
                            "season": "2024",
                        }
                    }
                }
            }
        }
    }
    with patch("data.leagues._get", return_value=non_nhl_only):
        result = leagues.get_user_hockey_leagues(SESSION)

    assert result == []


def test_get_user_hockey_leagues_calls_games_endpoint_once():
    """get_games() should be called once regardless of how many NHL games exist."""
    call_count = {"n": 0}

    def counting_get(session, url):
        if "game_keys" not in url:
            call_count["n"] += 1
        return _games_then_leagues(session, url)

    with patch("data.leagues._get", side_effect=counting_get):
        leagues.get_user_hockey_leagues(SESSION)

    assert call_count["n"] == 1
