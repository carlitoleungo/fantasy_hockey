"""
Demo mode data layer.

Exposes the same data needed by the app's pages but loads from pre-saved
static files in demo/data/ instead of hitting any API. Zero network calls.

Called conditionally by pages and utils/common.py when
st.session_state["demo_mode"] is True.

All functions are simple file loaders — no session, no league_key parameter
needed because the demo snapshot is fixed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_DATA_DIR = Path(__file__).parent.parent / "demo" / "data"

DEMO_LEAGUE_KEY = "demo.l.000000"


# ---------------------------------------------------------------------------
# League context
# ---------------------------------------------------------------------------

def get_demo_league_context() -> dict:
    """
    Return a league dict matching the shape of get_user_hockey_leagues() output.

    Loaded from demo/data/league_meta.json so the real league name and season
    are used rather than placeholder values.
    """
    meta = _load_json("league_meta.json")
    return {
        "league_key": DEMO_LEAGUE_KEY,
        "league_id": "000000",
        "league_name": meta.get("league_name", "Demo League"),
        "scoring_type": "head",
        "season": meta.get("season", 2025),
        "start_week": meta.get("start_week", 1),
        "start_date": meta.get("start_date", "2024-10-08"),
        "end_date": meta.get("end_date", "2025-04-13"),
    }


def get_current_week() -> int:
    """Return the snapshot week number stored in league_meta.json."""
    meta = _load_json("league_meta.json")
    return int(meta.get("snapshot_week", 14))


# ---------------------------------------------------------------------------
# Matchup data
# ---------------------------------------------------------------------------

def get_matchups() -> pd.DataFrame:
    """Load matchup history from demo/data/matchups.parquet."""
    path = _DATA_DIR / "matchups.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


# ---------------------------------------------------------------------------
# Stat categories
# ---------------------------------------------------------------------------

def get_stat_categories() -> list[dict]:
    """Load stat category metadata from demo/data/stat_categories.json."""
    return _load_json("stat_categories.json")


# ---------------------------------------------------------------------------
# Player pools
# ---------------------------------------------------------------------------

def load_season_pool() -> pd.DataFrame:
    """Load the full available-player pool with season stats."""
    path = _DATA_DIR / "players_season.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def load_lastmonth_pool() -> pd.DataFrame:
    """Load the full available-player pool with last-30-day stats."""
    path = _DATA_DIR / "players_lastmonth.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


# ---------------------------------------------------------------------------
# Schedule / games remaining
# ---------------------------------------------------------------------------

def get_games_remaining() -> dict[str, int]:
    """
    Return a team_abbr → games_remaining mapping snapshotted at demo week.

    This is used by the waiver wire page to show games remaining this week.
    In demo mode the values are fixed from the snapshot.
    """
    data = _load_json("games_remaining.json")
    return {k: int(v) for k, v in data.items()}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_json(filename: str) -> dict | list:
    path = _DATA_DIR / filename
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)
