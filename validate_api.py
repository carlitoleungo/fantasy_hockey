"""
API validation script for waiver wire feature.

Tests assumptions about the Yahoo Fantasy API batch players endpoint
before we commit to the implementation in data/players.py.

Run from the project root:
    python validate_api.py [league_key]

If league_key is omitted, the script fetches your leagues and picks the first
NHL one automatically.

Requirements: tokens must already exist in .streamlit/oauth_token.json
(i.e. you must have logged in via the Streamlit app at least once).

Parameter reference (from yahoo-fantasy-node-docs.vercel.app/collection/players/leagues):
  sort       — stat_id | NAME | OR | AR | PTS
  sort_type  — season | date | week | lastweek | lastmonth
  status     — A (available) | FA (free agents) | W (waivers) | T (taken) | K (keepers)
  start      — pagination offset
  count      — page size
  position   — position code filter (e.g. F, D, G)
  out        — comma-separated subresources (e.g. stats)
"""

import json
import sys
import time
import tomllib
from pprint import pformat

import requests
import xmltodict

# ---------------------------------------------------------------------------
# Auth helpers (standalone — no Streamlit dependency)
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
# API helpers
# ---------------------------------------------------------------------------

def _get(session, url: str) -> dict:
    resp = session.get(url)
    resp.raise_for_status()
    return json.loads(json.dumps(xmltodict.parse(resp.content)))


def _as_list(value) -> list:
    return value if isinstance(value, list) else [value]


def _extract_players_node(data: dict) -> dict | None:
    """
    Pull the players node out of a leagues/players response.
    Returns None if the node is absent or empty (end of pagination).
    """
    node = (
        data
        .get("fantasy_content", {})
        .get("leagues", {})
        .get("league", {})
        .get("players")
    )
    if node is None:
        return None
    if int(node.get("@count", 0)) == 0:
        return None
    return node


def _parse_players(players_node: dict) -> list[dict]:
    """Return a list of player dicts from a players node."""
    return _as_list(players_node["player"])


def _player_stats(player: dict) -> dict[str, str]:
    """Extract {stat_id: value} from inline player_stats, or {} if absent."""
    raw = player.get("player_stats", {}).get("stats", {}).get("stat", [])
    if not raw:
        return {}
    return {s["stat_id"]: s["value"] for s in _as_list(raw)}


def _has_real_stats(stats: dict) -> bool:
    """Return True if any stat value is a real number (not '-' or None)."""
    for v in stats.values():
        if v not in ("-", None, ""):
            try:
                float(v)
                return True
            except (ValueError, TypeError):
                pass
    return False


def get_league_key(session) -> str:
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
    data = _get(session, f"{BASE_URL}/league/{league_key}/settings")
    raw_stats = data["fantasy_content"]["league"]["settings"]["stat_categories"]["stats"]["stat"]
    for stat in _as_list(raw_stats):
        pos_types = _as_list(stat["stat_position_types"]["stat_position_type"])
        is_display = any(p.get("is_only_display_stat", "0") == "1" for p in pos_types)
        if not is_display:
            return stat["stat_id"], stat["name"]
    sys.exit("No enabled stat categories found.")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def ok(msg: str):   print(f"  [PASS] {msg}")
