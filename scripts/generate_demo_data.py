"""
Generate static demo data for demo mode.

Run once offline when you want to refresh the demo snapshot:

    python scripts/generate_demo_data.py

Outputs to demo/data/ (committed to the repo as static assets).

Auth: reads Yahoo credentials and redirect_uri from .streamlit/secrets.toml
and caches tokens in .streamlit/demo_token.json so you only need to authorise
once. Subsequent runs refresh the token automatically.

On first run, Yahoo will redirect your browser to the registered redirect_uri
(e.g. https://localhost:8501) — the connection will fail because no server is
running there, but the code= parameter is visible in the address bar. Paste
the full redirect URL back into the terminal when prompted.
"""

from __future__ import annotations

import json
import sys
import time
import tomllib
import urllib.parse
import webbrowser
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration — edit these before running
# ---------------------------------------------------------------------------

TARGET_LEAGUE_KEY = "465.l.8977"
SNAPSHOT_WEEK = 14                  # week number to use as the demo "current week"
OUTPUT_DIR = Path("demo/data")

# ---------------------------------------------------------------------------
# Auth helpers — standalone, no Streamlit dependency
# ---------------------------------------------------------------------------

_SECRETS_FILE = Path(".streamlit/secrets.toml")
_TOKEN_FILE = Path(".streamlit/demo_token.json")
_YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
_YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"


def _load_secrets() -> dict:
    if not _SECRETS_FILE.exists():
        sys.exit(f"Error: {_SECRETS_FILE} not found. Copy secrets.toml.example and fill in credentials.")
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
        json.dump(tokens, f, indent=2)


def _stamp_expiry(tokens: dict) -> dict:
    tokens["expires_at"] = time.time() + int(tokens.get("expires_in", 3600))
    return tokens


def _is_valid(tokens: dict) -> bool:
    return time.time() < tokens.get("expires_at", 0) - 60


def _refresh_token(tokens: dict, client_id: str, client_secret: str) -> dict | None:
    resp = requests.post(
        _YAHOO_TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]},
        auth=(client_id, client_secret),
    )
    if not resp.ok:
        return None
    new_tokens = _stamp_expiry(resp.json())
    # Yahoo doesn't always return a new refresh_token; keep the old one if missing
    if "refresh_token" not in new_tokens:
        new_tokens["refresh_token"] = tokens["refresh_token"]
    return new_tokens


def _authorize(client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """
    Open browser for Yahoo OAuth, then prompt the user to paste the redirect URL.

    Yahoo redirects to the registered redirect_uri (e.g. https://localhost:8501).
    The connection will fail — no server is running there — but the code= param
    is visible in the browser address bar. Paste the full URL here.
    """
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    })
    auth_url = f"{_YAHOO_AUTH_URL}?{params}"
    print(f"\nOpening browser for Yahoo login...")
    print(f"If it doesn't open automatically, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print(
        "After logging in, Yahoo will redirect to your registered redirect URI.\n"
        "The page will fail to load — that's expected.\n"
        "Copy the full URL from your browser's address bar and paste it here."
    )
    raw = input("Paste redirect URL: ").strip()

    parsed = urllib.parse.urlparse(raw)
    params_back = dict(urllib.parse.parse_qsl(parsed.query))
    code = params_back.get("code")
    if not code:
        sys.exit("Error: no 'code' parameter found in the URL you pasted.")

    resp = requests.post(
        _YAHOO_TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
        auth=(client_id, client_secret),
    )
    resp.raise_for_status()
    return _stamp_expiry(resp.json())


