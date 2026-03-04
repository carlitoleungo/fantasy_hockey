"""
Fetch the authenticated user's Yahoo Fantasy hockey games and leagues.

Used by app.py to populate the league selection dropdown. All results are
returned as plain Python lists of dicts — no Streamlit, no pandas, no cache.

The Yahoo endpoint returns all fantasy games the user participates in across
all sports. get_user_hockey_leagues() filters to NHL (code == "nhl") and
flattens across seasons so the caller gets a single ranked list.
"""

from __future__ import annotations

from data.client import BASE_URL, _as_list, _get


def get_games(session) -> list[dict]:
    """
    Return all Yahoo Fantasy games the current user is enrolled in.

    Each dict has: game_key, game_code, season.
    Results are sorted by season descending (most recent first).
    """
    data = _get(session, f"{BASE_URL}/users;use_login=1/games/teams")
    raw_games = data["fantasy_content"]["users"]["user"]["games"]["game"]
    games = [
        {
            "game_key": g["game_key"],
            "game_code": g["code"],
            "season": g["season"],
        }
        for g in _as_list(raw_games)
    ]
    return sorted(games, key=lambda g: g["season"], reverse=True)


def get_leagues(session, game_key: str) -> list[dict]:
    """
    Return all leagues the current user is enrolled in for a given game.

    Each dict has: league_key, league_id, league_name, scoring_type,
    start_week, start_date, end_date.
    """
    data = _get(
        session,
        f"{BASE_URL}/users;use_login=1/games;game_keys={game_key}/leagues",
    )
    leagues_data = (
        data["fantasy_content"]["users"]["user"]["games"]["game"]["leagues"]
    )
    return [
        {
            "league_key": league["league_key"],
            "league_id": league["league_id"],
            "league_name": league["name"],
            "scoring_type": league["scoring_type"],
            "start_week": league["start_week"],
            "start_date": league["start_date"],
            "end_date": league["end_date"],
        }
        for league in _as_list(leagues_data["league"])
    ]


def get_user_hockey_leagues(session) -> list[dict]:
    """
    Return all NHL fantasy leagues for the current user, most recent first.

    Calls get_games() filtered to NHL, then get_leagues() for each game key.
    Each returned dict has all fields from get_leagues() plus a 'season' key
    so the UI can show e.g. "2024 — My League".
    """
    games = get_games(session)
    nhl_games = [g for g in games if g["game_code"] == "nhl"]

    all_leagues = []
    for game in nhl_games:
        for league in get_leagues(session, game["game_key"]):
            all_leagues.append({**league, "season": game["season"]})
    return all_leagues