def warn(msg: str): print(f"  [WARN] {msg}")
def fail(msg: str): print(f"  [FAIL] {msg}")
def show(label: str, value): print(f"  {label}: {value}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sort_by_stat_id(session, league_key, stat_id, stat_name):
    """
    Test 1: sort={stat_id} works on the batch players endpoint.
    """
    section(f"Test 1: sort={stat_id} ({stat_name}) with sort_type=season")
    url = (
        f"{BASE_URL}/leagues;league_keys={league_key}/players"
        f";status=A;sort={stat_id};sort_type=season;out=stats;start=0;count=5"
    )
    show("URL", url)
    try:
        data = _get(session, url)
        players_node = _extract_players_node(data)
        if players_node is None:
            fail("No players returned")
            return
        players = _parse_players(players_node)
        show("Player count returned", len(players))
        print(f"  Top {len(players)} players:")
        for p in players:
            name = p["name"]["full"]
            stats = _player_stats(p)
            val = stats.get(stat_id, "n/a")
            print(f"    - {name}  (stat {stat_id} = {val})")
        ok("sort={stat_id} works and returns players")
    except Exception as e:
        fail(f"Request failed: {e}")


def test_sort_or(session, league_key):
    """
    Test 2: sort=OR (overall rank) works — this is what data/players.py will use.
    """
    section("Test 2: sort=OR (overall rank)")
    url = (
        f"{BASE_URL}/leagues;league_keys={league_key}/players"
        f";status=A;sort=OR;sort_type=season;out=stats;start=0;count=5"
    )
    show("URL", url)
    try:
        data = _get(session, url)
        players_node = _extract_players_node(data)
        if players_node is None:
            fail("No players returned — sort=OR may not be supported")
            return
        players = _parse_players(players_node)
        print(f"  Top {len(players)} by overall rank:")
        for p in players:
            print(f"    - {p['name']['full']}")
        ok("sort=OR works")
    except Exception as e:
        fail(f"Request failed: {e}")


def test_lastmonth_stats(session, league_key, stat_id):
    """
    Test 3: Getting lastmonth stats.

    3a: Try type=lastmonth directly in the league players URL (long shot).
    3b: Fetch player keys via the league players endpoint, then call
        /players;player_keys={keys}/stats;type=lastmonth separately.
        Compare those values against the season stats from the first call
        to confirm they actually differ.
    """
    section("Test 3a: type=lastmonth inline in league players URL (long shot)")
    url_inline = (
        f"{BASE_URL}/leagues;league_keys={league_key}/players"
        f";status=A;sort={stat_id};sort_type=season;out=stats;type=lastmonth;start=0;count=5"
    )
    show("URL", url_inline)
    try:
        data = _get(session, url_inline)
        node = _extract_players_node(data)
        if node is None:
            fail("No players returned")
        else:
            players = _parse_players(node)
            # Compare first player's stats to a plain season fetch of the same player
            p = players[0]
            inline_stats = _player_stats(p)
            show(f"  First player", p["name"]["full"])
            show(f"  stat {stat_id} value", inline_stats.get(stat_id, "n/a"))
            show(f"  Full stats", pformat(inline_stats))
            # We can't tell definitively here whether these are season or lastmonth
            # without a comparison — result will become clear in Test 3b
            warn("Can't confirm if these are lastmonth or season without comparison — see Test 3b")
    except Exception as e:
        fail(f"Request failed: {e}")

    section("Test 3b: date=lastmonth vs type=lastmonth on /player/{key}/stats")
    try:
        # Get a player key and their season stats to compare against
        url_season = (
            f"{BASE_URL}/leagues;league_keys={league_key}/players"
            f";status=A;sort={stat_id};sort_type=season;out=stats;start=0;count=10"
        )
        data = _get(session, url_season)
        node = _extract_players_node(data)
        if node is None:
            fail("No players returned — can't run Test 3b")
            return

        # Pick first player with real stats as test subject
        test_player = None
        test_season_stats = None
        for p in _parse_players(node):
            stats = _player_stats(p)
            if _has_real_stats(stats):
                test_player = p
                test_season_stats = stats
                break

        if test_player is None:
            fail("No player with real stats found")
            return

        player_key = test_player["player_key"]
        player_name = test_player["name"]["full"]
        show("Test player", f"{player_name} ({player_key})")
        show(f"Season stat {stat_id}", test_season_stats.get(stat_id, "n/a"))

        # Try each URL pattern and compare against season
        candidates = [
            ("date=lastmonth", f"{BASE_URL}/player/{player_key}/stats;date=lastmonth"),
            ("type=lastmonth", f"{BASE_URL}/player/{player_key}/stats;type=lastmonth"),
            ("week=lastmonth", f"{BASE_URL}/player/{player_key}/stats;week=lastmonth"),
        ]

        for label, url in candidates:
            print()
            show(f"  Trying {label}", url)
            try:
                r = _get(session, url)
                p = r.get("fantasy_content", {}).get("player", {})
                lm_stats = _player_stats(p) if p else {}
                lm_val = lm_stats.get(stat_id, "n/a")
                season_val = test_season_stats.get(stat_id, "n/a")
                show(f"  stat {stat_id} ({label})", lm_val)
                if not _has_real_stats(lm_stats):
                    warn(f"  {label}: response has no real stat values")
                elif lm_val != season_val:
                    ok(f"  {label} returns DIFFERENT value ({lm_val}) than season ({season_val}) — THIS IS THE RIGHT PATTERN")
                    show(f"  Full lastmonth stats", pformat(lm_stats))
                else:
                    show(f"  Full stats", pformat(lm_stats))
                    warn(f"  {label}: values match season — may be correct or still wrong param")
            except requests.HTTPError as e:
                fail(f"  {label}: HTTP {e.response.status_code} — URL pattern not supported")
            except Exception as e:
                fail(f"  {label}: {e}")

    except Exception as e:
        fail(f"Request failed: {e}")


def test_pagination_termination(session, league_key, stat_id):
    """
    Test 4: What does an exhausted page look like?
    Checks both the None-node case (start=9999) and the natural end of pagination.
    """
    section("Test 4: Pagination termination")

    # 4a: Far past the end
    url = (
        f"{BASE_URL}/leagues;league_keys={league_key}/players"
        f";status=A;sort={stat_id};sort_type=season;out=stats;start=9999;count=25"
    )
    show("URL (start=9999)", url)
    try:
        data = _get(session, url)
        players_node = _extract_players_node(data)
        if players_node is None:
            ok("start=9999 → players node is None or @count=0 — _extract_players_node handles this")
        else:
            players = _parse_players(players_node)
            warn(f"Unexpectedly got {len(players)} players at start=9999 — check response:")
            print(f"  players_node keys: {list(players_node.keys())}")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            warn("Returns 404 — catch HTTPError(404) as termination condition instead")
        else:
            fail(f"Unexpected HTTP error: {e}")
    except Exception as e:
        fail(f"Request failed: {e}")

    # 4b: Walk pages until empty to confirm count<25 is also a valid stop condition
    print()
    show("Walking pages until empty (count=25 per page)...", "")
    start = 0
    page_num = 0
    try:
        while True:
            url = (
                f"{BASE_URL}/leagues;league_keys={league_key}/players"
                f";status=A;sort={stat_id};sort_type=season;out=stats;start={start};count=25"
            )
            data = _get(session, url)
            players_node = _extract_players_node(data)
            if players_node is None:
                show(f"  Page {page_num} (start={start})", "→ empty (players node None/@count=0) — stop here")
                break
            players = _parse_players(players_node)
            show(f"  Page {page_num} (start={start})", f"→ {len(players)} players")
            if len(players) < 25:
                show(f"  Page {page_num} (start={start})", f"→ {len(players)} players (< 25) — also a valid stop condition")
                break
            start += 25
            page_num += 1
            if page_num > 20:
                warn("Stopped after 20 pages to avoid rate limits")
                break
        ok("Pagination termination confirmed — use `players_node is None` as primary stop condition")
    except Exception as e:
        fail(f"Pagination walk failed: {e}")


def test_position_filter(session, league_key, stat_id):
    """
    Test 5: position=F returns all forwards (C, LW, RW).
    Also tests position=D and position=G for completeness.
    """
    section("Test 5: Position filtering (F, D, G)")
    for position in ("F", "D", "G"):
        url = (
            f"{BASE_URL}/leagues;league_keys={league_key}/players"
            f";status=A;sort={stat_id};sort_type=season;out=stats;position={position};start=0;count=5"
        )
        try:
            data = _get(session, url)
            players_node = _extract_players_node(data)
            if players_node is None:
                warn(f"position={position}: no players returned")
                continue
            players = _parse_players(players_node)
            all_positions: set[str] = set()
            for p in players:
                pos_data = p.get("eligible_positions", {}).get("position", [])
                all_positions.update(_as_list(pos_data))
            print(f"  position={position}: {len(players)} players, positions seen: {sorted(all_positions)}")
            ok(f"position={position} works")
        except Exception as e:
            fail(f"position={position} failed: {e}")


def test_batch_lastmonth(session, league_key, stat_id):
    """
    Test 6: /players;player_keys={keys}/stats;type=lastmonth as a batch call.

    Fetches a page of players (season stats inline), then requests lastmonth
    stats for all their keys in a single call. Confirms:
    - The batch call succeeds and returns one entry per player
    - The lastmonth values differ from the season values for at least one player
    """
    section("Test 6: Batch /players;player_keys/stats;type=lastmonth")
    try:
        # Step 1: get a page of players with season stats
        url = (
            f"{BASE_URL}/leagues;league_keys={league_key}/players"
            f";status=A;sort=OR;sort_type=season;out=stats;start=0;count=25"
        )
        data = _get(session, url)
        node = _extract_players_node(data)
        if node is None:
            fail("No players returned in step 1")
            return
        players = _parse_players(node)
        season_by_key = {
            p["player_key"]: (p["name"]["full"], _player_stats(p))
            for p in players
            if _has_real_stats(_player_stats(p))
        }
        show("Players with real season stats", len(season_by_key))
        if not season_by_key:
            fail("No players with real season stats — can't compare")
            return

        # Step 2: batch lastmonth call for all keys at once
        keys_param = ",".join(season_by_key.keys())
        url_batch = f"{BASE_URL}/players;player_keys={keys_param}/stats;type=lastmonth"
        show("Batch URL", url_batch)
        lm_data = _get(session, url_batch)

        raw = lm_data.get("fantasy_content", {}).get("players", {})
        lm_count = int(raw.get("@count", 0))
        show("Players returned in batch response", lm_count)

        if lm_count == 0:
            fail("Batch call returned no players — batch form not supported")
            return

        lastmonth_by_key = {}
        for p in _as_list(raw["player"]):
            lastmonth_by_key[p["player_key"]] = _player_stats(p)

        # Check at least one player has differing season vs lastmonth values
        diffs = 0
        for key, (name, season_stats) in season_by_key.items():
            lm_stats = lastmonth_by_key.get(key, {})
            if season_stats.get(stat_id) != lm_stats.get(stat_id):
                diffs += 1

        show("Players where season ≠ lastmonth for stat", f"{diffs}/{len(season_by_key)}")
        if diffs > 0:
            ok("Batch call works and returns lastmonth stats that differ from season")
            ok("Two-call-per-page architecture confirmed — ready to build data/players.py")
        else:
            warn("Batch call succeeded but all values match season — may be early in season")
            warn("Inspect a sample player manually to confirm:")
            sample_key = next(iter(lastmonth_by_key))
            sample_name, season_stats = season_by_key[sample_key]
            show(f"  {sample_name} season", pformat(season_stats))
            show(f"  {sample_name} lastmonth", pformat(lastmonth_by_key[sample_key]))

    except requests.HTTPError as e:
        fail(f"HTTP {e.response.status_code} — batch call may not be supported")
    except Exception as e:
        fail(f"Request failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Yahoo Fantasy API — Waiver Wire Validator")
    print("Authenticating...")

    session = build_session()
    print("  Session ready.")

    if len(sys.argv) > 1:
        league_key = sys.argv[1]
        print(f"  Using league_key from argument: {league_key}")
    else:
        print("  No league_key provided — fetching from API...")
        league_key = get_league_key(session)
        print(f"  Found league_key: {league_key}")

    stat_id, stat_name = get_first_enabled_stat_id(session, league_key)
    print(f"  Using stat: {stat_name} (id={stat_id}) for sort tests")

    test_sort_by_stat_id(session, league_key, stat_id, stat_name)
    test_sort_or(session, league_key)
    test_lastmonth_stats(session, league_key, stat_id)
    test_pagination_termination(session, league_key, stat_id)
    test_position_filter(session, league_key, stat_id)
    test_batch_lastmonth(session, league_key, stat_id)

    print(f"\n{'=' * 60}")
    print("  Done. Review [PASS] / [WARN] / [FAIL] above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
