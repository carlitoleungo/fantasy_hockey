"""
Local parquet cache for cross-session data persistence.

Two-layer caching model:
- This module handles the disk layer: .cache/{league_key}/{data_type}.parquet
- @st.cache_data handles the in-session memory layer (applied in pages/ as needed)

last_updated.json lives alongside the parquet files and tracks write timestamps
per data type, so callers can implement delta-fetch and staleness logic without
reading the parquet files themselves.

All timestamps are stored as UTC ISO 8601 strings and returned as timezone-aware
datetime objects.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

CACHE_DIR = os.environ.get("CACHE_DIR", ".cache")


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _parquet_path(league_key: str, data_type: str) -> Path:
    """Return the Path for a league's parquet file of the given data type."""
    return Path(CACHE_DIR) / league_key / f"{data_type}.parquet"


def _meta_path(league_key: str) -> Path:
    """Return the Path for a league's last_updated.json metadata file."""
    return Path(CACHE_DIR) / league_key / "last_updated.json"


def _ensure_dir(league_key: str) -> None:
    """Create the cache directory for the league if it doesn't exist."""
    (Path(CACHE_DIR) / league_key).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def _read_meta(league_key: str) -> dict:
    """Load the last_updated metadata for a league, returning {} if absent."""
    path = _meta_path(league_key)
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _write_meta(league_key: str, data_type: str, ts: datetime) -> None:
    """Record a write timestamp for data_type in the league's metadata file."""
    meta = _read_meta(league_key)
    meta[data_type] = ts.isoformat()
    _ensure_dir(league_key)
    with open(_meta_path(league_key), "w") as f:
        json.dump(meta, f, indent=2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read(league_key: str, data_type: str) -> pd.DataFrame | None:
    """Load a parquet file. Returns None if the file doesn't exist."""
    path = _parquet_path(league_key, data_type)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def write(league_key: str, data_type: str, df: pd.DataFrame) -> None:
    """Write/overwrite a parquet file and update last_updated.json."""
    _ensure_dir(league_key)
    df.to_parquet(_parquet_path(league_key, data_type), index=False)
    _write_meta(league_key, data_type, _now())


def append(league_key: str, data_type: str, df: pd.DataFrame) -> None:
    """
    Append rows to an existing parquet file, or create it if absent.
    Row order is preserved: existing rows first, new rows after.
    Index is reset on write — callers should not rely on index values.
    """
    existing = read(league_key, data_type)
    if existing is not None:
        df = pd.concat([existing, df], ignore_index=True)
    _ensure_dir(league_key)
    df.to_parquet(_parquet_path(league_key, data_type), index=False)
    _write_meta(league_key, data_type, _now())


def last_updated(league_key: str, data_type: str) -> datetime | None:
    """Return the UTC datetime of the last write, or None if never written."""
    meta = _read_meta(league_key)
    if data_type not in meta:
        return None
    return datetime.fromisoformat(meta[data_type])


def is_stale(league_key: str, data_type: str, max_age_hours: float) -> bool:
    """
    Return True if the cache is older than max_age_hours, or doesn't exist.
    Used by callers to decide whether to re-fetch from the API.
    """
    ts = last_updated(league_key, data_type)
    if ts is None:
        return True
    return (_now() - ts).total_seconds() > max_age_hours * 3600


# ---------------------------------------------------------------------------
# Player pool cache (waiver wire)
# ---------------------------------------------------------------------------
# Season pools are keyed by (league_key, position, stat_name) — each is a
# 25-row parquet representing the top-25 available players sorted by that stat.
# The lastmonth cache is a single growing parquet per league, keyed by player_key.

def _pool_key(position: str, stat_name: str) -> str:
    """Build a safe data_type string for a (position, stat_name) pool."""
    safe_stat = stat_name.replace(" ", "_").replace("/", "_")
    safe_pos = position if position and position != "All" else "All"
    return f"ww_season__{safe_pos}__{safe_stat}"


def read_player_pool(league_key: str, position: str, stat_name: str) -> "pd.DataFrame | None":
    """Load a cached season pool slice. Returns None if absent."""
    return read(league_key, _pool_key(position, stat_name))


def write_player_pool(league_key: str, position: str, stat_name: str, df: "pd.DataFrame") -> None:
    """Write a season pool slice to disk."""
    write(league_key, _pool_key(position, stat_name), df)


def is_player_pool_stale(
    league_key: str, position: str, stat_name: str, max_age_hours: float = 24
) -> bool:
    """True if the pool slice is older than max_age_hours or doesn't exist."""
    return is_stale(league_key, _pool_key(position, stat_name), max_age_hours)


def read_lastmonth_cache(league_key: str) -> "pd.DataFrame | None":
    """Load the cumulative lastmonth stats cache. Returns None if absent."""
    return read(league_key, "ww_lastmonth")


def upsert_lastmonth_cache(league_key: str, df: "pd.DataFrame") -> None:
    """
    Merge new lastmonth rows into the cache, replacing existing player_key rows.

    Newer rows (from df) win over existing rows for the same player_key.
    """
    existing = read(league_key, "ww_lastmonth")
    if existing is not None and not existing.empty:
        existing = existing[~existing["player_key"].isin(df["player_key"])]
        df = pd.concat([existing, df], ignore_index=True)
    write(league_key, "ww_lastmonth", df)


def is_lastmonth_stale(league_key: str, max_age_hours: float = 24) -> bool:
    """True if the lastmonth cache is older than max_age_hours or doesn't exist."""
    return is_stale(league_key, "ww_lastmonth", max_age_hours)
