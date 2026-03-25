"""
Unit tests for data/players.py.

_get and get_stat_categories are both imported by name in data.players, so they
must be patched in that namespace (data.players._get / data.players.get_stat_categories).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from data import players

FIXTURES = Path(__file__).parent / "fixtures"
LEAGUE_KEY = "nhl.l.99999"
SESSION = MagicMock()

STAT_CATEGORIES = [
    {"stat_id": "1", "stat_name": "Goals",        "abbreviation": "G",   "stat_group": "offense", "is_enabled": True},
    {"stat_id": "2", "stat_name": "Assists",       "abbreviation": "A",   "stat_group": "offense", "is_enabled": True},
    {"stat_id": "3", "stat_name": "Points",        "abbreviation": "Pts", "stat_group": "offense", "is_enabled": False},
    {"stat_id": "7", "stat_name": "Shots on Goal", "abbreviation": "SOG", "stat_group": "offense", "is_enabled": True},
]
ID_TO_NAME = {"1": "Goals", "2": "Assists", "7": "Shots on Goal"}


def load(filename: str) -> dict:
    with open(FIXTURES / filename) as f:
        return json.load(f)


def _make_season_page(n: int, start_id: int = 1) -> dict:
    """Build a league players season response with n players."""
    player_list = [
        {
            "player_key": f"nhl.p.{start_id + i}",
            "name": {"full": f"Player {start_id + i}"},
            "editorial_team_abbr": "BOS",
            "display_position": "C",
            "status": "",
            "player_stats": {
                "stats": {
                    "stat": [
                        {"stat_id": "1", "value": str(i + 1)},
                        {"stat_id": "2", "value": str(i)},
                    ]
                }
            },
        }
        for i in range(n)
    ]
    # Mimic xmltodict: single item → dict, multiple → list
    return {
        "fantasy_content": {
            "leagues": {
                "league": {
                    "players": {
                        "@count": str(n),
                        "player": player_list[0] if n == 1 else player_list,
                    }
                }
            }
        }
    }


def _make_lastmonth_page(n: int, start_id: int = 1) -> dict:
    """Build a batch lastmonth stats response for n players."""
    player_list = [
        {
            "player_key": f"nhl.p.{start_id + i}",
            "player_stats": {
                "stats": {
                    "stat": [
                        {"stat_id": "0", "value": "10"},
                        {"stat_id": "1", "value": "1"},
                        {"stat_id": "2", "value": "2"},
                    ]
                }
            },
        }
        for i in range(n)
    ]
    return {
        "fantasy_content": {
            "players": {
                "@count": str(n),
                "player": player_list[0] if n == 1 else player_list,
            }
        }
    }


# ---------------------------------------------------------------------------
# _fetch_page_season
# ---------------------------------------------------------------------------

def test_fetch_page_season_returns_rows_and_keys():
    with patch("data.players._get", return_value=load("players_page_season.json")):
        rows, keys = players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    assert len(rows) == 2
    assert keys == ["nhl.p.1", "nhl.p.2"]


def test_fetch_page_season_metadata():
    with patch("data.players._get", return_value=load("players_page_season.json")):
        rows, _ = players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    geekie = rows[0]
    assert geekie["player_key"] == "nhl.p.1"
    assert geekie["player_name"] == "Morgan Geekie"
    assert geekie["team_abbr"] == "BOS"
    assert geekie["display_position"] == "C"
    assert geekie["status"] == ""


def test_fetch_page_season_stat_values():
    with patch("data.players._get", return_value=load("players_page_season.json")):
        rows, _ = players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    geekie = rows[0]
    assert geekie["Goals"] == 34.0
    assert geekie["Assists"] == 27.0


def test_fetch_page_season_dash_coerced_to_zero():
    """stat_id '7' (Shots on Goal) has value '-' for Morgan Geekie in the fixture."""
    with patch("data.players._get", return_value=load("players_page_season.json")):
        rows, _ = players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    assert rows[0]["Shots on Goal"] == 0.0


def test_fetch_page_season_display_stat_excluded():
    """stat_id '3' (Points) has is_enabled=False — must not appear in output."""
    with patch("data.players._get", return_value=load("players_page_season.json")):
        rows, _ = players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    for row in rows:
        assert "Points" not in row


def test_fetch_page_season_unknown_stat_excluded():
    """stat_id '99' is in the fixture but not in id_to_name — must be silently skipped."""
    with patch("data.players._get", return_value=load("players_page_season.json")):
        rows, _ = players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    for row in rows:
        assert "99" not in row


def test_fetch_page_season_injured_player_status():
    with patch("data.players._get", return_value=load("players_page_season.json")):
        rows, _ = players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    smith = rows[1]
    assert smith["status"] == "GTD"


def test_fetch_page_season_empty_returns_empty():
    with patch("data.players._get", return_value=load("players_page_empty.json")):
        rows, keys = players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    assert rows == []
    assert keys == []


def test_fetch_page_season_single_player_handled():
    """xmltodict returns a dict (not list) when @count == 1 — _as_list must normalise it."""
    with patch("data.players._get", return_value=load("players_single_season.json")):
        rows, keys = players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    assert len(rows) == 1
    assert len(keys) == 1
    assert rows[0]["Goals"] == 34.0


def test_fetch_page_season_url_includes_start():
    with patch("data.players._get", return_value=load("players_page_empty.json")) as mock_get:
        players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=50)

    url = mock_get.call_args[0][1]
    assert "start=50" in url


def test_fetch_page_season_url_includes_league_and_available_status():
    with patch("data.players._get", return_value=load("players_page_empty.json")) as mock_get:
        players._fetch_page_season(SESSION, LEAGUE_KEY, ID_TO_NAME, start=0)

    url = mock_get.call_args[0][1]
    assert LEAGUE_KEY in url
    assert "status=A" in url


# ---------------------------------------------------------------------------
# _fetch_page_lastmonth
# ---------------------------------------------------------------------------

def test_fetch_page_lastmonth_returns_dict_by_key():
    with patch("data.players._get", return_value=load("players_page_lastmonth.json")):
        result = players._fetch_page_lastmonth(SESSION, ["nhl.p.1", "nhl.p.2"], ID_TO_NAME)

    assert set(result.keys()) == {"nhl.p.1", "nhl.p.2"}


def test_fetch_page_lastmonth_stat_values():
    with patch("data.players._get", return_value=load("players_page_lastmonth.json")):
        result = players._fetch_page_lastmonth(SESSION, ["nhl.p.1", "nhl.p.2"], ID_TO_NAME)

    assert result["nhl.p.1"]["Goals"] == 2.0
    assert result["nhl.p.1"]["Assists"] == 5.0
    assert result["nhl.p.2"]["Goals"] == 1.0


def test_fetch_page_lastmonth_includes_games_played():
    with patch("data.players._get", return_value=load("players_page_lastmonth.json")):
        result = players._fetch_page_lastmonth(SESSION, ["nhl.p.1", "nhl.p.2"], ID_TO_NAME)

    assert result["nhl.p.1"]["games_played"] == 13
    assert result["nhl.p.2"]["games_played"] == 8


def test_fetch_page_lastmonth_single_player_handled():
    """xmltodict dict (not list) when @count == 1."""
    with patch("data.players._get", return_value=load("players_single_lastmonth.json")):
        result = players._fetch_page_lastmonth(SESSION, ["nhl.p.1"], ID_TO_NAME)

    assert "nhl.p.1" in result
    assert result["nhl.p.1"]["Goals"] == 2.0
    assert result["nhl.p.1"]["games_played"] == 13


def test_fetch_page_lastmonth_empty_count_returns_empty():
    empty = {"fantasy_content": {"players": {"@count": "0"}}}
    with patch("data.players._get", return_value=empty):
        result = players._fetch_page_lastmonth(SESSION, ["nhl.p.1"], ID_TO_NAME)

    assert result == {}


def test_fetch_page_lastmonth_url_pattern():
    with patch("data.players._get", return_value=load("players_page_lastmonth.json")) as mock_get:
        players._fetch_page_lastmonth(SESSION, ["nhl.p.1", "nhl.p.2"], ID_TO_NAME)

    url = mock_get.call_args[0][1]
    assert "nhl.p.1,nhl.p.2" in url
    assert "type=lastmonth" in url


# ---------------------------------------------------------------------------
# _parse_stats
# ---------------------------------------------------------------------------

def test_parse_stats_returns_empty_when_no_player_stats():
    player = {"player_key": "nhl.p.1"}
    result = players._parse_stats(player, ID_TO_NAME)
    assert result == {}


def test_parse_stats_games_played_not_included_by_default():
    player = {
        "player_stats": {
            "stats": {"stat": [{"stat_id": "0", "value": "10"}, {"stat_id": "1", "value": "5"}]}
        }
    }
    result = players._parse_stats(player, ID_TO_NAME)
    assert "games_played" not in result
    assert result["Goals"] == 5.0


def test_parse_stats_games_played_included_when_flag_set():
    player = {
        "player_stats": {
            "stats": {"stat": [{"stat_id": "0", "value": "10"}, {"stat_id": "1", "value": "5"}]}
        }
    }
    result = players._parse_stats(player, ID_TO_NAME, include_games_played=True)
    assert result["games_played"] == 10
    assert result["Goals"] == 5.0


def test_parse_stats_games_played_dash_coerced_to_zero():
    player = {
        "player_stats": {
            "stats": {"stat": [{"stat_id": "0", "value": "-"}]}
        }
    }
    result = players._parse_stats(player, ID_TO_NAME, include_games_played=True)
    assert result["games_played"] == 0


GAA_ID_TO_NAME = {**ID_TO_NAME, "22": "Goals Against", "23": "Goals Against Average"}


def test_parse_stats_lastmonth_gaa_computed_from_ga_and_gp():
    """Yahoo returns season GAA for stat_id 23; we recompute from raw GA (22) / GP (0)."""
    player = {
        "player_stats": {
            "stats": {
                "stat": [
                    {"stat_id": "0",  "value": "8"},   # GP
                    {"stat_id": "22", "value": "22"},  # raw GA
                    {"stat_id": "23", "value": "2.9"}, # season GAA (should be ignored)
                ]
            }
        }
    }
    result = players._parse_stats(player, GAA_ID_TO_NAME, include_games_played=True)

    import pytest
    assert result["games_played"] == 8
    assert result["Goals Against"] == pytest.approx(22.0)    # raw GA stored normally
    assert result["Goals Against Average"] == pytest.approx(22.0 / 8)  # recomputed, not 2.9


def test_parse_stats_gaa_zero_when_no_games_played():
    """If GP is 0, computed GAA should be 0.0 (no division by zero)."""
    player = {
        "player_stats": {
            "stats": {
                "stat": [
                    {"stat_id": "0",  "value": "0"},
                    {"stat_id": "22", "value": "0"},
                    {"stat_id": "23", "value": "2.9"},
                ]
            }
        }
    }
    result = players._parse_stats(player, GAA_ID_TO_NAME, include_games_played=True)
    assert result["Goals Against Average"] == 0.0


def test_parse_stats_season_gaa_unchanged_when_not_lastmonth():
    """Without include_games_played, Yahoo's season GAA value is stored as-is."""
    player = {
        "player_stats": {
            "stats": {
                "stat": [
                    {"stat_id": "23", "value": "2.9"},
                ]
            }
        }
    }
    result = players._parse_stats(player, GAA_ID_TO_NAME)

    import pytest
    assert result["Goals Against Average"] == pytest.approx(2.9)


