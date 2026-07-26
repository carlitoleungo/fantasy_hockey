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
import threading
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
# Concurrency (ticket 037 — atomic rename + per-league lock)
# ---------------------------------------------------------------------------

def run_concurrently(targets, timeout=60):
    """
    Run each callable in its own thread, released simultaneously by a Barrier.

    Returns the list of exceptions raised by any thread (empty if all clean).
    Fails the test if a thread is still alive after `timeout` — that means a
    deadlock, which is the failure mode a badly-scoped lock would produce.
    """
    barrier = threading.Barrier(len(targets))
    errors = []

    def runner(fn):
        barrier.wait()
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 — the test asserts on these
            errors.append(exc)

    threads = [threading.Thread(target=runner, args=(fn,)) for fn in targets]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=timeout)
    assert not any(t.is_alive() for t in threads), "thread did not finish — deadlock?"
    return errors


def test_concurrent_appends_do_not_lose_rows():
    """N threads appending one row each must leave exactly N rows on disk."""
    n = 12

    def appender(i):
        def run():
            row = pd.DataFrame({"team_name": [f"team_{i}"], "week": [i], "goals": [i], "assists": [i]})
            cache.append(LEAGUE_KEY, "matchups", row)
        return run

    errors = run_concurrently([appender(i) for i in range(n)])
    assert errors == []
    result = cache.read(LEAGUE_KEY, "matchups")
    assert len(result) == n
    assert sorted(result["week"]) == list(range(n))


def test_concurrent_appends_onto_seeded_file_preserve_seed_rows():
    seed = matchups_df()
    cache.write(LEAGUE_KEY, "matchups", seed)
    n = 8

    def appender(i):
        def run():
            row = pd.DataFrame({"team_name": [f"team_{i}"], "week": [i], "goals": [i], "assists": [i]})
            cache.append(LEAGUE_KEY, "matchups", row)
        return run

    errors = run_concurrently([appender(i) for i in range(n)])
    assert errors == []
    result = cache.read(LEAGUE_KEY, "matchups")
    assert len(result) == len(seed) + n
    assert "Mighty Ducks" in result["team_name"].values
    assert "Maple Leafs" in result["team_name"].values


def test_reads_during_concurrent_writes_never_observe_a_partial_file():
    """
    A reader overlapping a writer sees either the old or the new complete frame,
    never a truncated parquet (which raises ArrowInvalid/OSError).
    """
    small = pd.DataFrame({"x": range(500)})
    big = pd.DataFrame({"x": range(4000)})
    cache.write(LEAGUE_KEY, "big", small)

    stop = threading.Event()
    observed = []

    def writer():
        try:
            for i in range(40):
                cache.write(LEAGUE_KEY, "big", big if i % 2 else small)
        finally:
            stop.set()

    def reader():
        while not stop.is_set():
            observed.append(cache.read(LEAGUE_KEY, "big"))

    errors = run_concurrently([writer, reader, reader, reader])
    assert errors == []
    assert observed, "readers never got to run"
    # Every observation is a complete frame: never None (the file always exists
    # after the seed write) and never a partial row count.
    assert all(df is not None for df in observed)
    assert {len(df) for df in observed} <= {len(small), len(big)}


def test_concurrent_write_meta_keeps_every_data_type():
    """Interleaved metadata writes must not lose keys or produce invalid JSON."""
    n = 12
    ts = datetime.now(timezone.utc)

    def writer(i):
        def run():
            cache._write_meta(LEAGUE_KEY, f"type_{i}", ts)
        return run

    errors = run_concurrently([writer(i) for i in range(n)])
    assert errors == []
    with open(cache._meta_path(LEAGUE_KEY)) as f:
        meta = json.load(f)  # raises JSONDecodeError if the file was torn
    assert sorted(meta) == sorted(f"type_{i}" for i in range(n))
    for i in range(n):
        assert cache.last_updated(LEAGUE_KEY, f"type_{i}") is not None


def test_concurrent_writes_of_distinct_data_types_keep_all_metadata():
    """write() serialises its own metadata update through the same league lock."""
    n = 10

    def writer(i):
        def run():
            cache.write(LEAGUE_KEY, f"players_{i}", players_df())
        return run

    errors = run_concurrently([writer(i) for i in range(n)])
    assert errors == []
    meta = cache._read_meta(LEAGUE_KEY)
    assert sorted(meta) == sorted(f"players_{i}" for i in range(n))
    for i in range(n):
        assert cache.read(LEAGUE_KEY, f"players_{i}") is not None


