"""
Unit tests for analysis/projection.py.
All tests use in-memory inputs — no fixtures or API calls needed.
"""
from analysis import projection

STAT_CATEGORIES = [
    {"stat_id": "1", "stat_name": "Goals",   "is_enabled": True},
    {"stat_id": "2", "stat_name": "Assists", "is_enabled": True},
    {"stat_id": "3", "stat_name": "Points",  "is_enabled": False},  # display-only
    {"stat_id": "8", "stat_name": "GAA",     "is_enabled": True},   # lower is better
]


# ---------------------------------------------------------------------------
# project_team_stats
# ---------------------------------------------------------------------------

def test_projection_basic_math():
    """Single player, 2 remaining games, 10 goals in 10 lastmonth games → +2."""
    current = {"Goals": 5.0, "Assists": 8.0, "GAA": 2.5}
    roster = [{"player_key": "p.1", "team_abbr": "EDM"}]
    lm = {"p.1": {"games_played": 10, "Goals": 10.0, "Assists": 20.0, "GAA": 2.0}}
    remaining = {"EDM": 2}

    result = projection.project_team_stats(current, roster, lm, remaining, STAT_CATEGORIES)

    assert result["Goals"] == pytest.approx(5.0 + 2.0)    # 5 + (10/10 * 2)
    assert result["Assists"] == pytest.approx(8.0 + 4.0)  # 8 + (20/10 * 2)
    assert result["GAA"] == pytest.approx(2.5 + 0.4)      # 2.5 + (2.0/10 * 2)


def test_projection_zero_games_played_contributes_nothing():
    current = {"Goals": 5.0}
    roster = [{"player_key": "p.1", "team_abbr": "EDM"}]
    lm = {"p.1": {"games_played": 0, "Goals": 10.0}}
    remaining = {"EDM": 3}

    result = projection.project_team_stats(current, roster, lm, remaining, STAT_CATEGORIES)

    assert result["Goals"] == 5.0


def test_projection_zero_remaining_games_contributes_nothing():
    current = {"Goals": 5.0}
    roster = [{"player_key": "p.1", "team_abbr": "EDM"}]
    lm = {"p.1": {"games_played": 10, "Goals": 10.0}}
    remaining = {"EDM": 0}

    result = projection.project_team_stats(current, roster, lm, remaining, STAT_CATEGORIES)

    assert result["Goals"] == 5.0


def test_projection_missing_team_abbr_contributes_nothing():
    current = {"Goals": 5.0}
    roster = [{"player_key": "p.1", "team_abbr": "EDM"}]
    lm = {"p.1": {"games_played": 10, "Goals": 10.0}}
    remaining = {}  # EDM not present

    result = projection.project_team_stats(current, roster, lm, remaining, STAT_CATEGORIES)

    assert result["Goals"] == 5.0


def test_projection_missing_player_in_lastmonth_contributes_nothing():
    current = {"Goals": 5.0}
    roster = [{"player_key": "p.99", "team_abbr": "EDM"}]
    lm = {}  # player not in lastmonth data
    remaining = {"EDM": 2}

    result = projection.project_team_stats(current, roster, lm, remaining, STAT_CATEGORIES)

    assert result["Goals"] == 5.0


def test_projection_display_stat_excluded():
    """Points (is_enabled=False) should not appear in the output."""
    current = {"Goals": 0.0, "Points": 99.0}
    roster = []
    result = projection.project_team_stats(current, [], {}, {}, STAT_CATEGORIES)

    assert "Points" not in result


def test_projection_sums_multiple_players():
    current = {"Goals": 0.0}
    roster = [
        {"player_key": "p.1", "team_abbr": "EDM"},
        {"player_key": "p.2", "team_abbr": "BOS"},
    ]
    lm = {
        "p.1": {"games_played": 10, "Goals": 5.0},
        "p.2": {"games_played": 5,  "Goals": 10.0},
    }
    remaining = {"EDM": 2, "BOS": 3}

    result = projection.project_team_stats(current, roster, lm, remaining, STAT_CATEGORIES)

    # p.1: 5/10 * 2 = 1.0; p.2: 10/5 * 3 = 6.0; total = 7.0
    assert result["Goals"] == pytest.approx(7.0)


def test_projection_empty_roster():
    current = {"Goals": 12.0, "Assists": 18.0, "GAA": 3.0}
    result = projection.project_team_stats(current, [], {}, {}, STAT_CATEGORIES)

    assert result["Goals"] == 12.0
    assert result["Assists"] == 18.0
    assert result["GAA"] == 3.0


# ---------------------------------------------------------------------------
# compare_projections
# ---------------------------------------------------------------------------

import pytest


def test_compare_higher_wins():
    a = {"Goals": 20.0, "Assists": 10.0, "GAA": 2.0}
    b = {"Goals": 15.0, "Assists": 12.0, "GAA": 3.0}

    result = projection.compare_projections(a, b, STAT_CATEGORIES)

    by_cat = {r["category"]: r["winner"] for r in result}
    assert by_cat["Goals"] == "team_a"   # 20 > 15
    assert by_cat["Assists"] == "team_b" # 12 > 10


def test_compare_lower_is_better():
    a = {"Goals": 10.0, "Assists": 10.0, "GAA": 2.0}
    b = {"Goals": 10.0, "Assists": 10.0, "GAA": 3.0}

    result = projection.compare_projections(a, b, STAT_CATEGORIES)

    by_cat = {r["category"]: r["winner"] for r in result}
    assert by_cat["GAA"] == "team_a"   # 2.0 < 3.0, lower is better


def test_compare_tie():
    a = {"Goals": 10.0, "Assists": 10.0, "GAA": 2.5}
    b = {"Goals": 10.0, "Assists": 10.0, "GAA": 2.5}

    result = projection.compare_projections(a, b, STAT_CATEGORIES)

    for row in result:
        assert row["winner"] == "Tie"


def test_compare_returns_values():
    a = {"Goals": 18.5, "Assists": 25.0, "GAA": 2.1}
    b = {"Goals": 15.2, "Assists": 30.0, "GAA": 2.8}

    result = projection.compare_projections(a, b, STAT_CATEGORIES)

    goals_row = next(r for r in result if r["category"] == "Goals")
    assert goals_row["team_a"] == pytest.approx(18.5)
    assert goals_row["team_b"] == pytest.approx(15.2)


def test_compare_display_stat_excluded():
    a = {"Goals": 10.0, "Points": 99.0}
    b = {"Goals": 8.0, "Points": 99.0}

    result = projection.compare_projections(a, b, STAT_CATEGORIES)
    categories = [r["category"] for r in result]

    assert "Points" not in categories


def test_compare_custom_lower_is_better():
    a = {"Goals": 5.0, "Assists": 10.0, "GAA": 2.0}
    b = {"Goals": 8.0, "Assists": 10.0, "GAA": 2.0}

    # Override: treat Goals as lower-is-better
    result = projection.compare_projections(
        a, b, STAT_CATEGORIES, lower_is_better=frozenset({"Goals", "GAA"})
    )

    by_cat = {r["category"]: r["winner"] for r in result}
    assert by_cat["Goals"] == "team_a"  # 5 < 8, lower is better here
