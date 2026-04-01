#!/usr/bin/env python3
"""
Generate demo projection data files.

Run once from the project root:

    python scripts/extend_demo_data.py

Writes two files to demo/data/:
    projection_context.json   — teams, scoreboard, stat_categories, live_stats_rows
    projection_pair_data.json — rosters, lastmonth_stats (derived), games_remaining

Requires Yahoo OAuth credentials in .streamlit/secrets.toml:
    [yahoo]
    client_id     = "..."
    client_secret = "..."
    redirect_uri  = "https://localhost:8501"  # or whatever is registered

On first run, prints an authorization URL and prompts for the redirect URL.
The token is cached to .streamlit/script_token.json for subsequent runs.
"""

from __future__ import annotations

import json
import sys
import time
import tomllib
import urllib.parse
import webbrowser
from datetime import date, timedelta
from pathlib import Path

import requests

# Ensure project root is on sys.path so we can import project modules
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from data import roster as roster_module
from data.client import BASE_URL, _as_list, _coerce, _get
from data.schedule import _YAHOO_TO_NHL, _nhl_get, _COUNTED_GAME_TYPES

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DEMO_DATA = _ROOT / "demo" / "data"
_SECRETS_FILE = _ROOT / ".streamlit" / "secrets.toml"
_TOKEN_FILE = _ROOT / ".streamlit" / "script_token.json"

YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
TOKEN_EXPIRY_BUFFER = 60


# ---------------------------------------------------------------------------
# Standalone OAuth helpers (no Streamlit dependency)
# ---------------------------------------------------------------------------

def _load_secrets() -> dict:
    if not _SECRETS_FILE.exists():
        sys.exit(
            f"ERROR: {_SECRETS_FILE} not found.\n"
            "Add your Yahoo OAuth credentials there before running this script."
        )
    with open(_SECRETS_FILE, "rb") as f:
        return tomllib.load(f)


def _load_token() -> dict | None:
    if not _TOKEN_FILE.exists():
        return None
    try:
        with open(_TOKEN_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_token(tokens: dict) -> None:
    _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_TOKEN_FILE, "w") as f:
        json.dump(tokens, f)


def _stamp_expiry(tokens: dict) -> dict:
    tokens["expires_at"] = time.time() + int(tokens.get("expires_in", 3600))
    return tokens


def _is_valid(tokens: dict) -> bool:
    return time.time() < tokens.get("expires_at", 0) - TOKEN_EXPIRY_BUFFER


def _refresh(tokens: dict, secrets: dict) -> dict | None:
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return None
    try:
        resp = requests.post(
            YAHOO_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "redirect_uri": secrets["yahoo"].get("redirect_uri", "https://localhost:8501"),
            },
            auth=(secrets["yahoo"]["client_id"], secrets["yahoo"]["client_secret"]),
        )
        resp.raise_for_status()
        return _stamp_expiry(resp.json())
    except requests.HTTPError as e:
        print(f"Token refresh failed: {e}")
        return None


def _do_auth_flow(secrets: dict) -> dict:
    """Interactive OAuth flow: print URL → user pastes redirect → exchange code."""
    client_id = secrets["yahoo"]["client_id"]
    redirect_uri = secrets["yahoo"].get("redirect_uri", "https://localhost:8501")

    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    })
    auth_url = f"{YAHOO_AUTH_URL}?{params}"

    print("\n--- Yahoo OAuth ---")
    print("Opening auth URL in your browser (or paste it manually):")
    print(f"\n  {auth_url}\n")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    redirect_response = input(
        "After authorizing, paste the full redirect URL here:\n> "
    ).strip()

    # Extract `code` from the redirect URL
    parsed = urllib.parse.urlparse(redirect_response)
    qs = urllib.parse.parse_qs(parsed.query)
    code = qs.get("code", [None])[0]
    if not code:
        # Maybe the user pasted just the code value, not the full URL
        code = redirect_response

    resp = requests.post(
        YAHOO_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        auth=(client_id, secrets["yahoo"]["client_secret"]),
    )
    resp.raise_for_status()
    return _stamp_expiry(resp.json())


