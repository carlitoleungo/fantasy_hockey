"""
Unit tests for data/cache.py.

All tests redirect CACHE_DIR to a pytest tmp_path so nothing is written to
the real .cache/ directory. The autouse fixture handles this automatically —
no test needs to clean up after itself.

If more test files are added later, consider moving the monkeypatch fixture
to a conftest.py so it can be shared.
"""

import importlib
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

import data.cache as cache

LEAGUE_KEY = "nhl.l.99999"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path, monkeypatch):
    """Redirect all cache reads/writes to a temporary directory."""
    monkeypatch.setattr(cache, "CACHE_DIR", str(tmp_path))


def matchups_df() -> pd.DataFrame:
    return pd.DataFrame({
        "team_name": ["Mighty Ducks", "Maple Leafs"],
        "week": [1, 1],
        "goals": [10, 8],
        "assists": [20, 15],
    })


def players_df() -> pd.DataFrame:
    return pd.DataFrame({
        "player_name": ["McDavid", "Draisaitl"],
        "goals": [40, 35],
        "assists": [80, 65],
    })


# ---------------------------------------------------------------------------
# read()
# ---------------------------------------------------------------------------

def test_read_returns_none_when_file_missing():
    assert cache.read(LEAGUE_KEY, "matchups") is None


def test_read_returns_none_for_unknown_data_type():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    assert cache.read(LEAGUE_KEY, "players") is None


def test_read_returns_dataframe_after_write():
    df = matchups_df()
    cache.write(LEAGUE_KEY, "matchups", df)
    result = cache.read(LEAGUE_KEY, "matchups")
    pd.testing.assert_frame_equal(result, df)


def test_read_preserves_column_types():
    df = matchups_df()
    cache.write(LEAGUE_KEY, "matchups", df)
    result = cache.read(LEAGUE_KEY, "matchups")
    assert result["goals"].dtype == df["goals"].dtype
    assert result["team_name"].dtype == df["team_name"].dtype


# ---------------------------------------------------------------------------
# write()
# ---------------------------------------------------------------------------

def test_write_creates_parent_directories_automatically():
    # league dir doesn't exist yet — write should create it
    cache.write("brand/new/league", "matchups", matchups_df())
    assert cache.read("brand/new/league", "matchups") is not None


def test_write_overwrites_existing_file():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    replacement = pd.DataFrame({"team_name": ["Senators"], "week": [5], "goals": [3], "assists": [6]})
    cache.write(LEAGUE_KEY, "matchups", replacement)
    result = cache.read(LEAGUE_KEY, "matchups")
    pd.testing.assert_frame_equal(result, replacement)


def test_write_updates_last_updated_timestamp():
    before = datetime.now(timezone.utc)
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    ts = cache.last_updated(LEAGUE_KEY, "matchups")
    assert ts is not None
    assert ts >= before


def test_write_does_not_affect_other_data_types():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    assert cache.read(LEAGUE_KEY, "players") is None
    assert cache.last_updated(LEAGUE_KEY, "players") is None


# ---------------------------------------------------------------------------
# append()
# ---------------------------------------------------------------------------

def test_append_creates_file_when_none_exists():
    df = matchups_df()
    cache.append(LEAGUE_KEY, "matchups", df)
    result = cache.read(LEAGUE_KEY, "matchups")
    pd.testing.assert_frame_equal(result, df)


def test_append_adds_rows_after_existing():
    week1 = pd.DataFrame({"team_name": ["Ducks"], "week": [1], "goals": [10], "assists": [20]})
    week2 = pd.DataFrame({"team_name": ["Ducks"], "week": [2], "goals": [8], "assists": [14]})
    cache.write(LEAGUE_KEY, "matchups", week1)
    cache.append(LEAGUE_KEY, "matchups", week2)
    result = cache.read(LEAGUE_KEY, "matchups")
    assert len(result) == 2
    assert list(result["week"]) == [1, 2]


def test_append_preserves_existing_rows():
    original = matchups_df()
    extra = pd.DataFrame({"team_name": ["Senators"], "week": [2], "goals": [5], "assists": [9]})
    cache.write(LEAGUE_KEY, "matchups", original)
    cache.append(LEAGUE_KEY, "matchups", extra)
    result = cache.read(LEAGUE_KEY, "matchups")
    assert "Mighty Ducks" in result["team_name"].values
    assert "Maple Leafs" in result["team_name"].values
    assert "Senators" in result["team_name"].values


def test_append_resets_index():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    extra = pd.DataFrame({"team_name": ["X"], "week": [3], "goals": [1], "assists": [2]})
    cache.append(LEAGUE_KEY, "matchups", extra)
    result = cache.read(LEAGUE_KEY, "matchups")
    assert list(result.index) == list(range(len(result)))


