"""
Rank available players by performance in selected stat categories.

All functions are pure pandas — no API calls, no Streamlit, no cache I/O.
They accept DataFrames produced by data.players.get_available_players() and
return plain DataFrames ready for the UI to display.

Player DataFrame schema (from data.players):
    player_key        str
    player_name       str
    team_abbr         str
    display_position  str    e.g. "C,LW", "D", "G"
    status            str    injury flag, "" if healthy
    games_played      int    (lastmonth df only)
    <stat_name>       float  one column per enabled scoring category
"""

from __future__ import annotations

import pandas as pd

from analysis.team_scores import LOWER_IS_BETTER

# Metadata columns that are never stat categories.
_META_COLS: frozenset[str] = frozenset({
    "player_key", "player_name", "team_abbr",
    "display_position", "status", "games_played",
})


def rank_players(
    df: pd.DataFrame,
    selected_categories: list[str],
    lower_is_better: frozenset[str] | None = None,
) -> pd.DataFrame:
    """
    Add a composite_rank column and return df sorted ascending by it.

    For each selected category, players are ranked 1–N (1 = best). The
    composite_rank is the sum of those per-category ranks — lower is better.
    Ties within a category use method='min' (consistent with team_scores.py).

    If selected_categories is empty, returns df unchanged with
    composite_rank set to None for all rows.
    """
    if lower_is_better is None:
        lower_is_better = LOWER_IS_BETTER

    result = df.copy()

    if not selected_categories:
        result["composite_rank"] = None
        return result

    rank_sum = pd.Series(0.0, index=result.index)
    for col in selected_categories:
        ascending = col in lower_is_better
        col_values = result[col]
        if ascending:
            # A coerced 0.0 (from '-', i.e. non-goalies in GAA) must not
            # outrank players with real values. Replace 0.0 with NaN and
            # push NaN to the bottom of the ranking.
            col_values = col_values.replace(0.0, float("nan"))
            rank_sum += col_values.rank(method="min", ascending=True, na_option="bottom")
        else:
            rank_sum += col_values.rank(method="min", ascending=False)

    result["composite_rank"] = rank_sum
    return result.sort_values("composite_rank").reset_index(drop=True)


def filter_by_position(df: pd.DataFrame, position_group: str) -> pd.DataFrame:
    """
    Filter players by position group.

    position_group values:
        "All"       — no filter
        "Skaters"   — forwards and defensemen (excludes goalies)
        "Forwards"  — C, LW, RW
        "Defence"   — D only
        "Goalies"   — G only

    Filtering uses display_position (e.g. "C,LW", "D", "G"), splitting on
    commas and checking for overlap with the target position set.
    """
    if position_group == "All":
        return df

    targets: frozenset[str] = _POSITION_GROUPS.get(position_group, frozenset())
    if not targets:
        return df

    mask = df["display_position"].apply(
        lambda pos: bool(targets & set(pos.split(",")))
    )
    return df[mask].reset_index(drop=True)


_POSITION_GROUPS: dict[str, frozenset[str]] = {
    # Named groups
    "Skaters":  frozenset({"C", "LW", "RW", "F", "D"}),
    "Forwards": frozenset({"C", "LW", "RW", "F"}),
    "Defence":  frozenset({"D"}),
    "Goalies":  frozenset({"G"}),
    # Individual position codes (used by the waiver wire pill buttons)
    "C":  frozenset({"C"}),
    "LW": frozenset({"LW"}),
    "RW": frozenset({"RW"}),
    "D":  frozenset({"D"}),
    "G":  frozenset({"G"}),
}