def get_session() -> requests.Session:
    """Return an authenticated requests.Session, refreshing or re-authorising as needed."""
    secrets = _load_secrets()
    client_id = secrets["yahoo"]["client_id"]
    client_secret = secrets["yahoo"]["client_secret"]
    redirect_uri = secrets["yahoo"].get("redirect_uri", "https://localhost:8501").strip()

    tokens = _load_token()

    if tokens and _is_valid(tokens):
        pass  # use as-is
    elif tokens and tokens.get("refresh_token"):
        print("Refreshing Yahoo token...")
        tokens = _refresh_token(tokens, client_id, client_secret)
        if tokens is None:
            print("Refresh failed — re-authorising.")
            tokens = _authorize(client_id, client_secret, redirect_uri)
    else:
        tokens = _authorize(client_id, client_secret, redirect_uri)

    _save_token(tokens)
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return session


# ---------------------------------------------------------------------------
# Data fetching helpers
# ---------------------------------------------------------------------------

BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"


def _get(session: requests.Session, url: str) -> dict:
    import xmltodict
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    return json.loads(json.dumps(xmltodict.parse(resp.content)))


# ---------------------------------------------------------------------------
# Main snapshot logic
# ---------------------------------------------------------------------------

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Authenticating with Yahoo...")
    session = get_session()

    # --- 1. League metadata ---
    print(f"Fetching league metadata for {TARGET_LEAGUE_KEY}...")
    from data.leagues import get_user_hockey_leagues
    all_leagues = get_user_hockey_leagues(session)
    target = next((lg for lg in all_leagues if lg["league_key"] == TARGET_LEAGUE_KEY), None)
    if target is None:
        sys.exit(f"Error: league {TARGET_LEAGUE_KEY!r} not found in your account.\n"
                 f"Available leagues: {[lg['league_key'] for lg in all_leagues]}")
    # Add snapshot week to the metadata
    target["snapshot_week"] = SNAPSHOT_WEEK
    (OUTPUT_DIR / "league_meta.json").write_text(json.dumps(target, indent=2))
    print(f"  Saved league_meta.json  ({target['league_name']})")

    # --- 2. Stat categories ---
    print("Fetching stat categories...")
    from data.client import get_stat_categories
    stat_cats = get_stat_categories(session, TARGET_LEAGUE_KEY)
    (OUTPUT_DIR / "stat_categories.json").write_text(json.dumps(stat_cats, indent=2))
    print(f"  Saved stat_categories.json  ({len(stat_cats)} categories)")

    id_to_name = {c["stat_id"]: c["stat_name"] for c in stat_cats if c["is_enabled"]}

    # --- 3. Matchup history up to SNAPSHOT_WEEK ---
    print(f"Fetching matchup history (weeks 1–{SNAPSHOT_WEEK})...")
    _fetch_matchups(session, id_to_name)

    # --- 4. Player pool — season stats ---
    print("Fetching available player pool (season stats)...")
    season_df = _fetch_all_season_players(session, id_to_name)
    season_df.to_parquet(OUTPUT_DIR / "players_season.parquet", index=False)
    print(f"  Saved players_season.parquet  ({len(season_df)} players)")

    # --- 5. Player pool — last-30-day stats ---
    print("Fetching last-30-day stats for the same player pool...")
    from data.players import fetch_lastmonth_batch
    player_keys = season_df["player_key"].tolist()
    lm_df = fetch_lastmonth_batch(session, player_keys, id_to_name)
    lm_df.to_parquet(OUTPUT_DIR / "players_lastmonth.parquet", index=False)
    print(f"  Saved players_lastmonth.parquet  ({len(lm_df)} players)")

    # --- 6. Games remaining snapshot ---
    print("Fetching games remaining this week...")
    _fetch_games_remaining(session)

    print("\nDone. All demo data written to demo/data/")
    print("Commit the contents of demo/data/ to the repo.")


