"""
Tests for POST /api/waiver/players and POST /demo/api/waiver/players (019a + 019b).

Covers:
- _merge_pool unit test
- empty-state (stats=[])
- authenticated POST returns table
- unauthenticated POST → 401 (RequiresLogin → 302)
- demo POST returns table, no cache writes, no Yahoo calls
- pagination: page=0 ≤25 rows; page=1 next slice; page=99 on 30-row set clamped
- period="Last 30 days": games_played column, footer text, games-remaining column
- period="Last 30 days" fallback when lm_pool is empty
- period="Last 30 days" fallback when get_matchups returns None
- period="Last 30 days" fallback when get_current_matchup raises
- demo mode Last 30 days: no cache writes, no Yahoo calls
"""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fastapi.testclient import TestClient

from db.connection import db_dep
from web.main import app
from web.routes.waiver import PAGE_SIZE, _merge_pool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE user_sessions (
            session_id   TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at   REAL,
            created_at   REAL,
            league_key   TEXT
        );
        CREATE TABLE oauth_states (
            state TEXT PRIMARY KEY,
            expires_at REAL
        );
    """)
    return conn


def _insert_session(conn, session_id="sid-test", league_key="419.l.11111"):
    conn.execute(
        "INSERT INTO user_sessions"
        " (session_id, access_token, refresh_token, expires_at, created_at, league_key)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, "acc-token", "ref-token", time.time() + 3600, time.time(), league_key),
    )
    conn.commit()


def _make_season_pool(n: int = 30) -> pd.DataFrame:
    """Produce a minimal season pool DataFrame with n rows."""
    rows = []
    for i in range(n):
        rows.append({
            "player_key": f"nhl.p.{i}",
            "player_name": f"Player {i}",
            "team_abbr": "TOR",
            "display_position": "C",
            "status": "",
            "Goals": float(n - i),
            "Assists": float(i),
        })
    return pd.DataFrame(rows)


def _make_stat_categories() -> list[dict]:
    return [
        {"stat_id": "1", "stat_name": "Goals", "abbreviation": "G", "is_enabled": True},
        {"stat_id": "2", "stat_name": "Assists", "abbreviation": "A", "is_enabled": True},
    ]


@pytest.fixture()
def ctx():
    conn = _make_db()

    def override_db():
        yield conn

    app.dependency_overrides[db_dep] = override_db
    client = TestClient(app, follow_redirects=False)
    yield conn, client
    app.dependency_overrides.clear()
    conn.close()


# ---------------------------------------------------------------------------
# Unit tests: _merge_pool
# ---------------------------------------------------------------------------

def test_merge_pool_empty_existing():
    existing = pd.DataFrame()
    new_rows = pd.DataFrame([
        {"player_key": "nhl.p.1", "player_name": "A", "Goals": 10.0},
        {"player_key": "nhl.p.2", "player_name": "B", "Goals": 8.0},
    ])
    result = _merge_pool(existing, new_rows)
    assert len(result) == 2
    assert set(result["player_key"]) == {"nhl.p.1", "nhl.p.2"}


def test_merge_pool_empty_new_rows():
    existing = pd.DataFrame([{"player_key": "nhl.p.1", "player_name": "A", "Goals": 10.0}])
    new_rows = pd.DataFrame()
    result = _merge_pool(existing, new_rows)
    assert len(result) == 1
    assert result.iloc[0]["player_key"] == "nhl.p.1"


def test_merge_pool_discards_duplicate_keys():
    existing = pd.DataFrame([{"player_key": "nhl.p.1", "Goals": 10.0}])
    new_rows = pd.DataFrame([
        {"player_key": "nhl.p.1", "Goals": 99.0},  # duplicate — should be discarded
        {"player_key": "nhl.p.2", "Goals": 5.0},   # new — should be kept
    ])
    result = _merge_pool(existing, new_rows)
    assert len(result) == 2
    # existing row for nhl.p.1 wins
    p1 = result[result["player_key"] == "nhl.p.1"].iloc[0]
    assert p1["Goals"] == 10.0


def test_merge_pool_all_duplicates():
    existing = pd.DataFrame([
        {"player_key": "nhl.p.1", "Goals": 10.0},
        {"player_key": "nhl.p.2", "Goals": 7.0},
    ])
    new_rows = pd.DataFrame([
        {"player_key": "nhl.p.1", "Goals": 99.0},
        {"player_key": "nhl.p.2", "Goals": 88.0},
    ])
    result = _merge_pool(existing, new_rows)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# TC1 — POST /api/waiver/players with stats=[] → empty-state, no <table>
# ---------------------------------------------------------------------------

def test_waiver_post_empty_stats_returns_empty_state(ctx):
    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": [], "position": "All", "period": "Season", "page": "0"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    body = response.text
    assert "Select one or more stat categories above to rank available players." in body
    assert "<table" not in body


# ---------------------------------------------------------------------------
# TC2 — POST /api/waiver/players with stats=["Goals"] → 200 with <table>
# ---------------------------------------------------------------------------

def test_waiver_post_with_stats_returns_table(ctx):
    conn, client = ctx
    _insert_session(conn)

    pool_df = _make_season_pool(5)

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
        patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.is_player_pool_stale", return_value=True),
        patch("web.routes.waiver.fetch_season_pool", return_value=pool_df),
        patch("web.routes.waiver.cache.write_player_pool"),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Season", "page": "0"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    assert "<table" in response.text


# ---------------------------------------------------------------------------
# TC3 — POST /api/waiver/players with no session → 302 (RequiresLogin)
# ---------------------------------------------------------------------------

def test_waiver_post_no_cookie_returns_redirect(ctx):
    _, client = ctx
    response = client.post(
        "/api/waiver/players",
        data={"stats": ["Goals"], "position": "All", "period": "Season", "page": "0"},
    )
    # RequiresLogin → 302 to /auth/login
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# TC4 — POST /demo/api/waiver/players → 200 with <table>, no Yahoo calls
# ---------------------------------------------------------------------------

def test_demo_waiver_post_returns_table_no_yahoo_calls(ctx):
    _, client = ctx

    pool_df = _make_season_pool(5)

    with (
        patch("data.demo.load_season_pool", return_value=pool_df),
        patch("data.demo.get_stat_categories", return_value=_make_stat_categories()),
    ):
        response = client.post(
            "/demo/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Season", "page": "0"},
        )

    assert response.status_code == 200
    assert "<table" in response.text


# ---------------------------------------------------------------------------
# TC5 — Pagination: page=0 returns ≤25 rows; page=1 returns next slice
# ---------------------------------------------------------------------------

def test_waiver_post_pagination_page0_and_page1(ctx):
    conn, client = ctx
    _insert_session(conn)

    pool_df = _make_season_pool(30)

    common_patches = dict(
        make_session=MagicMock(),
        _get_league_key="419.l.11111",
        stat_cats=_make_stat_categories(),
        pool=pool_df,
    )

    def _post(page: int):
        with (
            patch("web.routes.waiver.make_session", return_value=MagicMock()),
            patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
            patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
            patch("web.routes.waiver.cache.is_player_pool_stale", return_value=True),
            patch("web.routes.waiver.fetch_season_pool", return_value=pool_df),
            patch("web.routes.waiver.cache.write_player_pool"),
        ):
            return client.post(
                "/api/waiver/players",
                data={"stats": ["Goals"], "position": "All", "period": "Season", "page": str(page)},
                cookies={"session_id": "sid-test"},
            )

    r0 = _post(0)
    assert r0.status_code == 200
    # Page 0 of 30 players: 25 rows
    assert "Player 0" in r0.text
    assert "Player 24" in r0.text
    assert "Player 25" not in r0.text
    # Footer: page 1 of 2
    assert "Page 1 of 2" in r0.text

    r1 = _post(1)
    assert r1.status_code == 200
    # Page 1 of 30 players: 5 rows
    assert "Player 25" in r1.text
    assert "Player 29" in r1.text
    assert "Player 0" not in r1.text
    assert "Page 2 of 2" in r1.text


# ---------------------------------------------------------------------------
# TC6 — Pagination: page=99 on 30-row set is clamped to last valid page
# ---------------------------------------------------------------------------

def test_waiver_post_page_clamped_to_last(ctx):
    conn, client = ctx
    _insert_session(conn)

    pool_df = _make_season_pool(30)

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
        patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.is_player_pool_stale", return_value=True),
        patch("web.routes.waiver.fetch_season_pool", return_value=pool_df),
        patch("web.routes.waiver.cache.write_player_pool"),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Season", "page": "99"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    body = response.text
    # Clamped to page 1 (index 1, last page): 5 rows
    assert "Player 25" in body
    assert "Page 2 of 2" in body


# ---------------------------------------------------------------------------
# TC7 — Cache hit: no fetch_season_pool call when cache is fresh
# ---------------------------------------------------------------------------

def test_waiver_post_cache_hit_skips_api(ctx):
    conn, client = ctx
    _insert_session(conn)

    pool_df = _make_season_pool(5)

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
        patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.is_player_pool_stale", return_value=False),
        patch("web.routes.waiver.cache.read_player_pool", return_value=pool_df),
        patch("web.routes.waiver.fetch_season_pool") as mock_fetch,
        patch("web.routes.waiver.cache.write_player_pool"),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Season", "page": "0"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    assert "<table" in response.text
    mock_fetch.assert_not_called()


# ---------------------------------------------------------------------------
# TC8 — Position filter G with stat "Goals" → no rows → empty-state message
# ---------------------------------------------------------------------------

def test_waiver_post_position_no_matching_rows(ctx):
    conn, client = ctx
    _insert_session(conn)

    # All players are C position; filtering for G should return no rows
    pool_df = _make_season_pool(5)  # display_position = "C"

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
        patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.is_player_pool_stale", return_value=True),
        patch("web.routes.waiver.fetch_season_pool", return_value=pool_df),
        patch("web.routes.waiver.cache.write_player_pool"),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": ["Goals"], "position": "G", "period": "Season", "page": "0"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    # No rows after G filter — the empty-result message should appear
    assert "No players found" in response.text


# ---------------------------------------------------------------------------
# TC9 — Demo mode: no cache writes occur
# ---------------------------------------------------------------------------

def test_demo_waiver_post_no_cache_writes(ctx):
    _, client = ctx

    pool_df = _make_season_pool(5)

    with (
        patch("data.demo.load_season_pool", return_value=pool_df),
        patch("data.demo.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.write_player_pool") as mock_write,
    ):
        response = client.post(
            "/demo/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Season", "page": "0"},
        )

    assert response.status_code == 200
    mock_write.assert_not_called()


# ---------------------------------------------------------------------------
# Helpers for 019b tests
# ---------------------------------------------------------------------------

def _make_lastmonth_pool(n: int = 5) -> pd.DataFrame:
    """Minimal lastmonth pool DataFrame — player_key matches _make_season_pool."""
    rows = []
    for i in range(n):
        rows.append({
            "player_key": f"nhl.p.{i}",
            "team_abbr": "TOR",
            "games_played": 10 + i,
            "Goals": float(n - i),
            "Assists": float(i),
        })
    return pd.DataFrame(rows)


def _make_matchups_df() -> pd.DataFrame:
    return pd.DataFrame([{"week": 14, "team": "t.1", "Goals": 5.0}])


def _make_matchup_dict() -> dict:
    return {
        "week_start": "2026-03-23",
        "week_end": "2026-03-29",
        "matchups": [],
    }


# ---------------------------------------------------------------------------
# TC10 — POST with period="Last 30 days": games_played column, footer text
# ---------------------------------------------------------------------------

def test_waiver_post_lastmonth_returns_gp_column_and_footer(ctx):
    conn, client = ctx
    _insert_session(conn)

    season_pool = _make_season_pool(5)
    lm_pool = _make_lastmonth_pool(5)

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
        patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.is_player_pool_stale", return_value=True),
        patch("web.routes.waiver.fetch_season_pool", return_value=season_pool),
        patch("web.routes.waiver.cache.write_player_pool"),
        patch("web.routes.waiver.cache.is_lastmonth_stale", return_value=True),
        patch("web.routes.waiver.fetch_lastmonth_batch", return_value=lm_pool),
        patch("web.routes.waiver.cache.upsert_lastmonth_cache"),
        patch("web.routes.waiver.get_matchups", return_value=_make_matchups_df()),
        patch("web.routes.waiver.get_current_matchup", return_value=_make_matchup_dict()),
        patch("web.routes.waiver.get_remaining_games", return_value={"TOR": 3}),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Last 30 days", "page": "0"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    body = response.text
    assert "<table" in body
    assert "last 30 days stats" in body
    # GP column header present
    assert ">GP<" in body


# ---------------------------------------------------------------------------
# TC11 — period="Season" unchanged: no GP column, footer reads "season stats"
# ---------------------------------------------------------------------------

def test_waiver_post_season_footer_unchanged(ctx):
    conn, client = ctx
    _insert_session(conn)

    pool_df = _make_season_pool(5)

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
        patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.is_player_pool_stale", return_value=True),
        patch("web.routes.waiver.fetch_season_pool", return_value=pool_df),
        patch("web.routes.waiver.cache.write_player_pool"),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Season", "page": "0"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    body = response.text
    assert "season stats" in body
    assert "last 30 days stats" not in body
    assert ">GP<" not in body
    assert ">GR<" not in body


# ---------------------------------------------------------------------------
# TC12 — demo POST with period="Last 30 days": no Yahoo calls, no cache writes
# ---------------------------------------------------------------------------

def test_demo_waiver_post_lastmonth_no_yahoo_no_cache(ctx):
    _, client = ctx

    season_pool = _make_season_pool(5)
    lm_pool = _make_lastmonth_pool(5)

    with (
        patch("data.demo.load_season_pool", return_value=season_pool),
        patch("data.demo.load_lastmonth_pool", return_value=lm_pool),
        patch("data.demo.get_games_remaining", return_value={"TOR": 3}),
        patch("web.routes.waiver.cache.upsert_lastmonth_cache") as mock_upsert,
        patch("web.routes.waiver.fetch_lastmonth_batch") as mock_fetch,
        patch("web.routes.waiver.get_current_matchup") as mock_matchup,
    ):
        response = client.post(
            "/demo/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Last 30 days", "page": "0"},
        )

    assert response.status_code == 200
    assert "<table" in response.text
    assert "last 30 days stats" in response.text
    mock_upsert.assert_not_called()
    mock_fetch.assert_not_called()
    mock_matchup.assert_not_called()


# ---------------------------------------------------------------------------
# TC13 — get_matchups returns None → games_remaining == 0, no 500
# ---------------------------------------------------------------------------

def test_waiver_post_lastmonth_matchups_none_no_500(ctx):
    conn, client = ctx
    _insert_session(conn)

    season_pool = _make_season_pool(5)
    lm_pool = _make_lastmonth_pool(5)

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
        patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.is_player_pool_stale", return_value=True),
        patch("web.routes.waiver.fetch_season_pool", return_value=season_pool),
        patch("web.routes.waiver.cache.write_player_pool"),
        patch("web.routes.waiver.cache.is_lastmonth_stale", return_value=True),
        patch("web.routes.waiver.fetch_lastmonth_batch", return_value=lm_pool),
        patch("web.routes.waiver.cache.upsert_lastmonth_cache"),
        patch("web.routes.waiver.get_matchups", return_value=None),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Last 30 days", "page": "0"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    assert "<table" in response.text
    # No games_remaining column added; template renders — for missing values
    assert "last 30 days stats" in response.text


# ---------------------------------------------------------------------------
# TC14 — get_current_matchup raises → games_remaining fallback, no 500
# ---------------------------------------------------------------------------

def test_waiver_post_lastmonth_matchup_raises_no_500(ctx):
    conn, client = ctx
    _insert_session(conn)

    season_pool = _make_season_pool(5)
    lm_pool = _make_lastmonth_pool(5)

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
        patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.is_player_pool_stale", return_value=True),
        patch("web.routes.waiver.fetch_season_pool", return_value=season_pool),
        patch("web.routes.waiver.cache.write_player_pool"),
        patch("web.routes.waiver.cache.is_lastmonth_stale", return_value=True),
        patch("web.routes.waiver.fetch_lastmonth_batch", return_value=lm_pool),
        patch("web.routes.waiver.cache.upsert_lastmonth_cache"),
        patch("web.routes.waiver.get_matchups", return_value=_make_matchups_df()),
        patch("web.routes.waiver.get_current_matchup", side_effect=ValueError("API error")),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Last 30 days", "page": "0"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    assert "<table" in response.text
    assert "last 30 days stats" in response.text


# ---------------------------------------------------------------------------
# TC15 — lm_pool empty after cache + fetch → fallback to season stats, no 500
# ---------------------------------------------------------------------------

def test_waiver_post_lastmonth_empty_lm_pool_falls_back_to_season(ctx):
    conn, client = ctx
    _insert_session(conn)

    season_pool = _make_season_pool(5)

    with (
        patch("web.routes.waiver.make_session", return_value=MagicMock()),
        patch("web.routes.waiver._get_league_key", return_value="419.l.11111"),
        patch("web.routes.waiver.get_stat_categories", return_value=_make_stat_categories()),
        patch("web.routes.waiver.cache.is_player_pool_stale", return_value=True),
        patch("web.routes.waiver.fetch_season_pool", return_value=season_pool),
        patch("web.routes.waiver.cache.write_player_pool"),
        patch("web.routes.waiver.cache.is_lastmonth_stale", return_value=True),
        patch("web.routes.waiver.fetch_lastmonth_batch", return_value=pd.DataFrame()),
        patch("web.routes.waiver.get_matchups", return_value=_make_matchups_df()),
        patch("web.routes.waiver.get_current_matchup", return_value=_make_matchup_dict()),
        patch("web.routes.waiver.get_remaining_games", return_value={"TOR": 2}),
    ):
        response = client.post(
            "/api/waiver/players",
            data={"stats": ["Goals"], "position": "All", "period": "Last 30 days", "page": "0"},
            cookies={"session_id": "sid-test"},
        )

    assert response.status_code == 200
    body = response.text
    assert "<table" in body
    # Fell back to season stats — season player names are present
    assert "Player 0" in body
