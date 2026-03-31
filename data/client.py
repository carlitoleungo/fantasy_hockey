"""
Raw Yahoo Fantasy API calls.

All functions accept a requests.Session (from auth.oauth.get_session()) and
return plain Python structures — no Streamlit, no pandas, no cache logic here.

API base: https://fantasysports.yahooapis.com/fantasy/v2
Responses: XML -> xmltodict -> dict. The single-item list gotcha (xmltodict
returns a dict instead of a list when @count == 1) is handled at this layer
so callers never see it.
"""

from __future__ import annotations

import json

import xmltodict

BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get(session, url: str, timeout: int = 15) -> dict:
    """
    GET a Yahoo API URL, parse the XML response to a dict.

    Raises requests.Timeout if the server doesn't respond within `timeout`
    seconds, preventing indefinite hangs on slow or inactive-league calls.
    """
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    # json.dumps/loads round-trip converts OrderedDicts from xmltodict to plain dicts
    return json.loads(json.dumps(xmltodict.parse(response.content)))


def _as_list(value) -> list:
    """
    Normalise a value that may be a dict or a list to always be a list.

    xmltodict collapses a collection with exactly one child element to a dict
    instead of a one-element list. Always call this before iterating over any
    collection that could theoretically have one item.
    """
    return value if isinstance(value, list) else [value]