def _fetch_matchups(session: requests.Session, id_to_name: dict) -> None:
    """Fetch all weeks up to SNAPSHOT_WEEK and save as matchups.parquet."""
    from data.client import BASE_URL as _BASE, _as_list, _coerce, _get as _client_get

    all_rows: list[dict] = []
    for week in range(1, SNAPSHOT_WEEK + 1):
        url = f"{_BASE}/league/{TARGET_LEAGUE_KEY}/teams/stats;type=week;week={week}"
        data = _client_get(session, url)
        teams_node = (
            data.get("fantasy_content", {})
            .get("league", {})
            .get("teams", {})
        )
        if not teams_node:
            continue
        for team in _as_list(teams_node.get("team", [])):
            meta = team["team_key"] if isinstance(team, str) else team
            if isinstance(meta, str):
                continue
            team_key = meta.get("team_key", "")
            team_name_raw = meta.get("name", "")
            # team_name is sometimes nested under team[0] list structure
            if isinstance(team_name_raw, dict):
                team_name_raw = team_name_raw.get("#text", str(team_name_raw))
            stats_node = meta.get("team_stats", {}).get("stats", {}).get("stat", [])
            row: dict = {
                "team_key": team_key,
                "team_name": str(team_name_raw),
                "week": week,
                "games_played": 0,
            }
            for stat in _as_list(stats_node):
                sid = stat.get("stat_id", "")
                val = _coerce(stat.get("value"))
                if sid == "0":
                    row["games_played"] = int(val)
                elif sid in id_to_name:
                    row[id_to_name[sid]] = val
            all_rows.append(row)

    df = pd.DataFrame(all_rows)
    df.to_parquet(OUTPUT_DIR / "matchups.parquet", index=False)
    print(f"  Saved matchups.parquet  ({len(df)} team-week rows across {SNAPSHOT_WEEK} weeks)")


def _fetch_all_season_players(session: requests.Session, id_to_name: dict) -> pd.DataFrame:
    """
    Fetch available players with season stats across all stat categories.

    Fetches top-25 by each enabled stat, then merges into a single pool.
    This mirrors how the live waiver wire builds its pool — one slice per stat.
    """
    from data.players import fetch_season_pool

    all_dfs: list[pd.DataFrame] = []
    seen_keys: set[str] = set()

    for stat_id, stat_name in id_to_name.items():
        print(f"    Fetching top players sorted by {stat_name}...")
        df = fetch_season_pool(session, TARGET_LEAGUE_KEY, stat_id, id_to_name)
        if df.empty:
            continue
        fresh = df[~df["player_key"].isin(seen_keys)]
        if not fresh.empty:
            all_dfs.append(fresh)
            seen_keys.update(fresh["player_key"].tolist())

    if not all_dfs:
        sys.exit("Error: no player data fetched. Check TARGET_LEAGUE_KEY and SNAPSHOT_WEEK.")

    merged = pd.concat(all_dfs, ignore_index=True)
    # Fill any missing stat columns with 0 (can happen when players didn't accrue that stat)
    for col in id_to_name.values():
        if col not in merged.columns:
            merged[col] = 0.0
    return merged


def _fetch_games_remaining(session: requests.Session) -> None:
    """Fetch games remaining this week as a team_abbr → int mapping."""
    from data import schedule as schedule_module, scoreboard as scoreboard_module

    try:
        sb = scoreboard_module.get_current_matchup(session, TARGET_LEAGUE_KEY, SNAPSHOT_WEEK)
        from datetime import date
        week_end = date.fromisoformat(sb["week_end"])
        from_date = date.fromisoformat(sb["week_start"])
        # Get all team abbreviations from the season player pool we just fetched
        players_df = pd.read_parquet(OUTPUT_DIR / "players_season.parquet")
        team_abbrs = list(players_df["team_abbr"].dropna().unique())
        games_map = schedule_module.get_remaining_games(team_abbrs, from_date, week_end)
        (OUTPUT_DIR / "games_remaining.json").write_text(json.dumps(games_map, indent=2))
        print(f"  Saved games_remaining.json  ({len(games_map)} teams)")
    except Exception as e:
        print(f"  Warning: could not fetch games remaining ({e}). Saving empty map.")
        (OUTPUT_DIR / "games_remaining.json").write_text(json.dumps({}, indent=2))


if __name__ == "__main__":
    # Run from the project root: python scripts/generate_demo_data.py
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()
