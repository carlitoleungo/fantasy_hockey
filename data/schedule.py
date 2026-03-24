"""
Fetch remaining NHL games for a set of teams within a date range.

Uses the public NHL schedule API — no authentication required.
"""
from __future__ import annotations

from datetime import date, timedelta

import requests

NHL_SCHEDULE_BASE = "https://api-web.nhle.com/v1/schedule"

# Game states that mean the game is already finished — don't count these
_FINAL_STATES = frozenset({"FINAL", "OFF", "CRIT"})

# Only regular season (2) and playoff (3) games count; skip preseason (1)
_COUNTED_GAME_TYPES = frozenset({2, 3})

# Yahoo Fantasy uses 2-letter abbreviations for some teams; the NHL API uses 3-letter codes.
# Map Yahoo abbrs → NHL API abbrs before querying, then map results back.
_YAHOO_TO_NHL: dict[str, str] = {
    "LA": "LAK",   # Los Angeles Kings
    "NJ": "NJD",   # New Jersey Devils
    "SJ": "SJS",   # San Jose Sharks (historical; team is now Utah)
    "TB": "TBL",   # Tampa Bay Lightning
}


def _nhl_get(url: str) -> dict:
    """Plain HTTP GET — the NHL public API requires no auth."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def get_remaining_games(
    team_abbrs: list[str],
    from_date: date,
    to_date: date,
) -> dict[str, int]:
    """
    Count remaining NHL games for each team within [from_date, to_date].

    A game counts as "remaining" if:
    - Its date falls within the range (inclusive)
    - Its gameState is NOT in _FINAL_STATES (not yet finished)
    - It is a regular season or playoff game (not preseason)
    - LIVE games are counted (in progress, stats not yet final)

    The NHL schedule endpoint returns ~7 days from the requested date. If the
    date range spans more than 6 days, a second call is made starting 7 days
    after from_date to cover the full range.

    Args:
        team_abbrs: NHL team abbreviations to track (e.g. ["EDM", "BOS"])
        from_date:  First date to include, typically today
        to_date:    Last date to include, typically the fantasy week end date

    Returns:
        {team_abbr: count} — every input abbr is present; value is 0 if no games
    """
    # Normalise Yahoo 2-letter abbrs to NHL API 3-letter abbrs.
    # yahoo_to_nhl maps each input abbr to the abbr used in the API response.
    yahoo_to_nhl = {a: _YAHOO_TO_NHL.get(a, a) for a in team_abbrs}
    nhl_abbr_set = set(yahoo_to_nhl.values())
    nhl_counts: dict[str, int] = {nhl: 0 for nhl in nhl_abbr_set}

    fetch_dates = [from_date]
    if (to_date - from_date).days >= 7:
        fetch_dates.append(from_date + timedelta(days=7))

    seen_game_ids: set[int] = set()

    for fetch_date in fetch_dates:
        data = _nhl_get(f"{NHL_SCHEDULE_BASE}/{fetch_date.isoformat()}")
        for day in data.get("gameWeek", []):
            game_date_str = day.get("date", "")
            if not game_date_str:
                continue
            game_date = date.fromisoformat(game_date_str)
            if game_date < from_date or game_date > to_date:
                continue
            for game in day.get("games", []):
                game_id = game.get("id")
                if game_id is not None and game_id in seen_game_ids:
                    continue
                if game_id is not None:
                    seen_game_ids.add(game_id)
                if game.get("gameType") not in _COUNTED_GAME_TYPES:
                    continue
                if game.get("gameState") in _FINAL_STATES:
                    continue
                for side in ("awayTeam", "homeTeam"):
                    nhl_abbr = game.get(side, {}).get("abbrev", "")
                    if nhl_abbr in nhl_abbr_set:
                        nhl_counts[nhl_abbr] += 1

    # Return results keyed by the original input abbrs (Yahoo format).
    return {yahoo: nhl_counts[yahoo_to_nhl[yahoo]] for yahoo in team_abbrs}