# ---------------------------------------------------------------------------
# get_available_players (integration)
# ---------------------------------------------------------------------------

def test_get_available_players_returns_two_dataframes():
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", side_effect=[
            load("players_page_season.json"),
            load("players_page_lastmonth.json"),
        ]):
            season_df, lm_df = players.get_available_players(SESSION, LEAGUE_KEY)

    assert len(season_df) == 2
    assert len(lm_df) == 2


def test_get_available_players_season_df_has_season_stats():
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", side_effect=[
            load("players_page_season.json"),
            load("players_page_lastmonth.json"),
        ]):
            season_df, _ = players.get_available_players(SESSION, LEAGUE_KEY)

    geekie = season_df[season_df["player_name"] == "Morgan Geekie"].iloc[0]
    assert geekie["Goals"] == 34.0
    assert geekie["Assists"] == 27.0


def test_get_available_players_lastmonth_df_has_lastmonth_stats():
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", side_effect=[
            load("players_page_season.json"),
            load("players_page_lastmonth.json"),
        ]):
            _, lm_df = players.get_available_players(SESSION, LEAGUE_KEY)

    geekie = lm_df[lm_df["player_name"] == "Morgan Geekie"].iloc[0]
    assert geekie["Goals"] == 2.0
    assert geekie["games_played"] == 13


