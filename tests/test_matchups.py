"""
Unit tests for data/matchups.py.

Uses the real cache (redirected to tmp_path) and monkeypatched client
functions — no HTTP calls, no live API.

Tests focus on the delta-fetch logic: which weeks get fetched, that new rows
are appended correctly, and that the returned DataFrame has the expected shape.
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

import data.cache as cache
import data.client as client
from data import matchups

LEAGUE_KEY = "nhl.l.99999"

# Minimal stat categories: two enabled, one display-only
STAT_CATEGORIES = [
    {"stat_id": "1", "stat_name": "Goals",   "abbreviation": "G",   "stat_group": "offense", "is_enabled": True},
    {"stat_id": "2", "stat_name": "Assists",  "abbreviation": "A",   "stat_group": "offense", "is_enabled": True},
    {"stat_id": "3", "stat_name": "Points",   "abbreviation": "Pts", "stat_group": "offense", "is_enabled": False},
]

TEAMS = [
    {"team_key": "nhl.l.99999.t.1", "team_id": "1", "team_name": "Team Alpha", "manager_name": "Alice"},
    {"team_key": "nhl.l.99999.t.2", "team_id": "2", "team_name": "Team Beta",  "manager_name": "Bob"},
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Redirect cache reads/writes to a temp directory for every test."""
    monkeypatch.setattr(cache, "CACHE_DIR", str(tmp_path))


def make_settings(current_week: int, start_week: int = 1) -> dict:
    return {"current_week": current_week, "start_week": start_week, "end_week": 25}


def fake_all_teams_week_stats(session, league_key: str, week: int, stat_categories) -> list[dict]:
    """Deterministic fake stats for all teams: Goals = week * 2, Assists = week * 3."""
    return [
        {
            "team_key": t["team_key"],
            "team_name": t["team_name"],
            "week": week,
            "games_played": week,
            "Goals": float(week * 2),
            "Assists": float(week * 3),
        }
        for t in TEAMS
    ]


# ---------------------------------------------------------------------------
# Delta fetch: empty cache
# ---------------------------------------------------------------------------

def test_fetches_all_weeks_when_cache_empty(monkeypatch):
    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=3))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)

    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    result = matchups.get_matchups(None, LEAGUE_KEY)

    assert result is not None
    # 3 weeks × 2 teams = 6 rows
    assert len(result) == 6
    assert sorted(result["week"].unique()) == [1, 2, 3]


def test_fetches_from_start_week_when_cache_empty(monkeypatch):
    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=3, start_week=2))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)

    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    result = matchups.get_matchups(None, LEAGUE_KEY)

    # start_week=2 so only weeks 2 and 3: 2 weeks × 2 teams = 4 rows
    assert len(result) == 4
    assert sorted(result["week"].unique()) == [2, 3]


# ---------------------------------------------------------------------------
# Delta fetch: partial cache (most important case)
# ---------------------------------------------------------------------------

def test_fetches_only_missing_weeks_when_cache_partial(monkeypatch):
    # Seed the cache with weeks 1 and 2
    seed = pd.DataFrame([
        {"team_key": "nhl.l.99999.t.1", "team_name": "Team Alpha", "week": 1, "Goals": 2.0, "Assists": 3.0},
        {"team_key": "nhl.l.99999.t.2", "team_name": "Team Beta",  "week": 1, "Goals": 4.0, "Assists": 6.0},
        {"team_key": "nhl.l.99999.t.1", "team_name": "Team Alpha", "week": 2, "Goals": 4.0, "Assists": 6.0},
        {"team_key": "nhl.l.99999.t.2", "team_name": "Team Beta",  "week": 2, "Goals": 8.0, "Assists": 12.0},
    ])
    cache.write(LEAGUE_KEY, "matchups", seed)

    fetched_weeks = []

    def tracking_stats(session, league_key, week, stat_categories):
        fetched_weeks.append(week)
        return fake_all_teams_week_stats(session, league_key, week, stat_categories)

    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=4))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", tracking_stats)

    result = matchups.get_matchups(None, LEAGUE_KEY)

    # Only weeks 3 and 4 should have been fetched
    assert set(fetched_weeks) == {3, 4}
    # Total: 4 seeded rows + 4 new rows (weeks 3 & 4 × 2 teams)
    assert len(result) == 8
    assert sorted(result["week"].unique()) == [1, 2, 3, 4]


