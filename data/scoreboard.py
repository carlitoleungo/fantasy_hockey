"""
Fetch the current week's matchup pairings and date range from the Yahoo scoreboard.
"""
from __future__ import annotations

from data.client import BASE_URL, _as_list, _get


def get_current_matchup(session, league_key: str, week: int) -> dict:
    """
    Fetch matchup pairings and week dates from the scoreboard endpoint.

    Returns:
        {
            "week_start": "2026-03-23",   # str, YYYY-MM-DD
            "week_end":   "2026-03-29",
            "matchups": [
                {"team_a_key": "nhl.l.99999.t.1", "team_b_key": "nhl.l.99999.t.4"},
                ...
            ]
        }

    Raises:
        ValueError: if the API response is missing week date fields.
    """
    url = f"{BASE_URL}/league/{league_key}/scoreboard;week={week}"
    data = _get(session, url)

    raw_matchups = (
        data.get("fantasy_content", {})
        .get("league", {})
        .get("scoreboard", {})
        .get("matchups", {})
    )

    matchup_list = _as_list(raw_matchups.get("matchup", []))

    if not matchup_list:
        raise ValueError(f"No matchups found for week {week}")

    first = matchup_list[0]
    week_start = first.get("week_start")
    week_end = first.get("week_end")

    if not week_start or not week_end:
        raise ValueError("Scoreboard response missing week_start/week_end")

    matchups = []
    for m in matchup_list:
        teams = _as_list(m.get("teams", {}).get("team", []))
        if len(teams) >= 2:
            matchups.append({
                "team_a_key": teams[0]["team_key"],
                "team_b_key": teams[1]["team_key"],
            })

    return {
        "week_start": week_start,
        "week_end": week_end,
        "matchups": matchups,
    }