def test_get_available_players_metadata_in_both_dfs():
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", side_effect=[
            load("players_page_season.json"),
            load("players_page_lastmonth.json"),
        ]):
            season_df, lm_df = players.get_available_players(SESSION, LEAGUE_KEY)

    for df in (season_df, lm_df):
        for col in ("player_key", "player_name", "team_abbr", "display_position", "status"):
            assert col in df.columns


def test_get_available_players_stops_when_page_less_than_25():
    """2-player fixture (< 25) means loop exits after one page — only 2 _get calls."""
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", side_effect=[
            load("players_page_season.json"),
            load("players_page_lastmonth.json"),
        ]) as mock_get:
            players.get_available_players(SESSION, LEAGUE_KEY)

    assert mock_get.call_count == 2


def test_get_available_players_stops_on_empty_first_page():
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", return_value=load("players_page_empty.json")):
            season_df, lm_df = players.get_available_players(SESSION, LEAGUE_KEY)

    assert len(season_df) == 0
    assert len(lm_df) == 0


def test_get_available_players_max_players_zero_skips_fetch():
    """max_players=0 means loop never starts — _get never called."""
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get") as mock_get:
            season_df, lm_df = players.get_available_players(SESSION, LEAGUE_KEY, max_players=0)

    mock_get.assert_not_called()
    assert len(season_df) == 0
    assert len(lm_df) == 0


