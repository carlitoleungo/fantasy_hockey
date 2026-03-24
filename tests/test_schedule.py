"""
Unit tests for data/schedule.py.

_nhl_get is patched throughout — no real HTTP calls are made.
"""

from datetime import date
from unittest.mock import patch

from data import schedule


def _make_response(games_by_date: dict) -> dict:
    """
    Build a minimal NHL schedule API response.

    games_by_date: {
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    }
    """
    game_week = []
    for game_date, games in games_by_date.items():
        game_week.append({"date": game_date, "games": games})
    return {"gameWeek": game_week}


FROM = date(2026, 3, 24)
TO = date(2026, 3, 29)


# ---------------------------------------------------------------------------
# Basic counting
# ---------------------------------------------------------------------------

def test_future_game_counted():
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM", "BOS"], FROM, TO)

    assert result["EDM"] == 1
    assert result["BOS"] == 1


def test_live_game_counted():
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "LIVE",
             "awayTeam": {"abbrev": "TOR"}, "homeTeam": {"abbrev": "MTL"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["TOR", "MTL"], FROM, TO)

    assert result["TOR"] == 1
    assert result["MTL"] == 1


def test_final_game_not_counted():
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "FINAL",
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM", "BOS"], FROM, TO)

    assert result["EDM"] == 0
    assert result["BOS"] == 0


def test_off_state_not_counted():
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "OFF",
             "awayTeam": {"abbrev": "CAR"}, "homeTeam": {"abbrev": "TBL"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["CAR", "TBL"], FROM, TO)

    assert result["CAR"] == 0
    assert result["TBL"] == 0


# ---------------------------------------------------------------------------
# Date filtering
# ---------------------------------------------------------------------------

def test_game_before_from_date_excluded():
    resp = _make_response({
        "2026-03-23": [  # one day before FROM
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM", "BOS"], FROM, TO)

    assert result["EDM"] == 0


def test_game_after_to_date_excluded():
    resp = _make_response({
        "2026-03-30": [  # one day after TO
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM", "BOS"], FROM, TO)

    assert result["EDM"] == 0


def test_game_on_to_date_included():
    resp = _make_response({
        "2026-03-29": [  # exactly on TO
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM", "BOS"], FROM, TO)

    assert result["EDM"] == 1


# ---------------------------------------------------------------------------
# Team filtering
# ---------------------------------------------------------------------------

def test_unknown_abbr_not_in_result():
    """Teams not in team_abbrs should not appear in the output."""
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "VGK"}, "homeTeam": {"abbrev": "LAK"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM"], FROM, TO)

    assert "VGK" not in result
    assert "LAK" not in result
    assert result["EDM"] == 0


def test_all_input_abbrs_present_even_with_no_games():
    resp = _make_response({})
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM", "BOS", "TOR"], FROM, TO)

    assert set(result.keys()) == {"EDM", "BOS", "TOR"}
    assert all(v == 0 for v in result.values())


# ---------------------------------------------------------------------------
# Game type filtering
# ---------------------------------------------------------------------------

def test_preseason_game_not_counted():
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 1, "gameState": "FUT",  # preseason
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM", "BOS"], FROM, TO)

    assert result["EDM"] == 0


def test_playoff_game_counted():
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 3, "gameState": "FUT",  # playoff
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM", "BOS"], FROM, TO)

    assert result["EDM"] == 1


# ---------------------------------------------------------------------------
# Two-call path (range > 6 days)
# ---------------------------------------------------------------------------

def test_two_call_path_for_long_range():
    """When to_date - from_date >= 7 days, two _nhl_get calls are made."""
    from_long = date(2026, 3, 24)
    to_long = date(2026, 3, 31)  # 7 days later

    resp = _make_response({})
    with patch("data.schedule._nhl_get", return_value=resp) as mock_nhl:
        schedule.get_remaining_games(["EDM"], from_long, to_long)

    assert mock_nhl.call_count == 2


def test_single_call_for_short_range():
    """When range is 6 days or fewer, only one call is made."""
    resp = _make_response({})
    with patch("data.schedule._nhl_get", return_value=resp) as mock_nhl:
        schedule.get_remaining_games(["EDM"], FROM, TO)  # 5-day range

    assert mock_nhl.call_count == 1


def test_no_double_counting_overlapping_responses():
    """Same game ID appearing in both calls is only counted once."""
    resp = _make_response({
        "2026-03-24": [
            {"id": 42, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    })
    from_long = date(2026, 3, 24)
    to_long = date(2026, 3, 31)

    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM", "BOS"], from_long, to_long)

    # Game appears in both calls but should only be counted once
    assert result["EDM"] == 1
    assert result["BOS"] == 1


# ---------------------------------------------------------------------------
# Multiple games per team
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Yahoo → NHL abbreviation normalisation
# ---------------------------------------------------------------------------

def test_yahoo_two_letter_la_normalised():
    """Yahoo 'LA' → NHL 'LAK'; result keyed by original Yahoo abbr."""
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "LAK"}, "homeTeam": {"abbrev": "EDM"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["LA", "EDM"], FROM, TO)

    assert result["LA"] == 1    # Yahoo abbr in, Yahoo abbr out
    assert result["EDM"] == 1
    assert "LAK" not in result  # NHL abbr must not leak into output


def test_yahoo_two_letter_tb_normalised():
    """Yahoo 'TB' → NHL 'TBL'."""
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "TBL"}, "homeTeam": {"abbrev": "BOS"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["TB", "BOS"], FROM, TO)

    assert result["TB"] == 1
    assert result["BOS"] == 1


def test_yahoo_two_letter_nj_normalised():
    """Yahoo 'NJ' → NHL 'NJD'."""
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "NJD"}, "homeTeam": {"abbrev": "NYR"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["NJ"], FROM, TO)

    assert result["NJ"] == 1


def test_three_letter_abbrs_unchanged():
    """Standard 3-letter Yahoo abbrs (e.g. BOS, EDM) pass through unchanged."""
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "BOS"}, "homeTeam": {"abbrev": "EDM"}},
        ]
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["BOS", "EDM"], FROM, TO)

    assert result["BOS"] == 1
    assert result["EDM"] == 1


def test_multiple_games_accumulated():
    resp = _make_response({
        "2026-03-24": [
            {"id": 1, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "BOS"}},
        ],
        "2026-03-26": [
            {"id": 2, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "EDM"}, "homeTeam": {"abbrev": "TOR"}},
        ],
        "2026-03-28": [
            {"id": 3, "gameType": 2, "gameState": "FUT",
             "awayTeam": {"abbrev": "CGY"}, "homeTeam": {"abbrev": "EDM"}},
        ],
    })
    with patch("data.schedule._nhl_get", return_value=resp):
        result = schedule.get_remaining_games(["EDM"], FROM, TO)

    assert result["EDM"] == 3