def test_concurrent_upsert_lastmonth_keeps_every_player():
    n = 10

    def upserter(i):
        def run():
            cache.upsert_lastmonth_cache(LEAGUE_KEY, pd.DataFrame({"player_key": [f"465.p.{i}"], "goals": [i]}))
        return run

    errors = run_concurrently([upserter(i) for i in range(n)])
    assert errors == []
    result = cache.read_lastmonth_cache(LEAGUE_KEY)
    assert len(result) == n
    assert sorted(result["player_key"]) == sorted(f"465.p.{i}" for i in range(n))


def test_upsert_lastmonth_still_replaces_rows_for_the_same_player():
    cache.upsert_lastmonth_cache(LEAGUE_KEY, pd.DataFrame({"player_key": ["465.p.1"], "goals": [3]}))
    cache.upsert_lastmonth_cache(LEAGUE_KEY, pd.DataFrame({"player_key": ["465.p.1"], "goals": [9]}))
    result = cache.read_lastmonth_cache(LEAGUE_KEY)
    assert len(result) == 1
    assert result["goals"].iloc[0] == 9


def test_writes_leave_no_temp_files_behind(tmp_path):
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    cache.append(LEAGUE_KEY, "matchups", matchups_df())
    names = sorted(p.name for p in (tmp_path / LEAGUE_KEY).iterdir())
    assert names == ["last_updated.json", "matchups.parquet"]


def test_temp_file_is_written_into_the_target_directory(tmp_path, monkeypatch):
    """
    os.replace() is only atomic within one filesystem, so the temp file must be
    created next to its target rather than in the system temp dir.
    """
    seen = []
    real_mkstemp = cache.tempfile.mkstemp

    def spy(*args, **kwargs):
        seen.append(kwargs.get("dir"))
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(cache.tempfile, "mkstemp", spy)
    cache.write(LEAGUE_KEY, "matchups", matchups_df())
    assert seen  # parquet + metadata
    assert all(str(d) == str(tmp_path / LEAGUE_KEY) for d in seen)


# ---------------------------------------------------------------------------
# Shared-tier path affordance (ticket 037 — affordance only, no call site uses it)
# ---------------------------------------------------------------------------

def test_shared_write_round_trips_through_shared_dir(tmp_path):
    df = players_df()
    cache.write(None, "some_type", df)
    assert (tmp_path / "_shared" / "some_type.parquet").exists()
    pd.testing.assert_frame_equal(cache.read(None, "some_type"), df)


def test_shared_read_returns_none_when_missing():
    assert cache.read(None, "some_type") is None


def test_shared_append_round_trips(tmp_path):
    cache.append(None, "some_type", players_df())
    cache.append(None, "some_type", players_df())
    assert (tmp_path / "_shared" / "some_type.parquet").exists()
    assert len(cache.read(None, "some_type")) == 4


def test_shared_metadata_is_tracked(tmp_path):
    cache.write(None, "some_type", players_df())
    assert (tmp_path / "_shared" / "last_updated.json").exists()
    assert cache.last_updated(None, "some_type") is not None
    assert cache.is_stale(None, "some_type", max_age_hours=24) is False
    assert cache.is_stale(None, "other_type", max_age_hours=24) is True


def test_shared_tier_is_isolated_from_league_keyed_data():
    shared = pd.DataFrame({"x": [1]})
    league = pd.DataFrame({"x": [2]})
    cache.write(None, "matchups", shared)
    cache.write(LEAGUE_KEY, "matchups", league)
    assert cache.read(None, "matchups")["x"].iloc[0] == 1
    assert cache.read(LEAGUE_KEY, "matchups")["x"].iloc[0] == 2


def test_league_keyed_paths_are_unchanged(tmp_path):
    assert cache._parquet_path(LEAGUE_KEY, "matchups") == tmp_path / LEAGUE_KEY / "matchups.parquet"
    assert cache._meta_path(LEAGUE_KEY) == tmp_path / LEAGUE_KEY / "last_updated.json"
    assert cache._parquet_path(None, "matchups") == tmp_path / "_shared" / "matchups.parquet"
    assert cache._meta_path(None) == tmp_path / "_shared" / "last_updated.json"


def test_concurrent_shared_appends_do_not_lose_rows():
    n = 8

    def appender(i):
        def run():
            cache.append(None, "some_type", pd.DataFrame({"x": [i]}))
        return run

    errors = run_concurrently([appender(i) for i in range(n)])
    assert errors == []
    assert sorted(cache.read(None, "some_type")["x"]) == list(range(n))


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
