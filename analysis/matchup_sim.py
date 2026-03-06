"""
Head-to-head matchup simulation between two teams.

Given the full matchups DataFrame, two team names, and a week range, compute
each team's average stats per category over that range and determine which
team wins each category.

All functions are pure pandas — no Streamlit, no API calls, no cache I/O.

Matchups DataFrame schema (from data.matchups):
    team_key     str
    team_name    str
    week         int
    games_played int
    <stat_name>  float   (one column per enabled scoring category)
"""

from __future__ import annotations

import pandas as pd

from analysis.team_scores import LOWER_IS_BETTER, stat_columns


def simulate(
    df: pd.DataFrame,
    team_a: str,
    team_b: str,
    from_week: int | None = None,
    to_week: int | None = None,
    lower_is_better: frozenset[str] | None = None,
) -> pd.DataFrame:
    """
    Simulate a head-to-head matchup between two teams.

    Parameters
    ----------
    df : DataFrame
        Full matchups DataFrame (all teams, all weeks).
    team_a, team_b : str
        team_name values for the two teams to compare.
    from_week : int or None
        First week to include (inclusive). None = earliest available.
    to_week : int or None
        Last week to include (inclusive). None = latest available.
    lower_is_better : frozenset[str] or None
        Stat names where a lower value is better. Defaults to the
        module-level LOWER_IS_BETTER set.

    Returns
    -------
    DataFrame with columns:
        category   str    — stat name
        team_a     float  — team A's average value
        team_b     float  — team B's average value
        winner     str    — team_a name, team_b name, or "Tie"
    """
    if lower_is_better is None:
        lower_is_better = LOWER_IS_BETTER

    stat_cols = stat_columns(df)

    # Filter to the requested week range
    filtered = df.copy()
    if from_week is not None:
        filtered = filtered[filtered["week"] >= from_week]
    if to_week is not None:
        filtered = filtered[filtered["week"] <= to_week]

    # Compute per-team averages over the period
    a_avg = (
        filtered[filtered["team_name"] == team_a][stat_cols]
        .mean()
    )
    b_avg = (
        filtered[filtered["team_name"] == team_b][stat_cols]
        .mean()
    )

    # Determine winner per category
    rows: list[dict] = []
    for col in stat_cols:
        a_val = a_avg[col]
        b_val = b_avg[col]

        if col in lower_is_better:
            # Lower is better — the team with the smaller average wins
            if a_val < b_val:
                winner = team_a
            elif b_val < a_val:
                winner = team_b
            else:
                winner = "Tie"
        else:
            # Higher is better
            if a_val > b_val:
                winner = team_a
            elif b_val > a_val:
                winner = team_b
            else:
                winner = "Tie"

        rows.append({
            "category": col,
            "team_a": a_val,
            "team_b": b_val,
            "winner": winner,
        })

    return pd.DataFrame(rows)


def tally(sim_df: pd.DataFrame, team_a: str, team_b: str) -> dict:
    """
    Summarise a simulation result into win/loss/tie counts.

    Returns a dict:
        {team_a_name: int, team_b_name: int, "Tie": int}
    """
    counts = sim_df["winner"].value_counts()
    return {
        team_a: int(counts.get(team_a, 0)),
        team_b: int(counts.get(team_b, 0)),
        "Tie": int(counts.get("Tie", 0)),
    }