def _coerce(value) -> float:
    """
    Coerce a raw stat value to float.
    '-' means the team/player had no activity in this period; treat as 0.
    None can appear when the API omits a value entirely; also treat as 0.
    """
    if value is None or value == "-":
        return 0.0
    return float(value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_league_settings(session, league_key: str) -> dict:
    """
    Return week boundaries for the league: current_week, start_week, end_week.
    Calls the settings endpoint (same one used for stat categories).
    """
    data = _get(session, f"{BASE_URL}/league/{league_key}/settings")
    league = data["fantasy_content"]["league"]
    return {
        "current_week": int(league["current_week"]),
        "start_week": int(league["start_week"]),
        "end_week": int(league["end_week"]),
    }


# Stat names/abbreviations where a lower value is better (e.g. goalie "against" stats).
# Used as a heuristic when the Yahoo API does not provide sort_order information.
_LOWER_IS_BETTER_NAMES: frozenset[str] = frozenset({
    "Goals Against",
    "Goals Against Average",
    "GA",
    "GAA",
})


def _is_lower_better(stat_name: str, abbreviation: str) -> bool:
    """Return True if this stat should be ranked ascending (lower value = better)."""
    return stat_name in _LOWER_IS_BETTER_NAMES or abbreviation in _LOWER_IS_BETTER_NAMES


def get_stat_categories(session, league_key: str) -> list[dict]:
    """
    Return stat category metadata for the league.

    Each dict has: stat_id, stat_name, abbreviation, stat_group, is_enabled,
    lower_is_better.
    Non-scoring display stats (is_only_display_stat == '1') are included with
    is_enabled=False so callers can filter them out explicitly.
    """
    data = _get(session, f"{BASE_URL}/league/{league_key}/settings")
    raw_stats = data["fantasy_content"]["league"]["settings"]["stat_categories"]["stats"]["stat"]

    categories = []
    for stat in _as_list(raw_stats):
        # stat_position_type can be a single dict or a list when a stat applies
        # to multiple position types (e.g. Assists applies to skaters and goalies)
        pos_types = _as_list(stat["stat_position_types"]["stat_position_type"])
        is_display = any(
            p.get("is_only_display_stat", "0") == "1" for p in pos_types
        )
        name = stat["name"]
        abbr = stat["display_name"]
        categories.append({
            "stat_id": stat["stat_id"],
            "stat_name": name,
            "abbreviation": abbr,
            "stat_group": stat["group"],
            "is_enabled": not is_display,
            "lower_is_better": _is_lower_better(name, abbr),
        })

    return categories


def get_settings_and_categories(
    session, league_key: str
) -> tuple[dict, list[dict]]:
    """
    Return league settings and stat categories in a single API call.

    Combines get_league_settings() and get_stat_categories() to avoid hitting
    /league/{key}/settings twice when both are needed (e.g. the projection page).

    Returns:
        settings:   {current_week, start_week, end_week}
        categories: same list as get_stat_categories()
    """
    data = _get(session, f"{BASE_URL}/league/{league_key}/settings")
    league = data["fantasy_content"]["league"]

    settings = {
        "current_week": int(league["current_week"]),
        "start_week": int(league["start_week"]),
        "end_week": int(league["end_week"]),
    }

    raw_stats = league["settings"]["stat_categories"]["stats"]["stat"]
    categories = []
    for stat in _as_list(raw_stats):
        pos_types = _as_list(stat["stat_position_types"]["stat_position_type"])
        is_display = any(
            p.get("is_only_display_stat", "0") == "1" for p in pos_types
        )
        categories.append({
            "stat_id": stat["stat_id"],
            "stat_name": stat["name"],
            "abbreviation": stat["display_name"],
            "stat_group": stat["group"],
            "is_enabled": not is_display,
        })

    return settings, categories


def get_teams(session, league_key: str) -> list[dict]:
    """Return a list of team dicts for the league."""
    data = _get(session, f"{BASE_URL}/league/{league_key}/teams")
    teams_data = data["fantasy_content"]["league"]["teams"]
    return [
        {
            "team_key": t["team_key"],
            "team_id": t["team_id"],
            "team_name": t["name"],
            "manager_name": t["managers"]["manager"]["nickname"],
        }
        for t in _as_list(teams_data["team"])
    ]


def get_all_teams_week_stats(
    session, league_key: str, week: int, stat_categories: list[dict]
) -> list[dict]:
    """
    Return stats for ALL teams in one API call using the teams collection.

    Endpoint: /league/{key}/teams/stats;type=week;week={w}
    This replaces N individual get_team_week_stats() calls with a single request.

    Returns a list of flat dicts (same shape as get_team_week_stats output):
        team_key, team_name, week, games_played, {stat_name...}
    """
    data = _get(
        session,
        f"{BASE_URL}/league/{league_key}/teams/stats;type=week;week={week}",
    )

    id_to_name = {
        cat["stat_id"]: cat["stat_name"]
        for cat in stat_categories
        if cat["is_enabled"]
    }

    teams_data = data["fantasy_content"]["league"]["teams"]
    rows = []
    for team in _as_list(teams_data["team"]):
        row: dict = {
            "team_key": team["team_key"],
            "team_name": team["name"],
            "week": week,
        }

        raw_stats = team["team_stats"]["stats"]["stat"]
        for stat in _as_list(raw_stats):
            stat_id = stat["stat_id"]
            value = stat["value"]

            if stat_id == "0":
                row["games_played"] = 0 if value in ("-", None) else int(value)
                continue

            if stat_id in id_to_name:
                row[id_to_name[stat_id]] = _coerce(value)

        rows.append(row)

    return rows


def get_team_week_stats(
    session, team_key: str, week: int, stat_categories: list[dict]
) -> dict:
    """
    Return a flat dict of stat values for one team for one week.

    Keys: team_key, week, games_played, then one key per enabled stat category.
    Stat values are floats; '-' (no activity) is coerced to 0.0.
    Stats not in the enabled categories list (display-only or unknown IDs) are
    silently ignored — this avoids the 'Unknown Stat ID: 22' columns the
    notebook produced.

    stat_id '0' is games played (not a scoring category).
    """
    data = _get(
        session, f"{BASE_URL}/team/{team_key}/stats;type=week;week={week}"
    )

    id_to_name = {
        cat["stat_id"]: cat["stat_name"]
        for cat in stat_categories
        if cat["is_enabled"]
    }

    row: dict = {"team_key": team_key, "week": week}

    raw_stats = data["fantasy_content"]["team"]["team_stats"]["stats"]["stat"]
    for stat in _as_list(raw_stats):
        stat_id = stat["stat_id"]
        value = stat["value"]

        if stat_id == "0":
            row["games_played"] = 0 if value in ("-", None) else int(value)
            continue

        if stat_id in id_to_name:
            row[id_to_name[stat_id]] = _coerce(value)

    return row