def test_append_updates_last_updated_timestamp():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    before = datetime.now(timezone.utc)
    extra = pd.DataFrame({"team_name": ["X"], "week": [3], "goals": [1], "assists": [2]})
    cache.append(LEAGUE_KEY, "matchups", extra)
    ts = cache.last_updated(LEAGUE_KEY, "matchups")
    assert ts >= before


# ---------------------------------------------------------------------------
# last_updated()
# ---------------------------------------------------------------------------

def test_last_updated_returns_none_when_never_written():
    assert cache.last_updated(LEAGUE_KEY, "matchups") is None


def test_last_updated_returns_none_for_unwritten_data_type():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    assert cache.last_updated(LEAGUE_KEY, "players") is None


def test_last_updated_returns_datetime():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    ts = cache.last_updated(LEAGUE_KEY, "matchups")
    assert isinstance(ts, datetime)


def test_last_updated_is_timezone_aware():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    ts = cache.last_updated(LEAGUE_KEY, "matchups")
    assert ts.tzinfo is not None


def test_last_updated_tracks_each_data_type_independently():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    cache.write(LEAGUE_KEY, "players", players_df())
    assert cache.last_updated(LEAGUE_KEY, "matchups") is not None
    assert cache.last_updated(LEAGUE_KEY, "players") is not None
    # Each gets its own timestamp entry
    meta = cache._read_meta(LEAGUE_KEY)
    assert "matchups" in meta
    assert "players" in meta


# ---------------------------------------------------------------------------
# is_stale()
# ---------------------------------------------------------------------------

def test_is_stale_true_when_nothing_written():
    assert cache.is_stale(LEAGUE_KEY, "matchups", max_age_hours=24) is True


def test_is_stale_false_immediately_after_write():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    assert cache.is_stale(LEAGUE_KEY, "matchups", max_age_hours=24) is False


def test_is_stale_true_when_timestamp_is_old():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    # Backdate the timestamp by 25 hours
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    with open(cache._meta_path(LEAGUE_KEY), "w") as f:
        json.dump({"matchups": old_ts}, f)
    assert cache.is_stale(LEAGUE_KEY, "matchups", max_age_hours=24) is True


def test_is_stale_false_when_within_max_age():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    # Backdate by 1 hour, max_age is 24 — should not be stale
    recent_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with open(cache._meta_path(LEAGUE_KEY), "w") as f:
        json.dump({"matchups": recent_ts}, f)
    assert cache.is_stale(LEAGUE_KEY, "matchups", max_age_hours=24) is False


def test_is_stale_respects_max_age_hours_boundary():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    # Exactly at the boundary (just over 1 hour ago), max_age is 1 hour
    just_over = (datetime.now(timezone.utc) - timedelta(hours=1, seconds=1)).isoformat()
    with open(cache._meta_path(LEAGUE_KEY), "w") as f:
        json.dump({"matchups": just_over}, f)
    assert cache.is_stale(LEAGUE_KEY, "matchups", max_age_hours=1) is True


# ---------------------------------------------------------------------------
# Isolation between league keys and data types
# ---------------------------------------------------------------------------

def test_different_league_keys_are_isolated():
    df_a = pd.DataFrame({"x": [1]})
    df_b = pd.DataFrame({"x": [2]})
    cache.write("league_a", "matchups", df_a)
    cache.write("league_b", "matchups", df_b)
    assert cache.read("league_a", "matchups")["x"].iloc[0] == 1
    assert cache.read("league_b", "matchups")["x"].iloc[0] == 2


def test_different_data_types_are_isolated():
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    cache.write(LEAGUE_KEY, "players", players_df())
    matchups = cache.read(LEAGUE_KEY, "matchups")
    players = cache.read(LEAGUE_KEY, "players")
    assert "team_name" in matchups.columns
    assert "player_name" in players.columns


# ---------------------------------------------------------------------------
# CACHE_DIR env var
# ---------------------------------------------------------------------------

def test_cache_dir_env_var_overrides_default(tmp_path, monkeypatch):
    """CACHE_DIR env var is picked up at module load time."""
    custom_dir = str(tmp_path / "custom_cache")
    monkeypatch.setenv("CACHE_DIR", custom_dir)
    importlib.reload(cache)
    try:
        assert cache.CACHE_DIR == custom_dir
        cache.write(LEAGUE_KEY, "matchups", matchups_df())
        expected = (tmp_path / "custom_cache" / LEAGUE_KEY / "matchups.parquet")
        assert expected.exists()
    finally:
        monkeypatch.delenv("CACHE_DIR", raising=False)
        importlib.reload(cache)