def get_session() -> requests.Session:
    """Return an authenticated requests.Session, running OAuth flow if needed."""
    secrets = _load_secrets()
    tokens = _load_token()

    if tokens and _is_valid(tokens):
        pass  # use as-is
    elif tokens:
        print("Token expired — attempting refresh...")
        tokens = _refresh(tokens, secrets)
        if tokens is None:
            print("Refresh failed — starting new auth flow.")
            tokens = None

    if tokens is None:
        tokens = _do_auth_flow(secrets)

    _save_token(tokens)

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return session


# ---------------------------------------------------------------------------
# Season stats batch fetch (for rostered players)
# ---------------------------------------------------------------------------

def _fetch_season_stats_for_keys(
    session,
    player_keys: list[str],
    id_to_name: dict[str, str],
) -> dict[str, dict]:
    """
    Fetch season stats + games_played for a list of player keys.

    Uses /players;player_keys={keys}/stats;type=season in batches of 25.
    Returns {player_key: {stat_name: float, ..., games_played: int}}.
    GAA (stat_id 23) is recomputed from raw GA / GP for consistency with
    how data/players.py handles the lastmonth endpoint.
    """
    result: dict[str, dict] = {}
    chunk_size = 25

    for i in range(0, len(player_keys), chunk_size):
        chunk = player_keys[i : i + chunk_size]
        keys_param = ",".join(chunk)
        url = f"{BASE_URL}/players;player_keys={keys_param}/stats;type=season"
        data = _get(session, url)

        raw = data.get("fantasy_content", {}).get("players", {})
        if not raw or int(raw.get("@count", 0)) == 0:
            continue

        for p in _as_list(raw["player"]):
            pk = p["player_key"]
            stats: dict = {}
            ga_raw: float | None = None

            raw_stats = (
                p.get("player_stats", {})
                .get("stats", {})
                .get("stat")
            )
            if not raw_stats:
                result[pk] = stats
                continue

            for s in _as_list(raw_stats):
                sid = s["stat_id"]
                val = s["value"]
                if sid == "0":
                    stats["games_played"] = 0 if val in ("-", None) else int(val)
                elif sid in id_to_name:
                    stats[id_to_name[sid]] = _coerce(val)
                if sid == "22":
                    ga_raw = _coerce(val)

            # Recompute GAA from raw GA / GP so the per-game rate is correct
            if "23" in id_to_name and ga_raw is not None:
                gp = stats.get("games_played", 0)
                stats[id_to_name["23"]] = ga_raw / gp if gp > 0 else 0.0

            result[pk] = stats

    return result


# ---------------------------------------------------------------------------
# Historical games-remaining helper
# ---------------------------------------------------------------------------

