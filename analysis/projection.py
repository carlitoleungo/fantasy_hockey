"""
Project final weekly stats for a fantasy team.

Given current week-to-date stats, a roster with last-30-day per-player stats,
and remaining NHL games per team, compute projected final totals for the week.

All functions are pure Python — no Streamlit, no API calls, no cache I/O.
"""
from __future__ import annotations

from analysis.team_scores import LOWER_IS_BETTER


_RATE_STAT_ABBRS: frozenset[str] = frozenset({"GAA", "SV%", "GSAA"})


def _is_rate_stat(name: str) -> bool:
    """Return True for stats that are already a per-game rate (e.g. GAA, SV%)."""
    if name in _RATE_STAT_ABBRS:
        return True
    lower = name.lower()
    return "average" in lower or "percentage" in lower or "%" in lower


def project_team_stats(
    current_stats: dict[str, float],
    roster: list[dict],
    lastmonth_stats: dict[str, dict],
    games_remaining: dict[str, int],
    stat_categories: list[dict],
) -> dict[str, float]:
    """
    Compute projected final stats for a team for the current week.

    projected[stat] = current[stat]
                    + Σ_players (lastmonth_stat / games_played * remaining_games)

    Players with games_played == 0 or no remaining games contribute nothing.

    Args:
        current_stats:    {stat_name: current_value} for the team's week so far
        roster:           list of {player_key, team_abbr, ...} from get_team_roster()
        lastmonth_stats:  {player_key: {stat_name: float, games_played: int}}
        games_remaining:  {team_abbr: remaining_game_count} from get_remaining_games()
        stat_categories:  list of {stat_id, stat_name, is_enabled, ...}

    Returns:
        {stat_name: projected_total} for each enabled category
    """
    enabled = [c["stat_name"] for c in stat_categories if c["is_enabled"]]
    projected = {stat: float(current_stats.get(stat, 0.0)) for stat in enabled}

    # Rate stats (GAA, SV%) need a weighted average, not a sum.
    # Accumulate numerator (rate × weight) and total weight separately.
    rate_numerator: dict[str, float] = {s: 0.0 for s in enabled if _is_rate_stat(s)}
    rate_weight: dict[str, float] = {s: 0.0 for s in enabled if _is_rate_stat(s)}

    for player in roster:
        remaining = games_remaining.get(player["team_abbr"], 0)
        if remaining == 0:
            continue

        lm = lastmonth_stats.get(player["player_key"], {})
        gp = lm.get("games_played", 0)
        if gp == 0:
            continue

        for stat in enabled:
            if stat in rate_numerator:
                rate = lm.get(stat, 0.0)
                if rate != 0.0:  # skip players with no data for this rate stat
                    rate_numerator[stat] += rate * remaining
                    rate_weight[stat] += remaining
            else:
                per_game = lm.get(stat, 0.0) / gp
                projected[stat] += per_game * remaining

    # Resolve rate stats: weighted average across contributing players.
    # If no players contributed, leave the current value unchanged.
    for stat in rate_numerator:
        if rate_weight[stat] > 0:
            projected[stat] = rate_numerator[stat] / rate_weight[stat]

    return projected


def compare_projections(
    team_a: dict[str, float],
    team_b: dict[str, float],
    stat_categories: list[dict],
    lower_is_better: frozenset[str] | None = None,
) -> list[dict]:
    """
    Compare two teams' projected stats and determine a winner per category.

    Args:
        team_a, team_b:   projected stat dicts from project_team_stats()
        stat_categories:  list of {stat_id, stat_name, is_enabled, ...}
        lower_is_better:  stat names where lower value wins; defaults to LOWER_IS_BETTER

    Returns:
        list of {
            "category": str,
            "team_a":   float,
            "team_b":   float,
            "winner":   "team_a" | "team_b" | "Tie"
        }
    """
    if lower_is_better is None:
        lower_is_better = LOWER_IS_BETTER

    enabled = [c["stat_name"] for c in stat_categories if c["is_enabled"]]
    rows = []

    for stat in enabled:
        a_val = team_a.get(stat, 0.0)
        b_val = team_b.get(stat, 0.0)

        if stat in lower_is_better:
            if a_val < b_val:
                winner = "team_a"
            elif b_val < a_val:
                winner = "team_b"
            else:
                winner = "Tie"
        else:
            if a_val > b_val:
                winner = "team_a"
            elif b_val > a_val:
                winner = "team_b"
            else:
                winner = "Tie"

        rows.append({"category": stat, "team_a": a_val, "team_b": b_val, "winner": winner})

    return rows
