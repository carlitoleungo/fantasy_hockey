"""
Fetch and cache weekly matchup stats for all teams in a league.

Delta fetch pattern:
1. Find the highest week already in the cache
2. Fetch stat categories and team list once (they rarely change mid-season)
3. For each missing week, fetch every team's stats and collect into rows
4. Append new rows to the cache
5. Return the full dataset from the cache

On first run with an empty cache this fetches all weeks from start_week to
current_week. On subsequent runs it only fetches weeks that aren't cached yet.

The current week's stats are fetched once when that week first becomes the
current week. They won't be refreshed until the next week starts (which
advances current_week). This is acceptable for a daily-use tool; if fresher
intra-week data is needed later, add a force_refresh flag.
"""

from __future__ import annotations

import pandas as pd

from data import cache, client


def get_matchups(session, league_key: str) -> pd.DataFrame | None:
    """
    Return a DataFrame of weekly stats for all teams, fetching only new weeks.

    Columns: team_key, team_name, week, games_played, {stat_name...}
    Returns None if there is no data (e.g. season hasn't started yet).
    """
    settings = client.get_league_settings(session, league_key)
    current_week = settings["current_week"]
    start_week = settings["start_week"]

    last_week = _last_cached_week(league_key)
    fetch_from = start_week if last_week is None else last_week + 1
    weeks_to_fetch = list(range(fetch_from, current_week + 1))

    if weeks_to_fetch:
        stat_categories = client.get_stat_categories(session, league_key)
        teams = client.get_teams(session, league_key)

        rows = []
        for week in weeks_to_fetch:
            for team in teams:
                row = client.get_team_week_stats(
                    session, team["team_key"], week, stat_categories
                )
                row["team_name"] = team["team_name"]
                rows.append(row)

        if rows:
            cache.append(league_key, "matchups", pd.DataFrame(rows))

    return cache.read(league_key, "matchups")


def _last_cached_week(league_key: str) -> int | None:
    """
    Return the highest week number stored in the cache, or None if empty.

    We read the actual data (not just the last_updated timestamp) because
    what matters for delta fetching is which week numbers exist, not when
    they were written. Using max(week) is robust to out-of-order writes.
    """
    df = cache.read(league_key, "matchups")
    if df is None or df.empty:
        return None
    return int(df["week"].max())