def test_get_available_players_max_players_limits_pages():
    """
    max_players=25 with a full 25-player first page stops after that page.
    Loop: len([]) < 25 → fetch 25 → len([25]) < 25 is False → exit.
    Only 2 _get calls (season + lastmonth for page 1).
    """
    page1_s = _make_season_page(25, start_id=1)
    page1_lm = _make_lastmonth_page(25, start_id=1)

    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", side_effect=[page1_s, page1_lm]) as mock_get:
            season_df, lm_df = players.get_available_players(SESSION, LEAGUE_KEY, max_players=25)

    assert mock_get.call_count == 2
    assert len(season_df) == 25


def test_get_available_players_two_full_pages():
    """Two full pages (25 each) then empty → 5 _get calls, 50 rows."""
    page1_s = _make_season_page(25, start_id=1)
    page1_lm = _make_lastmonth_page(25, start_id=1)
    page2_s = _make_season_page(25, start_id=26)
    page2_lm = _make_lastmonth_page(25, start_id=26)

    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", side_effect=[
            page1_s, page1_lm,
            page2_s, page2_lm,
            load("players_page_empty.json"),
        ]) as mock_get:
            season_df, lm_df = players.get_available_players(SESSION, LEAGUE_KEY, max_players=75)

    assert mock_get.call_count == 5
    assert len(season_df) == 50
    assert len(lm_df) == 50


# ---------------------------------------------------------------------------
# get_players_lastmonth_stats
# ---------------------------------------------------------------------------

def test_get_players_lastmonth_stats_returns_dict():
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", return_value=load("players_page_lastmonth.json")):
            result = players.get_players_lastmonth_stats(SESSION, LEAGUE_KEY, ["nhl.p.1", "nhl.p.2"])

    assert "nhl.p.1" in result
    assert "nhl.p.2" in result


def test_get_players_lastmonth_stats_values():
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", return_value=load("players_page_lastmonth.json")):
            result = players.get_players_lastmonth_stats(SESSION, LEAGUE_KEY, ["nhl.p.1", "nhl.p.2"])

    assert result["nhl.p.1"]["Goals"] == 2.0
    assert result["nhl.p.1"]["games_played"] == 13


def test_get_players_lastmonth_stats_empty_keys_returns_empty():
    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get") as mock_get:
            result = players.get_players_lastmonth_stats(SESSION, LEAGUE_KEY, [])

    mock_get.assert_not_called()
    assert result == {}


def test_get_players_lastmonth_stats_chunks_at_25():
    """27 player keys → two _get calls (chunk of 25 + chunk of 2)."""
    keys = [f"nhl.p.{i}" for i in range(27)]

    lm_resp = load("players_page_lastmonth.json")

    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", return_value=lm_resp) as mock_get:
            players.get_players_lastmonth_stats(SESSION, LEAGUE_KEY, keys)

    assert mock_get.call_count == 2


def test_get_players_lastmonth_stats_merges_chunks():
    """Results from multiple chunks are merged into a single dict."""
    keys_chunk1 = [f"nhl.p.{i}" for i in range(25)]
    keys_chunk2 = ["nhl.p.25", "nhl.p.26"]
    all_keys = keys_chunk1 + keys_chunk2

    def side_effect(session, url):
        # First call: return p.1 and p.2; second call: return empty
        if "nhl.p.0" in url:
            return load("players_page_lastmonth.json")
        return {"fantasy_content": {"players": {"@count": "0"}}}

    with patch("data.players.get_stat_categories", return_value=STAT_CATEGORIES):
        with patch("data.players._get", side_effect=side_effect):
            result = players.get_players_lastmonth_stats(SESSION, LEAGUE_KEY, all_keys)

    # Results from first chunk are present
    assert "nhl.p.1" in result