def test_current_week_always_refetched_even_when_cached(monkeypatch):
    # Cache already has the current week (potentially with all-zero stats from an
    # early-in-week fetch). The current week must always be re-fetched so that
    # stats update as games are played during the week.
    seed = pd.DataFrame([
        {"team_key": "nhl.l.99999.t.1", "team_name": "Team Alpha", "week": 5, "Goals": 0.0},
        {"team_key": "nhl.l.99999.t.2", "team_name": "Team Beta",  "week": 5, "Goals": 0.0},
    ])
    cache.write(LEAGUE_KEY, "matchups", seed)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    monkeypatch.setattr(cache, "last_updated", lambda league, dtype: yesterday)

    fetched_weeks = []

    def tracking_stats(session, league_key, week, stat_categories):
        fetched_weeks.append(week)
        return fake_all_teams_week_stats(session, league_key, week, stat_categories)

    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=5))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", tracking_stats)

    result = matchups.get_matchups(None, LEAGUE_KEY)

    assert 5 in fetched_weeks            # current week always re-fetched
    # fresh data replaces zeroes via drop_duplicates(keep="last")
    assert result[result["week"] == 5]["Goals"].iloc[0] == 10.0


# ---------------------------------------------------------------------------
# Data shape and content
# ---------------------------------------------------------------------------

def test_result_contains_team_name_column(monkeypatch):
    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=1))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)

    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    result = matchups.get_matchups(None, LEAGUE_KEY)

    assert "team_name" in result.columns
    assert set(result["team_name"]) == {"Team Alpha", "Team Beta"}


def test_stat_values_are_numeric(monkeypatch):
    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=1))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)

    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    result = matchups.get_matchups(None, LEAGUE_KEY)

    assert pd.api.types.is_float_dtype(result["Goals"])
    assert pd.api.types.is_float_dtype(result["Assists"])


def test_week_column_is_integer(monkeypatch):
    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=2))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)

    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    result = matchups.get_matchups(None, LEAGUE_KEY)

    assert pd.api.types.is_integer_dtype(result["week"])


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_returns_none_when_season_not_started(monkeypatch):
    """current_week < start_week means no weeks to fetch and an empty cache."""
    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=0, start_week=1))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)

    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    result = matchups.get_matchups(None, LEAGUE_KEY)

    assert result is None


def test_stat_categories_fetched_once_per_call(monkeypatch):
    """Expensive setup call (categories) happens once, not once per week."""
    categories_calls = []

    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=3))
    monkeypatch.setattr(client, "get_stat_categories",
                        lambda s, k: categories_calls.append(1) or STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    matchups.get_matchups(None, LEAGUE_KEY)

    assert len(categories_calls) == 1


def test_one_api_call_per_week(monkeypatch):
    """Bulk endpoint should be called once per week, not once per team."""
    api_calls = []

    def tracking_bulk(session, league_key, week, stat_categories):
        api_calls.append(week)
        return fake_all_teams_week_stats(session, league_key, week, stat_categories)

    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=3))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", tracking_bulk)

    matchups.get_matchups(None, LEAGUE_KEY)

    # 3 weeks = 3 API calls (not 3 weeks × 2 teams = 6)
    assert api_calls == [1, 2, 3]


# ---------------------------------------------------------------------------
# Prev-week re-fetch based on cache last_updated date
# ---------------------------------------------------------------------------

def test_prev_week_refetched_when_cache_updated_today(monkeypatch):
    """When the cache was last written today, the most recently completed week is re-fetched."""
    seed = pd.DataFrame([
        {"team_key": "nhl.l.99999.t.1", "team_name": "Team Alpha", "week": 4, "Goals": 8.0, "Assists": 12.0},
        {"team_key": "nhl.l.99999.t.2", "team_name": "Team Beta",  "week": 4, "Goals": 6.0, "Assists": 9.0},
    ])
    cache.write(LEAGUE_KEY, "matchups", seed)
    today = datetime.now(timezone.utc)
    monkeypatch.setattr(cache, "last_updated", lambda league, dtype: today)

    fetched_weeks = []

    def tracking_stats(session, league_key, week, stat_categories):
        fetched_weeks.append(week)
        return fake_all_teams_week_stats(session, league_key, week, stat_categories)

    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=5))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", tracking_stats)

    matchups.get_matchups(None, LEAGUE_KEY)

    assert 4 in fetched_weeks   # prev_week re-fetched because cache was written today
    assert 5 in fetched_weeks   # new current week also fetched


def test_prev_week_not_refetched_when_cache_updated_yesterday(monkeypatch):
    """When the cache was last written yesterday, the most recently completed week is not re-fetched."""
    seed = pd.DataFrame([
        {"team_key": "nhl.l.99999.t.1", "team_name": "Team Alpha", "week": 4, "Goals": 8.0, "Assists": 12.0},
        {"team_key": "nhl.l.99999.t.2", "team_name": "Team Beta",  "week": 4, "Goals": 6.0, "Assists": 9.0},
    ])
    cache.write(LEAGUE_KEY, "matchups", seed)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    monkeypatch.setattr(cache, "last_updated", lambda league, dtype: yesterday)

    fetched_weeks = []

    def tracking_stats(session, league_key, week, stat_categories):
        fetched_weeks.append(week)
        return fake_all_teams_week_stats(session, league_key, week, stat_categories)

    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=5))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", tracking_stats)

    matchups.get_matchups(None, LEAGUE_KEY)

    assert 4 not in fetched_weeks  # prev_week not re-fetched — cache was written yesterday
    assert 5 in fetched_weeks      # new current week still fetched


