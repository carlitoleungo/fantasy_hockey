"""
Unit tests for analysis/team_scores.py.

All tests use a hand-built matchups DataFrame with known stat values so that
expected ranks can be calculated mentally and asserted precisely.

Fixture structure — 3 teams × 3 weeks:

    Goals (higher is better):
        Team A = 10 every week  → rank 1
        Team B =  6 every week  → rank 2
        Team C =  2 every week  → rank 3

    Assists (higher is better):
        Team A =  2 every week  → rank 3
        Team B =  6 every week  → rank 2
        Team C = 10 every week  → rank 1

    Goals Against (lower is better):
        Team A =  1 every week  → rank 1
        Team B =  3 every week  → rank 2
        Team C =  5 every week  → rank 3

Expected avg_ranks (per team, per stat, consistent across all 3 weeks):
    Team A: Goals=1.0, Assists=3.0, Goals Against=1.0  avg_rank = 5/3 ≈ 1.67
    Team B: Goals=2.0, Assists=2.0, Goals Against=2.0  avg_rank = 2.00
    Team C: Goals=3.0, Assists=1.0, Goals Against=3.0  avg_rank = 7/3 ≈ 2.33

Sort order: Team A first (best avg_rank), Team C last.
"""

import pandas as pd
import pytest

from analysis.team_scores import LOWER_IS_BETTER, avg_ranks, stat_columns, weekly_scores


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def matchups_df() -> pd.DataFrame:
    """3 teams × 3 weeks with deterministic stat values."""
    rows = []
    for week in [1, 2, 3]:
        rows += [
            {"team_key": "t.1", "team_name": "Team A", "week": week,
             "games_played": 7, "Goals": 10.0, "Assists":  2.0, "Goals Against": 1.0},
            {"team_key": "t.2", "team_name": "Team B", "week": week,
             "games_played": 7, "Goals":  6.0, "Assists":  6.0, "Goals Against": 3.0},
            {"team_key": "t.3", "team_name": "Team C", "week": week,
             "games_played": 7, "Goals":  2.0, "Assists": 10.0, "Goals Against": 5.0},
        ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# stat_columns()
# ---------------------------------------------------------------------------

def test_stat_columns_excludes_metadata(matchups_df):
    cols = stat_columns(matchups_df)
    for meta in ("team_key", "team_name", "week", "games_played"):
        assert meta not in cols


def test_stat_columns_includes_stat_names(matchups_df):
    cols = stat_columns(matchups_df)
    assert "Goals" in cols
    assert "Assists" in cols
    assert "Goals Against" in cols


def test_stat_columns_preserves_df_column_order(matchups_df):
    cols = stat_columns(matchups_df)
    # Goals, Assists, Goals Against appear in that order in the fixture
    assert cols.index("Goals") < cols.index("Assists")
    assert cols.index("Assists") < cols.index("Goals Against")


# ---------------------------------------------------------------------------
# weekly_scores()
# ---------------------------------------------------------------------------

def test_weekly_scores_returns_one_row_per_team(matchups_df):
    result = weekly_scores(matchups_df, week=2)
    assert len(result) == 3


def test_weekly_scores_contains_team_name_column(matchups_df):
    result = weekly_scores(matchups_df, week=1)
    assert "team_name" in result.columns


def test_weekly_scores_drops_metadata_columns(matchups_df):
    result = weekly_scores(matchups_df, week=1)
    for col in ("team_key", "week", "games_played"):
        assert col not in result.columns


def test_weekly_scores_correct_values_for_week(matchups_df):
    result = weekly_scores(matchups_df, week=1)
    team_a_row = result[result["team_name"] == "Team A"].iloc[0]
    assert team_a_row["Goals"] == 10.0
    assert team_a_row["Assists"] == 2.0


def test_weekly_scores_sorted_by_team_name(matchups_df):
    result = weekly_scores(matchups_df, week=1)
    names = list(result["team_name"])
    assert names == sorted(names)


def test_weekly_scores_returns_empty_for_unknown_week(matchups_df):
    result = weekly_scores(matchups_df, week=99)
    assert len(result) == 0


def test_weekly_scores_consistent_across_weeks(matchups_df):
    """Fixture has identical values every week; scores should be the same."""
    w1 = weekly_scores(matchups_df, week=1).set_index("team_name")
    w2 = weekly_scores(matchups_df, week=2).set_index("team_name")
    pd.testing.assert_frame_equal(w1, w2)


# ---------------------------------------------------------------------------
# avg_ranks()
# ---------------------------------------------------------------------------

def test_avg_ranks_returns_one_row_per_team(matchups_df):
    result = avg_ranks(matchups_df, lower_is_better=frozenset({"Goals Against"}))
    assert len(result) == 3


def test_avg_ranks_has_team_name_column(matchups_df):
    result = avg_ranks(matchups_df, lower_is_better=frozenset({"Goals Against"}))
    assert "team_name" in result.columns


def test_avg_ranks_has_avg_rank_column(matchups_df):
    result = avg_ranks(matchups_df, lower_is_better=frozenset({"Goals Against"}))
    assert "avg_rank" in result.columns


def test_avg_ranks_higher_is_better_goals(matchups_df):
    """Team A always scores most goals → Goals avg_rank == 1.0."""
    result = avg_ranks(matchups_df, lower_is_better=frozenset({"Goals Against"}))
    idx = result.set_index("team_name")
    assert idx.loc["Team A", "Goals"] == pytest.approx(1.0)
    assert idx.loc["Team B", "Goals"] == pytest.approx(2.0)
    assert idx.loc["Team C", "Goals"] == pytest.approx(3.0)


def test_avg_ranks_higher_is_better_assists(matchups_df):
    """Team C always has most assists → Assists avg_rank == 1.0."""
    result = avg_ranks(matchups_df, lower_is_better=frozenset({"Goals Against"}))
    idx = result.set_index("team_name")
    assert idx.loc["Team C", "Assists"] == pytest.approx(1.0)
    assert idx.loc["Team B", "Assists"] == pytest.approx(2.0)
    assert idx.loc["Team A", "Assists"] == pytest.approx(3.0)


def test_avg_ranks_lower_is_better_goals_against(matchups_df):
    """Team A always concedes fewest goals → Goals Against avg_rank == 1.0."""
    result = avg_ranks(matchups_df, lower_is_better=frozenset({"Goals Against"}))
    idx = result.set_index("team_name")
    assert idx.loc["Team A", "Goals Against"] == pytest.approx(1.0)
    assert idx.loc["Team B", "Goals Against"] == pytest.approx(2.0)
    assert idx.loc["Team C", "Goals Against"] == pytest.approx(3.0)


def test_avg_ranks_overall_avg_rank_values(matchups_df):
    """
    Expected avg_rank:
        Team A: (1.0 + 3.0 + 1.0) / 3 = 5/3
        Team B: (2.0 + 2.0 + 2.0) / 3 = 2.0
        Team C: (3.0 + 1.0 + 3.0) / 3 = 7/3
    """
    result = avg_ranks(matchups_df, lower_is_better=frozenset({"Goals Against"}))
    idx = result.set_index("team_name")
    assert idx.loc["Team A", "avg_rank"] == pytest.approx(5 / 3)
    assert idx.loc["Team B", "avg_rank"] == pytest.approx(2.0)
    assert idx.loc["Team C", "avg_rank"] == pytest.approx(7 / 3)


def test_avg_ranks_sorted_by_avg_rank_ascending(matchups_df):
    """Best team (lowest avg_rank) should appear first."""
    result = avg_ranks(matchups_df, lower_is_better=frozenset({"Goals Against"}))
    assert list(result["team_name"]) == ["Team A", "Team B", "Team C"]


def test_avg_ranks_default_lower_is_better_contains_ga_variants():
    """The module-level constant should cover both 'Goals Against' spellings."""
    assert "Goals Against" in LOWER_IS_BETTER
    assert "Goals Against Average" in LOWER_IS_BETTER


def test_avg_ranks_treats_ga_as_lower_is_better_by_default():
    """Default lower_is_better should rank 'Goals Against' correctly."""
    rows = [
        {"team_key": "t.1", "team_name": "Goalie A", "week": 1,
         "games_played": 3, "Goals Against": 1.0},
        {"team_key": "t.2", "team_name": "Goalie B", "week": 1,
         "games_played": 3, "Goals Against": 5.0},
    ]
    df = pd.DataFrame(rows)
    result = avg_ranks(df)   # uses LOWER_IS_BETTER default
    idx = result.set_index("team_name")
    # Fewer goals against is better → Goalie A should rank 1
    assert idx.loc["Goalie A", "Goals Against"] == pytest.approx(1.0)
    assert idx.loc["Goalie B", "Goals Against"] == pytest.approx(2.0)


def test_avg_ranks_single_week(matchups_df):
    """Works correctly when there is only one week of data."""
    one_week = matchups_df[matchups_df["week"] == 1].copy()
    result = avg_ranks(one_week, lower_is_better=frozenset({"Goals Against"}))
    assert len(result) == 3
    idx = result.set_index("team_name")
    assert idx.loc["Team A", "Goals"] == pytest.approx(1.0)


def test_avg_ranks_tied_teams_share_min_rank():
    """When two teams tie on a stat, both get the lower rank (method='min')."""
    rows = [
        {"team_key": "t.1", "team_name": "Team A", "week": 1,
         "games_played": 7, "Goals": 10.0},
        {"team_key": "t.2", "team_name": "Team B", "week": 1,
         "games_played": 7, "Goals": 10.0},  # tied with Team A
        {"team_key": "t.3", "team_name": "Team C", "week": 1,
         "games_played": 7, "Goals":  5.0},
    ]
    df = pd.DataFrame(rows)
    result = avg_ranks(df)
    idx = result.set_index("team_name")
    # Both A and B tie at rank 1; C gets rank 3 (not rank 2)
    assert idx.loc["Team A", "Goals"] == pytest.approx(1.0)
    assert idx.loc["Team B", "Goals"] == pytest.approx(1.0)
    assert idx.loc["Team C", "Goals"] == pytest.approx(3.0)
