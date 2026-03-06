"""
Unit tests for analysis/matchup_sim.py.

Uses a hand-built matchups DataFrame with known stat values so that expected
averages and winners can be verified precisely.

Fixture structure — 3 teams × 4 weeks:

    Goals (higher is better):
        Team A: week 1=10, week 2=8, week 3=6, week 4=4   → full avg 7.0
        Team B: week 1=4,  week 2=6, week 3=8, week 4=10  → full avg 7.0
        Team C: week 1=2,  week 2=2, week 3=2, week 4=2   → full avg 2.0

    Assists (higher is better):
        Team A: 5 every week  → avg 5.0
        Team B: 3 every week  → avg 3.0
        Team C: 9 every week  → avg 9.0

    Goals Against (lower is better):
        Team A: 2 every week  → avg 2.0
        Team B: 4 every week  → avg 4.0
        Team C: 1 every week  → avg 1.0
"""

import pandas as pd
import pytest

from analysis.matchup_sim import simulate, tally

LIB = frozenset({"Goals Against"})  # lower_is_better for these tests


@pytest.fixture
def matchups_df() -> pd.DataFrame:
    rows = []
    a_goals = [10, 8, 6, 4]
    b_goals = [4, 6, 8, 10]
    for i, week in enumerate([1, 2, 3, 4]):
        rows += [
            {"team_key": "t.1", "team_name": "Team A", "week": week,
             "games_played": 7, "Goals": float(a_goals[i]),
             "Assists": 5.0, "Goals Against": 2.0},
            {"team_key": "t.2", "team_name": "Team B", "week": week,
             "games_played": 7, "Goals": float(b_goals[i]),
             "Assists": 3.0, "Goals Against": 4.0},
            {"team_key": "t.3", "team_name": "Team C", "week": week,
             "games_played": 7, "Goals": 2.0,
             "Assists": 9.0, "Goals Against": 1.0},
        ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# simulate() — full season (no week range)
# ---------------------------------------------------------------------------

def test_simulate_returns_one_row_per_category(matchups_df):
    result = simulate(matchups_df, "Team A", "Team B", lower_is_better=LIB)
    assert len(result) == 3  # Goals, Assists, Goals Against


def test_simulate_has_expected_columns(matchups_df):
    result = simulate(matchups_df, "Team A", "Team B", lower_is_better=LIB)
    assert list(result.columns) == ["category", "team_a", "team_b", "winner"]


def test_simulate_full_season_averages(matchups_df):
    """A and B both average 7.0 Goals over all 4 weeks → Tie."""
    result = simulate(matchups_df, "Team A", "Team B", lower_is_better=LIB)
    goals = result[result["category"] == "Goals"].iloc[0]
    assert goals["team_a"] == pytest.approx(7.0)
    assert goals["team_b"] == pytest.approx(7.0)
    assert goals["winner"] == "Tie"


def test_simulate_higher_is_better_winner(matchups_df):
    """A averages 5.0 Assists vs B's 3.0 → A wins Assists."""
    result = simulate(matchups_df, "Team A", "Team B", lower_is_better=LIB)
    assists = result[result["category"] == "Assists"].iloc[0]
    assert assists["winner"] == "Team A"


def test_simulate_lower_is_better_winner(matchups_df):
    """A averages 2.0 GA vs B's 4.0 → A wins Goals Against (lower = better)."""
    result = simulate(matchups_df, "Team A", "Team B", lower_is_better=LIB)
    ga = result[result["category"] == "Goals Against"].iloc[0]
    assert ga["winner"] == "Team A"


def test_simulate_lower_is_better_loser(matchups_df):
    """B averages 4.0 GA vs C's 1.0 → C wins Goals Against."""
    result = simulate(matchups_df, "Team B", "Team C", lower_is_better=LIB)
    ga = result[result["category"] == "Goals Against"].iloc[0]
    assert ga["winner"] == "Team C"


# ---------------------------------------------------------------------------
# simulate() — week range filtering
# ---------------------------------------------------------------------------

def test_simulate_from_week_filters_earlier_weeks(matchups_df):
    """Weeks 3–4 only: A Goals avg = (6+4)/2 = 5.0, B Goals avg = (8+10)/2 = 9.0."""
    result = simulate(matchups_df, "Team A", "Team B",
                      from_week=3, lower_is_better=LIB)
    goals = result[result["category"] == "Goals"].iloc[0]
    assert goals["team_a"] == pytest.approx(5.0)
    assert goals["team_b"] == pytest.approx(9.0)
    assert goals["winner"] == "Team B"


def test_simulate_to_week_filters_later_weeks(matchups_df):
    """Weeks 1–2 only: A Goals avg = (10+8)/2 = 9.0, B Goals avg = (4+6)/2 = 5.0."""
    result = simulate(matchups_df, "Team A", "Team B",
                      to_week=2, lower_is_better=LIB)
    goals = result[result["category"] == "Goals"].iloc[0]
    assert goals["team_a"] == pytest.approx(9.0)
    assert goals["team_b"] == pytest.approx(5.0)
    assert goals["winner"] == "Team A"


def test_simulate_from_and_to_week_combined(matchups_df):
    """Weeks 2–3 only: A Goals = (8+6)/2 = 7.0, B Goals = (6+8)/2 = 7.0 → Tie."""
    result = simulate(matchups_df, "Team A", "Team B",
                      from_week=2, to_week=3, lower_is_better=LIB)
    goals = result[result["category"] == "Goals"].iloc[0]
    assert goals["team_a"] == pytest.approx(7.0)
    assert goals["team_b"] == pytest.approx(7.0)
    assert goals["winner"] == "Tie"


def test_simulate_single_week(matchups_df):
    """Week 4 only: A Goals = 4.0, B Goals = 10.0."""
    result = simulate(matchups_df, "Team A", "Team B",
                      from_week=4, to_week=4, lower_is_better=LIB)
    goals = result[result["category"] == "Goals"].iloc[0]
    assert goals["team_a"] == pytest.approx(4.0)
    assert goals["team_b"] == pytest.approx(10.0)
    assert goals["winner"] == "Team B"


# ---------------------------------------------------------------------------
# simulate() — edge cases
# ---------------------------------------------------------------------------

def test_simulate_team_order_reflected_in_columns(matchups_df):
    """team_a column always corresponds to the first team argument."""
    r1 = simulate(matchups_df, "Team A", "Team B", lower_is_better=LIB)
    r2 = simulate(matchups_df, "Team B", "Team A", lower_is_better=LIB)

    assists_1 = r1[r1["category"] == "Assists"].iloc[0]
    assists_2 = r2[r2["category"] == "Assists"].iloc[0]

    assert assists_1["team_a"] == pytest.approx(5.0)  # Team A's value
    assert assists_2["team_a"] == pytest.approx(3.0)  # Team B's value (now team_a)


def test_simulate_all_categories_present(matchups_df):
    """Every stat category in the DataFrame should appear in the result."""
    result = simulate(matchups_df, "Team A", "Team C", lower_is_better=LIB)
    categories = set(result["category"])
    assert categories == {"Goals", "Assists", "Goals Against"}


def test_simulate_uses_default_lower_is_better(matchups_df):
    """When lower_is_better is None, module default is used."""
    result = simulate(matchups_df, "Team A", "Team B")
    ga = result[result["category"] == "Goals Against"].iloc[0]
    # Team A avg 2.0 vs Team B avg 4.0 → A wins (lower is better by default)
    assert ga["winner"] == "Team A"


# ---------------------------------------------------------------------------
# tally()
# ---------------------------------------------------------------------------

def test_tally_counts(matchups_df):
    """Full season A vs B: Goals=Tie, Assists=A wins, GA=A wins → A:2, B:0, Tie:1."""
    sim = simulate(matchups_df, "Team A", "Team B", lower_is_better=LIB)
    result = tally(sim, "Team A", "Team B")
    assert result["Team A"] == 2
    assert result["Team B"] == 0
    assert result["Tie"] == 1


def test_tally_with_week_range(matchups_df):
    """Weeks 3–4: Goals=B wins, Assists=A wins, GA=A wins → A:2, B:1, Tie:0."""
    sim = simulate(matchups_df, "Team A", "Team B",
                   from_week=3, lower_is_better=LIB)
    result = tally(sim, "Team A", "Team B")
    assert result["Team A"] == 2
    assert result["Team B"] == 1
    assert result["Tie"] == 0


def test_tally_keys_match_team_names(matchups_df):
    sim = simulate(matchups_df, "Team A", "Team C", lower_is_better=LIB)
    result = tally(sim, "Team A", "Team C")
    assert set(result.keys()) == {"Team A", "Team C", "Tie"}


def test_tally_all_ties():
    """When every category is a tie, both teams have 0 wins."""
    sim = pd.DataFrame([
        {"category": "Goals", "team_a": 5.0, "team_b": 5.0, "winner": "Tie"},
        {"category": "Assists", "team_a": 3.0, "team_b": 3.0, "winner": "Tie"},
    ])
    result = tally(sim, "X", "Y")
    assert result["X"] == 0
    assert result["Y"] == 0
    assert result["Tie"] == 2
