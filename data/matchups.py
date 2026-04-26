"""
Fetch and cache weekly matchup stats for all teams in a league.

Delta fetch pattern:
1. Find the highest week already in the cache
2. Fetch stat categories once (they rarely change mid-season)
3. For each missing week, fetch ALL teams' stats in a single API call
4. Append new rows to the cache
5. Return the full dataset from the cache

Uses the bulk endpoint (/league/{key}/teams/stats;type=week;week={w}) which
returns every team's stats in one request — 1 API call per week instead of
N_teams per week.

On first run with an empty cache this fetches all weeks from start_week to
current_week. On subsequent runs it fetches only missing weeks plus always
re-fetches current_week, because intra-week stats update as games are played.
"""

from __future__ import annotations

from datetime import date as _date

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

    # Always re-fetch the current week — stats update as games are played.
    if current_week >= start_week and current_week not in weeks_to_fetch:
        weeks_to_fetch.append(current_week)

    # Re-fetch the most recently completed week if the cache was last written
    # today — stats from that week may have updated since the earlier fetch.
    prev_week = current_week - 1
    if prev_week >= start_week and prev_week not in weeks_to_fetch:
        lu = cache.last_updated(league_key, "matchups")
        if lu is not None and lu.astimezone().date() == _date.today():
            weeks_to_fetch = [prev_week] + weeks_to_fetch

    if weeks_to_fetch:
        stat_categories = client.get_stat_categories(session, league_key)

        rows = []
        for week in weeks_to_fetch:
            week_rows = client.get_all_teams_week_stats(
                session, league_key, week, stat_categories
            )
            rows.extend(week_rows)

        if rows:
            cache.append(league_key, "matchups", pd.DataFrame(rows))

    result = cache.read(league_key, "matchups")
    if result is not None:
        # Deduplicate: earlier cache corruption (e.g. repeated appends during
        # development) can leave duplicate rows. Keep the last entry per
        # team/week pair so the most recent fetch wins.
        result = result.drop_duplicates(
            subset=["team_key", "week"], keep="last"
        ).reset_index(drop=True)
    return result


def get_current_week(session, league_key: str) -> int:
    """Return the current in-progress week number from Yahoo league settings."""
    settings = client.get_league_settings(session, league_key)
    return settings["current_week"]


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
