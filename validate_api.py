"""
API validation script for waiver wire feature.

Tests five assumptions about the Yahoo Fantasy API batch players endpoint
before we commit to the implementation in data/players.py.

Run from the project root:
    python validate_api.py [league_key]

If league_key is omitted, the script fetches your leagues and picks the first
NHL one automatically.

Requirements: tokens must already exist in .streamlit/oauth_token.json
(i.e. you must have logged in via the Streamlit app at least once).
"""

import json
import sys
import time
import tomllib
from pprint import pformat

import requests
import xmltodict

# ---------------------------------------------------------------------------
# Auth helpers (standalone versions of auth/oauth.py, no Streamlit dependency)
# ---------------------------------------------------------------------------

TOKEN_FILE = ".streamlit/oauth_token.json"
SECRETS_FILE = ".streamlit/secrets.toml"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"


def _load_tokens() -> dict:
    try:
        with open(TOKEN_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(
            f"No token file found at {TOKEN_FILE}. "
            "Log in via the Streamlit app first (streamlit run app.py)."
        )


def _load_secrets() -> dict:
    try:
        with open(SECRETS_FILE, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        sys.exit(f"No secrets file found at {SECRETS_FILE}.")


def _refresh_tokens(tokens: dict, secrets: dict) -> dict:
    print("  Access token expired — refreshing...")
    resp = requests.post(
        YAHOO_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "redirect_uri": secrets["yahoo"].get("redirect_uri", "https://localhost:8501"),
        },
        auth=(secrets["yahoo"]["client_id"], secrets["yahoo"]["client_secret"]),
    )
    resp.raise_for_status()
    new_tokens = resp.json()
    new_tokens["expires_at"] = time.time() + int(new_tokens.get("expires_in", 3600))
    with open(TOKEN_FILE, "w") as f:
        json.dump(new_tokens, f)
    return new_tokens


def build_session() -> requests.Session:
    tokens = _load_tokens()
    if time.time() >= tokens.get("expires_at", 0) - 60:
        secrets = _load_secrets()
        tokens = _refresh_tokens(tokens, secrets)
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return session


# ---------------------------------------------------------------------------
# API helpers (mirrors data/client.py)
# ---------------------------------------------------------------------------

def _get(session, url: str) -> dict:
    resp = session.get(url)
    resp.raise_for_status()
    return json.loads(json.dumps(xmltodict.parse(resp.content)))


def _as_list(value) -> list:
    return value if isinstance(value, list) else [value]


def get_league_key(session) -> str:
    """Fetch the first available NHL league key for the authenticated user."""
    data = _get(session, f"{BASE_URL}/users;use_login=1/games;game_codes=nhl/leagues")
    games = data["fantasy_content"]["users"]["user"]["games"]["game"]
    for game in _as_list(games):
        leagues = game.get("leagues")
        if not leagues:
            continue
        for league in _as_list(leagues["league"]):
            return league["league_key"]
    sys.exit("No NHL leagues found for this account.")


def get_first_enabled_stat_id(session, league_key: str) -> tuple[str, str]:
    """Return (stat_id, stat_name) for the first enabled scoring stat."""
    data = _get(session, f"{BASE_URL}/league/{league_key}/settings")
    raw_stats = data["fantasy_content"]["league"]["settings"]["stat_categories"]["stats"]["stat"]
    for stat in _as_list(raw_stats):
        pos_types = _as_list(stat["stat_position_types"]["stat_position_type"])
        is_display = any(p.get("is_only_display_stat", "0") == "1" for p in pos_types)
        if not is_display:
            return stat["stat_id"], stat["name"]
    sys.exit("No enabled stat categories found.")


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def ok(msg: str):
    print(f"  [PASS] {msg}")


def warn(msg: str):
    print(f"  [WARN] {msg}")


def fail(msg: str):
    print(f"  [FAIL] {msg}")


def show(label: str, value):
    print(f"  {label}: {value}")


# ---------------------------------------------------------------------------
# The five tests
# ---------------------------------------------------------------------------

def test_sort_by_stat_id(session, league_key, stat_id, stat_name):
    """
    Assumption 1: sort={stat_id} works on the batch players endpoint.
    Fetch top 3 players sorted by the given stat_id and show the result.
    """
    section(f"Test 1: sort={stat_id} ({stat_name}) on batch players endpoint")
    url = (
        f"{BASE_URL}/leagues;league_keys={league_key}/players"
        f";status=A;sort={stat_id};sort_type=season;out=stats;start=0;count=3"
    )
    show("URL", url)
    try:
        data = _get(session, url)
        players_node = data["fantasy_content"]["leagues"]["league"]["players"]
        count = int(players_node.get("@count", 0))
        show("Player count returned", count)
        if count == 0:
            fail("No players returned — sort by stat_id may not be supported")
            return None
        players = _as_list(players_node["player"])
        print(f"  Top {len(players)} players:")
        for p in players:
            name = p["name"]["full"]
            print(f"    - {name}")
        ok("sort={stat_id} works and returns players")
        return data
    except Exception as e:
        fail(f"Request failed: {e}")
        return None


def test_sort_type_lastmonth(session, league_key, stat_id, stat_name):
    """
    Assumption 2: sort_type=lastmonth works on the batch players endpoint.
    Compare the top 3 players with sort_type=season vs sort_type=lastmonth.
    Different order → lastmonth sorting is working.
    """
    section(f"Test 2: sort_type=lastmonth on batch players endpoint")

    def fetch_top3(sort_type):
        url = (
            f"{BASE_URL}/leagues;league_keys={league_key}/players"
            f";status=A;sort={stat_id};sort_type={sort_type};out=stats;start=0;count=3"
        )
        data = _get(session, url)
        players_node = data["fantasy_content"]["leagues"]["league"]["players"]
        players = _as_list(players_node["player"])
        return [p["name"]["full"] for p in players]

    try:
        season_names = fetch_top3("season")
        lastmonth_names = fetch_top3("lastmonth")
        show("Top 3 by season", season_names)
        show("Top 3 by lastmonth", lastmonth_names)
        if season_names != lastmonth_names:
            ok("sort_type=lastmonth returns a different order than season — param is working")
        else:
            warn("Same order for season and lastmonth — sorting may not differ (or few available players)")
    except Exception as e:
        fail(f"Request failed: {e}")


def test_out_stats_reflects_sort_type(session, league_key, stat_id, stat_name):
    """
    Assumption 3: out=stats returns stats matching the active sort_type.
    Fetch the same player with season and lastmonth, compare the stat values.
    If they differ → the stats in the response match the sort_type.
    If identical → out=stats always returns season stats regardless.
    """
    section("Test 3: out=stats reflects sort_type (season vs lastmonth)")

    def fetch_first_player_stats(sort_type):
        url = (
            f"{BASE_URL}/leagues;league_keys={league_key}/players"
            f";status=A;sort={stat_id};sort_type={sort_type};out=stats;start=0;count=1"
        )
        data = _get(session, url)
        player = _as_list(
            data["fantasy_content"]["leagues"]["league"]["players"]["player"]
        )[0]
        name = player["name"]["full"]
        raw_stats = player.get("player_stats", {}).get("stats", {}).get("stat", [])
        stats = {s["stat_id"]: s["value"] for s in _as_list(raw_stats)} if raw_stats else {}
        return name, stats

    try:
        season_name, season_stats = fetch_first_player_stats("season")
        lastmonth_name, lastmonth_stats = fetch_first_player_stats("lastmonth")

        show("Player (season fetch)", season_name)
        show("Player (lastmonth fetch)", lastmonth_name)

        # Find the sorted stat_id's value in each response
        season_val = season_stats.get(stat_id, "not found")
        lastmonth_val = lastmonth_stats.get(stat_id, "not found")

        show(f"  stat {stat_id} value in season response", season_val)
        show(f"  stat {stat_id} value in lastmonth response", lastmonth_val)

        if season_val != lastmonth_val:
            ok("Stat values differ between sort_type=season and sort_type=lastmonth")
            ok("out=stats DOES return stats matching the active sort_type")
        else:
            warn("Stat values are identical — out=stats may always return season stats")
            warn("Check the full stat dicts below to confirm:")
            print(f"  season stats:    {pformat(season_stats)}")
            print(f"  lastmonth stats: {pformat(lastmonth_stats)}")
    except Exception as e:
        fail(f"Request failed: {e}")


def test_pagination_termination(session, league_key, stat_id):
    """
    Assumption 4: What does an exhausted page look like?
    Fetch a page starting far past the end of available players.
    We want to know if we get: empty player list, @count=0, error, or something else.
    """
    section("Test 4: Pagination termination — what happens past the end?")
    url = (
        f"{BASE_URL}/leagues;league_keys={league_key}/players"
        f";status=A;sort={stat_id};sort_type=lastmonth;out=stats;start=9999;count=25"
    )
    show("URL (start=9999)", url)
    try:
        data = _get(session, url)
        players_node = data["fantasy_content"]["leagues"]["league"]["players"]
        count = int(players_node.get("@count", -1))
        show("@count in response", count)

        if count == 0:
            ok("Empty page returns @count=0 with no player key — use `count == 0` as loop termination")
        elif "player" not in players_node:
            ok("Empty page has no 'player' key — use `'player' not in players_node` as loop termination")
        else:
            warn("Unexpected response structure — inspect below:")
            print(f"  players_node keys: {list(players_node.keys())}")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            warn("Returns 404 on exhausted page — catch HTTPError with 404 as termination condition")
        else:
            fail(f"Unexpected HTTP error: {e}")
    except Exception as e:
        fail(f"Request failed: {e}")


def test_position_filter(session, league_key, stat_id):
    """
    Assumption 5: Does position=F return all forwards (C+LW+RW)?
    Fetch top 5 with position=F and show their eligible positions.
    """
    section("Test 5: position=F — does it include C, LW, RW?")
    url = (
        f"{BASE_URL}/leagues;league_keys={league_key}/players"
        f";status=A;sort={stat_id};sort_type=lastmonth;out=stats;position=F;start=0;count=5"
    )
    show("URL", url)
    try:
        data = _get(session, url)
        players_node = data["fantasy_content"]["leagues"]["league"]["players"]
        count = int(players_node.get("@count", 0))
        show("Player count returned", count)
        if count == 0:
            fail("No players returned — position=F may not be valid; try position=C")
            return

        players = _as_list(players_node["player"])
        print(f"  Top {len(players)} players and their eligible positions:")
        for p in players:
            name = p["name"]["full"]
            pos_data = p.get("eligible_positions", {}).get("position", [])
            positions = _as_list(pos_data)
            print(f"    - {name}: {positions}")

        all_positions = set()
        for p in players:
            pos_data = p.get("eligible_positions", {}).get("position", [])
            all_positions.update(_as_list(pos_data))

        if {"C", "LW", "RW"} & all_positions:
            ok(f"position=F returns forwards — positions seen: {sorted(all_positions)}")
        else:
            warn(f"Unexpected positions: {sorted(all_positions)} — may need separate C/LW/RW calls")
    except Exception as e:
        fail(f"Request failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Yahoo Fantasy API — Waiver Wire Assumption Validator")
    print("Authenticating...")

    session = build_session()
    print("  Session ready.")

    # Get or accept league_key
    if len(sys.argv) > 1:
        league_key = sys.argv[1]
        print(f"  Using league_key from argument: {league_key}")
    else:
        print("  No league_key provided — fetching from API...")
        league_key = get_league_key(session)
        print(f"  Found league_key: {league_key}")

    # Get a real stat_id to use in tests
    stat_id, stat_name = get_first_enabled_stat_id(session, league_key)
    print(f"  Using stat: {stat_name} (id={stat_id}) for sort tests")

    # Run tests
    test_sort_by_stat_id(session, league_key, stat_id, stat_name)
    test_sort_type_lastmonth(session, league_key, stat_id, stat_name)
    test_out_stats_reflects_sort_type(session, league_key, stat_id, stat_name)
    test_pagination_termination(session, league_key, stat_id)
    test_position_filter(session, league_key, stat_id)

    print(f"\n{'=' * 60}")
    print("  Done. Review [PASS] / [WARN] / [FAIL] above.")
    print('=' * 60)


if __name__ == "__main__":
    main()
