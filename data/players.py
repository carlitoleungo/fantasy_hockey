"""
Fetch available (unrostered) player data for the waiver wire page.

Two API calls per page of 25 players:
  1. /leagues;league_keys={key}/players — player list with season stats inline
     (out=stats always returns season totals regardless of sort_type)
  2. /players;player_keys={keys}/stats;type=lastmonth — lastmonth stats as a batch

Player DataFrames (season pool and last-month batch) share this structure:
    player_key        str
    player_name       str
    team_abbr         str
    display_position  str    e.g. "C,LW", "D", "G"
    status            str    injury flag e.g. "O", "IR", "" if healthy
    games_played      int    (lastmonth df only — from type=lastmonth response)
    <stat_name>       float  one column per enabled scoring category, same names
                             as the matchups DataFrame so LOWER_IS_BETTER etc. work

The waiver route caches season pools and last-month stats for 24 hours via
data/cache.py; nothing in this module caches.
"""

from __future__ import annotations

import pandas as pd

from data.client import BASE_URL, _as_list, _coerce, _get, get_stat_categories


def get_players_lastmonth_stats(
    session,
    league_key: str,
    player_keys: list[str],
) -> dict[str, dict]:
    """
    Fetch last-30-day stats for an explicit list of player keys (e.g. a roster).

    Fetches stats for a known set of keys in batches of 25.

    Returns:
        {player_key: {stat_name: float, ..., games_played: int}}
        Players with no API response map to {}.
    """
    if not player_keys:
        return {}

    stat_categories = get_stat_categories(session, league_key)
    id_to_name = {
        cat["stat_id"]: cat["stat_name"]
        for cat in stat_categories
        if cat["is_enabled"]
    }

    result: dict[str, dict] = {}
    chunk_size = 25
    for i in range(0, len(player_keys), chunk_size):
        chunk = player_keys[i : i + chunk_size]
        batch = _fetch_page_lastmonth(session, chunk, id_to_name)
        result.update(batch)

    return result


def fetch_season_pool(
    session,
    league_key: str,
    sort_stat_id: str,
    id_to_name: dict,
    position: str | None = None,
    count: int = 25,
) -> pd.DataFrame:
    """
    Fetch the top-`count` available players sorted by sort_stat_id.

    Returns a DataFrame with player metadata + ALL enabled season stat columns.
    All enabled stats come back for free in the same API call (Yahoo's out=stats).

    Parameters
    ----------
    sort_stat_id : Yahoo stat ID string (e.g. "18" for Hits) or "OR" for
                   Overall Rank.
    id_to_name   : {stat_id: stat_name} mapping from get_stat_categories().
    position     : Yahoo position code for server-side filtering (e.g. "G", "D").
    count        : Players to fetch (1–25).
    """
    rows, _ = _fetch_page_season(
        session, league_key, id_to_name, start=0,
        position=position, sort_stat_id=sort_stat_id, count=count,
    )
    return pd.DataFrame(rows)


def fetch_lastmonth_batch(
    session,
    player_keys: list[str],
    id_to_name: dict,
) -> pd.DataFrame:
    """
    Fetch last-30-day stats for a list of player keys in a single batch call.

    Returns a DataFrame with player_key as the first column and one column per
    enabled stat. Players with no API response are omitted.
    """
    if not player_keys:
        return pd.DataFrame()
    lm_by_key = _fetch_page_lastmonth(session, player_keys, id_to_name)
    rows = [{"player_key": pk, **stats} for pk, stats in lm_by_key.items()]
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_page_season(
    session,
    league_key: str,
    id_to_name: dict,
    start: int,
    position: str | None = None,
    sort_stat_id: str = "OR",
    count: int = 25,
) -> tuple[list[dict], list[str]]:
    """
    Fetch one page of available players with season stats inline.

    sort_stat_id: Yahoo stat ID to sort by (e.g. "18" for Hits), or "OR" for
                  Overall Rank (the Yahoo default).
    count: number of players to fetch (max 25 per Yahoo API limits).

    Returns (rows, player_keys). rows is empty if no more players.
    """
    pos_filter = f";position={position}" if position else ""
    url = (
        f"{BASE_URL}/leagues;league_keys={league_key}/players"
        f";status=A{pos_filter};sort={sort_stat_id};sort_type=season"
        f";out=stats;start={start};count={count}"
    )
    data = _get(session, url)
    node = (
        data.get("fantasy_content", {})
        .get("leagues", {})
        .get("league", {})
        .get("players")
    )
    if node is None or int(node.get("@count", 0)) == 0:
        return [], []

    rows = []
    keys = []
    for p in _as_list(node["player"]):
        row = _player_meta(p)
        row.update(_parse_stats(p, id_to_name))
        rows.append(row)
        keys.append(p["player_key"])

    return rows, keys


def _fetch_page_lastmonth(
    session,
    player_keys: list[str],
    id_to_name: dict,
) -> dict[str, dict]:
    """
    Fetch lastmonth stats for a list of player keys in a single batch call.

    Returns {player_key: stats_dict}. Keys with no API response map to {}.
    Caller is responsible for attaching player metadata.
    """
    keys_param = ",".join(player_keys)
    url = f"{BASE_URL}/players;player_keys={keys_param}/stats;type=lastmonth"
    data = _get(session, url)

    raw = data.get("fantasy_content", {}).get("players", {})
    by_key: dict[str, dict] = {}
    if raw and int(raw.get("@count", 0)) > 0:
        for p in _as_list(raw["player"]):
            by_key[p["player_key"]] = _parse_stats(p, id_to_name, include_games_played=True)
    return by_key


def _player_meta(player: dict) -> dict:
    """Extract player metadata fields from a league players response entry."""
    return {
        "player_key": player["player_key"],
        "player_name": player["name"]["full"],
        "team_abbr": player.get("editorial_team_abbr", ""),
        "display_position": player.get("display_position", ""),
        "status": player.get("status", ""),
    }


def _parse_stats(
    player: dict,
    id_to_name: dict,
    include_games_played: bool = False,
) -> dict:
    """
    Extract stat values from a player dict's player_stats node.

    Only includes stat IDs present in id_to_name (enabled scoring stats).
    Optionally extracts stat_id "0" as games_played.
    """
    raw = (
        player.get("player_stats", {})
        .get("stats", {})
        .get("stat")
    )
    if not raw:
        return {}

    stats = {}
    ga_raw: float | None = None  # raw goals-against count (stat_id "22")

    for s in _as_list(raw):
        stat_id = s["stat_id"]
        value = s["value"]
        if include_games_played and stat_id == "0":
            stats["games_played"] = 0 if value in ("-", None) else int(value)
        elif stat_id in id_to_name:
            stats[id_to_name[stat_id]] = _coerce(value)
        # Always capture raw GA even if not a scoring stat — needed to recompute GAA below.
        if include_games_played and stat_id == "22":
            ga_raw = _coerce(value)

    # Yahoo returns the *season* GAA for stat_id "23" even when type=lastmonth.
    # Recompute the correct last-30-day GAA ourselves from raw GA / games_played.
    if include_games_played and "23" in id_to_name and ga_raw is not None:
        gp = stats.get("games_played", 0)
        stats[id_to_name["23"]] = ga_raw / gp if gp > 0 else 0.0

    return stats
