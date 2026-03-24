import pandas as pd
import pytest

from analysis.waiver_ranking import filter_by_position, rank_players


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal players DataFrame from a list of dicts."""
    defaults = {
        "player_key": "key",
        "player_name": "Player",
        "team_abbr": "TM",
        "display_position": "C",
        "status": "",
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


PLAYERS = make_df([
    {"player_name": "Alice", "display_position": "C",    "Goals": 10.0, "Assists": 20.0, "Goals Against Average": 0.0},
    {"player_name": "Bob",   "display_position": "LW",   "Goals": 20.0, "Assists": 10.0, "Goals Against Average": 0.0},
    {"player_name": "Carol", "display_position": "D",    "Goals":  5.0, "Assists": 30.0, "Goals Against Average": 0.0},
    {"player_name": "Dave",  "display_position": "G",    "Goals":  0.0, "Assists":  0.0, "Goals Against Average": 2.5},
    {"player_name": "Eve",   "display_position": "C,LW", "Goals": 15.0, "Assists": 15.0, "Goals Against Average": 0.0},
])


# ---------------------------------------------------------------------------
# rank_players
# ---------------------------------------------------------------------------

class TestRankPlayers:
    def test_empty_categories_returns_df_with_none_rank(self):
        result = rank_players(PLAYERS, [])
        assert "composite_rank" in result.columns
        assert result["composite_rank"].isna().all()

    def test_single_category_rank_order(self):
        result = rank_players(PLAYERS, ["Goals"])
        # Bob has most goals → rank 1
        assert result.iloc[0]["player_name"] == "Bob"

    def test_composite_rank_sums_per_category_ranks(self):
        # Goals ranking: Bob=1, Eve=2, Alice=3, Carol=4, Dave=5
        # Assists ranking: Carol=1, Alice=2, Eve=3, Bob=4, Dave=5
        # Sum: Carol=5, Eve=5, Alice=5, Bob=5, Dave=10
        # (ties at top, Dave last)
        result = rank_players(PLAYERS, ["Goals", "Assists"])
        assert result.iloc[-1]["player_name"] == "Dave"
        assert result["composite_rank"].iloc[-1] == 10.0

    def test_lower_is_better_stat_ranked_correctly(self):
        goalies = make_df([
            {"player_name": "G1", "Goals Against Average": 3.5},
            {"player_name": "G2", "Goals Against Average": 1.8},
            {"player_name": "G3", "Goals Against Average": 2.2},
        ])
        result = rank_players(goalies, ["Goals Against Average"])
        # Lower GAA = better = rank 1
        assert result.iloc[0]["player_name"] == "G2"
        assert result.iloc[-1]["player_name"] == "G1"

    def test_ties_use_min_rank(self):
        tied = make_df([
            {"player_name": "A", "Goals": 10.0},
            {"player_name": "B", "Goals": 10.0},
            {"player_name": "C", "Goals":  5.0},
        ])
        result = rank_players(tied, ["Goals"])
        # A and B both rank 1, C ranks 3
        top_two = set(result.iloc[:2]["player_name"])
        assert top_two == {"A", "B"}
        assert result.iloc[2]["player_name"] == "C"
        assert result.iloc[2]["composite_rank"] == 3.0

    def test_composite_rank_column_added(self):
        result = rank_players(PLAYERS, ["Goals"])
        assert "composite_rank" in result.columns

    def test_original_df_not_mutated(self):
        original_cols = list(PLAYERS.columns)
        rank_players(PLAYERS, ["Goals"])
        assert list(PLAYERS.columns) == original_cols

    def test_sorted_ascending_by_composite_rank(self):
        result = rank_players(PLAYERS, ["Goals"])
        ranks = result["composite_rank"].tolist()
        assert ranks == sorted(ranks)

    def test_custom_lower_is_better(self):
        df = make_df([
            {"player_name": "A", "Penalty Minutes": 50.0},
            {"player_name": "B", "Penalty Minutes": 10.0},
        ])
        result = rank_players(df, ["Penalty Minutes"], lower_is_better=frozenset({"Penalty Minutes"}))
        assert result.iloc[0]["player_name"] == "B"


# ---------------------------------------------------------------------------
# filter_by_position
# ---------------------------------------------------------------------------

class TestFilterByPosition:
    def test_all_returns_full_df(self):
        result = filter_by_position(PLAYERS, "All")
        assert len(result) == len(PLAYERS)

    def test_forwards_includes_c_lw_rw(self):
        result = filter_by_position(PLAYERS, "Forwards")
        positions = set(result["display_position"])
        assert all(
            any(p in {"C", "LW", "RW", "F"} for p in pos.split(","))
            for pos in positions
        )
        assert "D" not in result["display_position"].values
        assert "G" not in result["display_position"].values

    def test_defence_returns_only_d(self):
        result = filter_by_position(PLAYERS, "Defence")
        assert all(result["display_position"] == "D")

    def test_goalies_returns_only_g(self):
        result = filter_by_position(PLAYERS, "Goalies")
        assert all(result["display_position"] == "G")

    def test_skaters_excludes_goalies(self):
        result = filter_by_position(PLAYERS, "Skaters")
        assert "G" not in result["display_position"].values
        assert len(result) == len(PLAYERS) - 1  # Dave the goalie excluded

    def test_multi_position_player_included(self):
        # Eve has display_position "C,LW" — should appear in Forwards
        result = filter_by_position(PLAYERS, "Forwards")
        assert "Eve" in result["player_name"].values

    def test_multi_position_player_in_skaters(self):
        result = filter_by_position(PLAYERS, "Skaters")
        assert "Eve" in result["player_name"].values

    def test_unknown_group_returns_full_df(self):
        result = filter_by_position(PLAYERS, "Unknown")
        assert len(result) == len(PLAYERS)

    def test_reset_index_after_filter(self):
        result = filter_by_position(PLAYERS, "Goalies")
        assert list(result.index) == list(range(len(result)))
