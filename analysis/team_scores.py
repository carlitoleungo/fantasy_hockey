"""
Weekly team scores and average category ranks for the league overview page.

All functions are pure pandas — no Streamlit, no API calls, no cache I/O.
They accept the matchups DataFrame produced by data.matchups.get_matchups()
and return plain DataFrames ready for the UI to display.

Matchups DataFrame schema (from data.matchups):
    team_key     str
    team_name    str
    week         int
    games_played int
    <stat_name>  float   (one column per enabled scoring category)

The stat column names are the full Yahoo stat names, e.g.
"Goals", "Assists", "Shots on Goal", "Goals Against Average", etc.
"""

from __future__ import annotations

import pandas as pd

# Stats where a lower value is better (e.g. goalie stats).
# Used as the default in avg_ranks(); callers can override.
LOWER_IS_BETTER: frozenset[str] = frozenset({
    "Goals Against",
    "Goals Against Average",
    "GA",
    "GAA",
})

# Columns that carry metadata rather than scoreable stat values.
_META_COLS: frozenset[str] = frozenset({"team_key", "team_name", "week", "games_played"})


def stat_columns(df: pd.DataFrame) -> list[str]:
    """Return the ordered list of stat column names (everything except metadata)."""
    return [c for c in df.columns if c not in _META_COLS]


def weekly_scores(df: pd.DataFrame, week: int) -> pd.DataFrame:
    """
    Return one row per team showing their raw scores for the given week.

    Columns: team_name, then one column per stat (metadata columns dropped).
    Sorted alphabetically by team_name.
    """
    week_df = df[df["week"] == week].copy()
    cols = ["team_name"] + stat_columns(df)
    return (
        week_df[cols]
        .sort_values("team_name")
        .reset_index(drop=True)
    )


def weekly_scores_ranked(
    df: pd.DataFrame,
    week: int,
    lower_is_better: frozenset[str] | None = None,
) -> pd.DataFrame:
    """
    Return one row per team for the given week with raw stats and an avg_rank
    column. Sorted by avg_rank ascending (best team first).

    Columns: team_name, {stat_name...}, avg_rank

    Ranks use method='min' for ties (consistent with avg_ranks()).
    """
    if lower_is_better is None:
        lower_is_better = LOWER_IS_BETTER

    stat_cols = stat_columns(df)
    week_df = df[df["week"] == week].copy()
    result = week_df[["team_name"] + stat_cols].reset_index(drop=True)

    per_cat_ranks = pd.DataFrame(index=result.index)
    for col in stat_cols:
        ascending = col in lower_is_better
        per_cat_ranks[col] = result[col].rank(method="min", ascending=ascending)

    result["avg_rank"] = per_cat_ranks.mean(axis=1)
    return result.sort_values("avg_rank").reset_index(drop=True)


def avg_ranks(
    df: pd.DataFrame,
    lower_is_better: frozenset[str] | None = None,
    exclude_weeks: set[int] | None = None,
) -> pd.DataFrame:
    """
    Compute each team's average rank per stat category across all weeks.

    Within each week, teams are ranked for every stat (rank 1 = best).
    For most stats, highest value = best. Stats listed in lower_is_better
    are ranked the other way (lowest value = rank 1).
    Ties receive the same (minimum) rank.

    exclude_weeks: week numbers to omit from the calculation (e.g. the
    current in-progress week whose data is partial).

    Returns a DataFrame with columns:
        team_name   str
        <stat_name> float  (average rank across all weeks, 1 = best)
        avg_rank    float  (mean of all per-category avg ranks)

    Sorted by avg_rank ascending (best overall team first).
    """
    if lower_is_better is None:
        lower_is_better = LOWER_IS_BETTER
    if exclude_weeks:
        df = df[~df["week"].isin(exclude_weeks)]

    stat_cols = stat_columns(df)
    ranked_parts: list[pd.DataFrame] = []

    for _, week_df in df.groupby("week"):
        ranks = week_df[["team_name"]].copy().reset_index(drop=True)
        week_vals = week_df.reset_index(drop=True)
        for col in stat_cols:
            ascending = col in lower_is_better
            ranks[col] = week_vals[col].rank(method="min", ascending=ascending)
        ranked_parts.append(ranks)

    all_ranks = pd.concat(ranked_parts, ignore_index=True)

    result = (
        all_ranks
        .groupby("team_name")[stat_cols]
        .mean()
        .assign(avg_rank=lambda d: d[stat_cols].mean(axis=1))
        .sort_values("avg_rank")
        .reset_index()          # team_name becomes a regular column
    )

    return result
