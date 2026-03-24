"""
Fetch available (unrostered) player data for the waiver wire page.

Two API calls per page of 25 players:
  1. /leagues;league_keys={key}/players — player list with season stats inline
     (out=stats always returns season totals regardless of sort_type)
  2. /players;player_keys={keys}/stats;type=lastmonth — lastmonth stats as a batch

Returns two DataFrames with identical structure:
    player_key        str
    player_name       str
    team_abbr         str
    display_position  str    e.g. "C,LW", "D", "G"
    status            str    injury flag e.g. "O", "IR", "" if healthy
    games_played      int    (lastmonth df only — from type=lastmonth response)
    <stat_name>       float  one column per enabled scoring category, same names
                             as the matchups DataFrame so LOWER_IS_BETTER etc. work

Available players change constantly — never cache this data.
"""

from __future__ import annotations

import pandas as pd

from data.client import BASE_URL, _as_list, _coerce, _get, get_stat_categories


def get_available_players(
    session,
    league_key: str,
    max_players: int = 100,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch available (unrostered) players sorted by overall rank.

    Returns (season_df, lastmonth_df). Both DataFrames have the same rows and
    metadata columns; stat values reflect the respective time period.
    lastmonth_df also includes a games_played column.
    """
    stat_categories = get_stat_categories(session, league_key)
    id_to_name = {
        cat["stat_id"]: cat["stat_name"]
        for cat in stat_categories
        if cat["is_enabled"]
    }

    season_rows: list[dict] = []
    lastmonth_rows: list[dict] = []
    start = 0

    while len(season_rows) < max_players:
        page_season, page_keys = _fetch_page_season(session, league_key, id_to_name, start)
        if not page_season:
            break

        # {player_key: stats_dict} — metadata comes from page_season
        lm_stats_by_key = _fetch_page_lastmonth(session, page_keys, id_to_name)

        season_rows.extend(page_season)
        for row in page_season:
            lm_row = {
                "player_key": row["player_key"],
                "player_name": row["player_name"],
                "team_abbr": row["team_abbr"],
                "display_position": row["display_position"],
                "status": row["status"],
            }
            lm_row.update(lm_stats_by_key.get(row["player_key"], {}))
            lastmonth_rows.append(lm_row)

        if len(page_season) < 25:
            break
        start += 25

    return pd.DataFrame(season_rows), pd.DataFrame(lastmonth_rows)


def get_players_lastmonth_stats(
    session,
    league_key: str,
    player_keys: list[str],
) -> dict[str, dict]:
    """
    Fetch last-30-day stats for an explicit list of player keys (e.g. a roster).

    Unlike get_available_players(), this does not paginate through waiver wire
    players — it fetches stats for a known set of keys in batches of 25.

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


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_page_season(
    session,
    league_key: str,
    id_to_name: dict,
    start: int,
) -> tuple[list[dict], list[str]]:
    """
    Fetch one page of available players with season stats inline.

    Returns (rows, player_keys). rows is empty if no more players.
    """
    url = (
        f"{BASE_URL}/leagues;league_keys={league_key}/players"
        f";status=A;sort=OR;sort_type=season;out=stats;start={start};count=25"
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
    for s in _as_list(raw):
        stat_id = s["stat_id"]
        value = s["value"]
        if include_games_played and stat_id == "0":
            stats["games_played"] = 0 if value in ("-", None) else int(value)
        elif stat_id in id_to_name:
            stats[id_to_name[stat_id]] = _coerce(value)
    return stats