def _compute_historical_games_remaining(
    team_abbrs: list[str],
    week_start: date,
    week_end: date,
    cutoff: date,
) -> dict[str, int]:
    """
    For a past week, compute how many games each team had remaining as of `cutoff`.

    Unlike schedule.get_remaining_games() (which skips FINAL games and therefore
    returns 0 for any past week), this function counts ALL games in [cutoff, week_end]
    from the historical NHL schedule, regardless of game state.

    NHL schedule API returns ~7 days starting from the requested date; two calls
    cover the full week.
    """
    yahoo_to_nhl = {a: _YAHOO_TO_NHL.get(a, a) for a in team_abbrs}
    nhl_abbr_set = set(yahoo_to_nhl.values())
    nhl_counts: dict[str, int] = {nhl: 0 for nhl in nhl_abbr_set}
    seen_game_ids: set[int] = set()

    fetch_dates = [week_start]
    if (week_end - week_start).days >= 7:
        fetch_dates.append(week_start + timedelta(days=7))

    for fetch_date in fetch_dates:
        data = _nhl_get(f"https://api-web.nhle.com/v1/schedule/{fetch_date.isoformat()}")
        for day in data.get("gameWeek", []):
            game_date_str = day.get("date", "")
            if not game_date_str:
                continue
            game_date = date.fromisoformat(game_date_str)
            # Only count games from cutoff through end of week
            if game_date < cutoff or game_date > week_end:
                continue
            for game in day.get("games", []):
                game_id = game.get("id")
                if game_id is not None and game_id in seen_game_ids:
                    continue
                if game_id is not None:
                    seen_game_ids.add(game_id)
                if game.get("gameType") not in _COUNTED_GAME_TYPES:
                    continue
                # Count ALL games regardless of state (FINAL, LIVE, etc.)
                for side in ("awayTeam", "homeTeam"):
                    nhl_abbr = game.get(side, {}).get("abbrev", "")
                    if nhl_abbr in nhl_abbr_set:
                        nhl_counts[nhl_abbr] += 1

    return {yahoo: nhl_counts[yahoo_to_nhl[yahoo]] for yahoo in team_abbrs}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # ── Load existing demo metadata ──────────────────────────────────────────
    meta_path = _DEMO_DATA / "league_meta.json"
    with open(meta_path) as f:
        meta = json.load(f)

    real_league_key = meta["league_key"]   # e.g. "465.l.8977"
    snapshot_week = int(meta["snapshot_week"])  # 14

    stat_cats_path = _DEMO_DATA / "stat_categories.json"
    with open(stat_cats_path) as f:
        stat_categories = json.load(f)

    id_to_name: dict[str, str] = {
        c["stat_id"]: c["stat_name"]
        for c in stat_categories
        if c["is_enabled"]
    }
    enabled_stats = [c["stat_name"] for c in stat_categories if c["is_enabled"]]

    # ── Authenticate ─────────────────────────────────────────────────────────
    print(f"Authenticating with Yahoo (league {real_league_key}, week {snapshot_week})...")
    session = get_session()
    print("Authenticated.\n")

    # ── Fetch week 14 scoreboard → dates + matchup pairs ────────────────────
    from data import scoreboard as scoreboard_module  # local import to avoid top-level st dependency
    print(f"Fetching week {snapshot_week} scoreboard...")
    sb = scoreboard_module.get_current_matchup(session, real_league_key, snapshot_week)
    week_start = sb["week_start"]
    week_end = sb["week_end"]
    print(f"  Week {snapshot_week}: {week_start} – {week_end}")
    print(f"  Matchups: {sb['matchups']}")

    # Pick the matchup containing MY_TEAM_KEY as the demo pair.
    # my_team is listed first so the demo dropdown defaults to them.
    MY_TEAM_KEY = f"{real_league_key}.t.8"   # AHO-V-O Crew
    if not sb["matchups"]:
        sys.exit("ERROR: No matchups found for the snapshot week.")

    demo_matchup = None
    for m in sb["matchups"]:
        if MY_TEAM_KEY in (m["team_a_key"], m["team_b_key"]):
            demo_matchup = m
            break
    if demo_matchup is None:
        sys.exit(f"ERROR: No matchup found for team {MY_TEAM_KEY} in week {snapshot_week}.")

    # Ensure MY_TEAM_KEY is listed as team_a (dropdown default)
    if demo_matchup["team_b_key"] == MY_TEAM_KEY:
        demo_matchup = {"team_a_key": MY_TEAM_KEY, "team_b_key": demo_matchup["team_a_key"]}

    my_team_key = demo_matchup["team_a_key"]
    opp_team_key = demo_matchup["team_b_key"]
    print(f"\nDemo pair: {my_team_key} vs {opp_team_key}")

    # ── Fetch rosters ─────────────────────────────────────────────────────────
    print(f"\nFetching rosters for week {snapshot_week}...")
    my_roster = roster_module.get_team_roster(session, my_team_key, week=snapshot_week)
    opp_roster = roster_module.get_team_roster(session, opp_team_key, week=snapshot_week)
    print(f"  {my_team_key}: {len(my_roster)} players")
    print(f"  {opp_team_key}: {len(opp_roster)} players")

    # ── Fetch season stats → derive lastmonth proxy ───────────────────────────
    all_player_keys = [p["player_key"] for p in my_roster + opp_roster]
    print(f"\nFetching season stats for {len(all_player_keys)} rostered players...")
    season_stats = _fetch_season_stats_for_keys(session, all_player_keys, id_to_name)

    # lastmonth_stats stores season totals + season GP.
    # The projection formula computes per_game = stat / games_played, so using
    # season totals / season GP gives the same per-game rate as the actual season.
    lastmonth_stats = season_stats
    print(f"  Got stats for {len(lastmonth_stats)} players.")

    # ── Fetch team names for the demo pair ────────────────────────────────────
    from data.client import get_teams
    print("\nFetching team names...")
    all_teams = get_teams(session, real_league_key)
    team_name_by_key = {t["team_key"]: t["team_name"] for t in all_teams}
    my_team_name = team_name_by_key.get(my_team_key, my_team_key)
    opp_team_name = team_name_by_key.get(opp_team_key, opp_team_key)
    print(f"  {my_team_name} vs {opp_team_name}")

    # ── Compute games remaining as of Wednesday of the demo week ─────────────
    # We can't use schedule.get_remaining_games() for a past week because the
    # NHL API marks all past games as FINAL and the function skips those.
    # Instead, fetch the full historical schedule and count games from Wed onward.
    week_start_dt = date.fromisoformat(week_start)
    week_end_dt = date.fromisoformat(week_end)
    wednesday = week_start_dt + timedelta(days=2)  # Mon + 2 → Wednesday
    print(f"\nFetching NHL schedule (historical games remaining from {wednesday} to {week_end_dt})...")
    all_abbrs = list({p["team_abbr"] for p in my_roster + opp_roster if p["team_abbr"]})
    games_remaining = _compute_historical_games_remaining(
        all_abbrs, week_start_dt, week_end_dt, cutoff=wednesday
    )
    print(f"  games_remaining: {games_remaining}")

    # ── Build live_stats_rows (all zeros — "start of week" snapshot) ──────────
    live_stats_rows = [
        {"team_key": my_team_key, "team_name": my_team_name,
         "week": snapshot_week, "games_played": 0,
         **{s: 0.0 for s in enabled_stats}},
        {"team_key": opp_team_key, "team_name": opp_team_name,
         "week": snapshot_week, "games_played": 0,
         **{s: 0.0 for s in enabled_stats}},
    ]

    # ── Assemble and write projection_context.json ────────────────────────────
    context = {
        "current_week": snapshot_week,
        "stat_categories": stat_categories,
        "teams": [
            {"team_key": my_team_key, "team_name": my_team_name},
            {"team_key": opp_team_key, "team_name": opp_team_name},
        ],
        "live_stats_rows": live_stats_rows,
        "scoreboard": {
            "week_start": week_start,
            "week_end": week_end,
            "matchups": [
                {"team_a_key": my_team_key, "team_b_key": opp_team_key}
            ],
        },
    }

    ctx_path = _DEMO_DATA / "projection_context.json"
    with open(ctx_path, "w") as f:
        json.dump(context, f, indent=2)
    print(f"\nWrote {ctx_path}")

    # ── Assemble and write projection_pair_data.json ──────────────────────────
    pair_data = {
        "my_team_key": my_team_key,
        "opp_team_key": opp_team_key,
        "my_roster": my_roster,
        "opp_roster": opp_roster,
        "lastmonth_stats": lastmonth_stats,
        "games_remaining": games_remaining,
    }

    pair_path = _DEMO_DATA / "projection_pair_data.json"
    with open(pair_path, "w") as f:
        json.dump(pair_data, f, indent=2)
    print(f"Wrote {pair_path}")

    print("\nDone. Commit both files to the repo:")
    print(f"  git add {ctx_path.relative_to(_ROOT)} {pair_path.relative_to(_ROOT)}")


if __name__ == "__main__":
    main()
