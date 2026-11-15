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


def lower_is_better_from_categories(categories: list[dict]) -> frozenset[str]:
    """
    Build a lower-is-better frozenset from fetched stat category dicts.

    Each dict is expected to have 'stat_name' and optionally 'lower_is_better'.
    Falls back to matching against the module-level LOWER_IS_BETTER constant for
    any category that lacks the 'lower_is_better' field.
    """
    result = set()
    for c in categories:
        if c.get("lower_is_better") or c["stat_name"] in LOWER_IS_BETTER:
            result.add(c["stat_name"])
    return frozenset(result)


def category_winner(a: float, b: float, lower_is_better: bool) -> str:
    """
    Decide one category between two values: "a", "b", or "tie".

    Higher wins unless lower_is_better (e.g. Goals Against Average). Equal
    values, or a NaN on either side (a team with no weeks in range), tie.
    """
    def beats(x: float, y: float) -> bool:
        return x < y if lower_is_better else x > y

    if beats(a, b):
        return "a"
    if beats(b, a):
        return "b"
    return "tie"


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



def rank_shade_levels(
    values: pd.DataFrame,
    lower_is_better: frozenset[str] | None = None,
) -> pd.DataFrame:
    """
    Shade levels for the Leaderboard, one int column per stat column in
    `values` (one row per team): 4 = best in the column, 0 = no shade.

    Teams at the top of a column (ties included) get 4. Everyone else is placed
    by f = (rank - 1) / (teams - 1), using the *average* rank of a tied group:
    f < .3 → 3, f < .6 → 2, f < .85 → 1, and the bottom ~15 % get no shade.
    Averaging ties stops a block of zeros (say nine teams with no shutouts)
    from all inheriting the high "min" rank that sits just below the leaders.
    The f scale keeps the leader bold in an 8-team league as well as a
    14-team one (a percentile cut like the Waiver Wire's would not).

    A column where every team is tied (a week with no games yet) gets no
    shading at all, rather than every cell looking like the best. Missing
    values get 0.
    """
    if lower_is_better is None:
        lower_is_better = LOWER_IS_BETTER

    out = pd.DataFrame(index=values.index)
    for col in values.columns:
        v = pd.to_numeric(values[col], errors="coerce")
        n = v.notna().sum()
        if n < 2 or v.nunique(dropna=True) <= 1:
            out[col] = 0
            continue
        ascending = col in lower_is_better
        top = v.rank(method="min", ascending=ascending) == 1
        f = (v.rank(method="average", ascending=ascending) - 1) / (n - 1)
        level = pd.Series(0, index=values.index)
        level = level.mask(f < 0.85, 1).mask(f < 0.6, 2).mask(f < 0.3, 3).mask(top, 4)
        out[col] = level.where(v.notna(), 0).astype(int)
    return out
