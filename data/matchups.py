"""
Fetch and cache weekly matchup stats for all teams in a league.

Delta fetch pattern:
1. Find the highest week already in the cache
2. Fetch stat categories once (they rarely change mid-season)
3. For each missing week, fetch ALL teams' stats in a single API call
4. Merge new rows into the cached frame, keeping one row per (team_key, week),
   and overwrite the parquet with the result
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
            _merge_into_cache(league_key, pd.DataFrame(rows))

    result = cache.read(league_key, "matchups")
    if result is not None:
        # Defence in depth: the write path above keeps the parquet free of
        # duplicates, but a file bloated by the pre-038 append behaviour may
        # still be on disk. Keep the last entry per team/week pair so the most
        # recent fetch wins; the file self-heals on the next write.
        result = result.drop_duplicates(
            subset=["team_key", "week"], keep="last"
        ).reset_index(drop=True)
    return result


def get_current_week(session, league_key: str) -> int:
    """Return the current in-progress week number from Yahoo league settings."""
    settings = client.get_league_settings(session, league_key)
    return settings["current_week"]


def _merge_into_cache(league_key: str, fetched: pd.DataFrame) -> None:
    """
    Overwrite the matchups parquet with the cached rows plus the fetched ones,
    keeping a single row per (team_key, week).

    Appending would grow the file on every call: current_week is re-fetched
    unconditionally and prev_week is re-fetched all day once the cache has been
    written today. Concatenating existing-first and dropping duplicates with
    keep="last" lets the fresh fetch win while keeping the file bounded to the
    distinct (team_key, week) pairs.
    """
    existing = cache.read(league_key, "matchups")
    if existing is not None and not existing.empty:
        fetched = pd.concat([existing, fetched], ignore_index=True)
    merged = fetched.drop_duplicates(
        subset=["team_key", "week"], keep="last"
    ).reset_index(drop=True)
    cache.write(league_key, "matchups", merged)


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