# ---------------------------------------------------------------------------
# Parquet stays clean across repeated same-day calls (ticket 038)
# ---------------------------------------------------------------------------

def read_parquet_from_disk(tmp_path) -> pd.DataFrame:
    """Read the matchups parquet straight off disk, bypassing get_matchups()."""
    return pd.read_parquet(tmp_path / LEAGUE_KEY / "matchups.parquet")


def test_repeated_same_day_calls_do_not_grow_parquet(tmp_path, monkeypatch):
    """
    The real same-day loop: after the first call the cache's last_updated is
    today, so every later call re-fetches prev_week and current_week. The
    on-disk row count must stay at the number of distinct (team_key, week)
    pairs instead of growing by the re-fetched rows each time.
    """
    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=5))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    matchups.get_matchups(None, LEAGUE_KEY)
    # 5 weeks × 2 teams
    assert len(read_parquet_from_disk(tmp_path)) == 10

    for _ in range(4):
        result = matchups.get_matchups(None, LEAGUE_KEY)
        on_disk = read_parquet_from_disk(tmp_path)
        assert len(on_disk) == 10
        assert len(result) == 10


def test_no_duplicate_rows_on_disk_after_repeated_calls(tmp_path, monkeypatch):
    """AC4: assert the file itself is clean, not merely the deduped read."""
    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=5))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    for _ in range(3):
        matchups.get_matchups(None, LEAGUE_KEY)

    on_disk = read_parquet_from_disk(tmp_path)
    assert not on_disk.duplicated(subset=["team_key", "week"]).any()
    assert sorted(on_disk["week"].unique()) == [1, 2, 3, 4, 5]


def test_current_week_updates_are_reflected_and_overwrite_cached_rows(tmp_path, monkeypatch):
    """
    AC2: current_week is still re-fetched every call (DECISIONS 2026-05-31) and
    the newer values win — in the returned frame and on disk.
    """
    goals = {"value": 1.0}

    def changing_stats(session, league_key, week, stat_categories):
        return [
            {
                "team_key": t["team_key"],
                "team_name": t["team_name"],
                "week": week,
                "games_played": week,
                "Goals": goals["value"],
                "Assists": 0.0,
            }
            for t in TEAMS
        ]

    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=2))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", changing_stats)

    first = matchups.get_matchups(None, LEAGUE_KEY)
    assert set(first[first["week"] == 2]["Goals"]) == {1.0}

    goals["value"] = 7.0
    second = matchups.get_matchups(None, LEAGUE_KEY)

    assert set(second[second["week"] == 2]["Goals"]) == {7.0}

    on_disk = read_parquet_from_disk(tmp_path)
    assert len(on_disk) == 4                                    # 2 weeks × 2 teams
    assert set(on_disk[on_disk["week"] == 2]["Goals"]) == {7.0}


def test_pre_existing_bloated_parquet_self_heals_on_next_write(tmp_path, monkeypatch):
    """A parquet already bloated by the pre-038 append behaviour is cleaned up."""
    bloated = pd.concat([
        pd.DataFrame([
            {"team_key": "nhl.l.99999.t.1", "team_name": "Team Alpha", "week": 1, "Goals": 2.0, "Assists": 3.0},
            {"team_key": "nhl.l.99999.t.2", "team_name": "Team Beta",  "week": 1, "Goals": 4.0, "Assists": 6.0},
        ])
    ] * 5, ignore_index=True)
    cache.write(LEAGUE_KEY, "matchups", bloated)
    assert len(read_parquet_from_disk(tmp_path)) == 10

    monkeypatch.setattr(client, "get_league_settings", lambda s, k: make_settings(current_week=2))
    monkeypatch.setattr(client, "get_stat_categories", lambda s, k: STAT_CATEGORIES)
    monkeypatch.setattr(client, "get_all_teams_week_stats", fake_all_teams_week_stats)

    result = matchups.get_matchups(None, LEAGUE_KEY)

    on_disk = read_parquet_from_disk(tmp_path)
    assert not on_disk.duplicated(subset=["team_key", "week"]).any()
    assert len(on_disk) == 4    # weeks 1 and 2 × 2 teams
    assert len(result) == 4
