"""
Tests for GET /projection/matchup (ticket 030 — Week Projection matchup fragment).

Uses an in-memory SQLite DB injected via dependency override on db_dep.
All data-layer functions are mocked so no live Yahoo/NHL API calls are made.
"""

from __future__ import annotations

import re
import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient

from db.connection import db_dep
from web.main import app


# ---------------------------------------------------------------------------
# Fixtures / helpers
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


LEAGUE_KEY = "419.l.11111"
T1 = "419.l.11111.t.1"  # Alpha (my default)
T2 = "419.l.11111.t.2"  # Beta (opponent)
T3 = "419.l.11111.t.3"  # Gamma (bye — no matchup)

TEAMS = [
    {"team_key": T1, "team_id": "1", "team_name": "Alpha", "manager_name": "Ann"},
    {"team_key": T2, "team_id": "2", "team_name": "Beta", "manager_name": "Bob"},
    {"team_key": T3, "team_id": "3", "team_name": "Gamma", "manager_name": "Cal"},
]

SETTINGS = {"current_week": 14, "start_week": 1, "end_week": 24}

STAT_CATEGORIES = [
    {"stat_id": "1", "stat_name": "Goals", "abbreviation": "G", "stat_group": "offense", "is_enabled": True},
    {"stat_id": "23", "stat_name": "Goals Against Average", "abbreviation": "GAA", "stat_group": "goaltending", "is_enabled": True},
]

SCOREBOARD = {
    "week_start": "2026-03-23",
    "week_end": "2026-03-29",
    "matchups": [
        {"team_a_key": T1, "team_b_key": T2},
    ],
}

LIVE_STATS = [
    {"team_key": T1, "team_name": "Alpha", "week": 14, "games_played": 3,
     "Goals": 5.0, "Goals Against Average": 0.0},
    {"team_key": T2, "team_name": "Beta", "week": 14, "games_played": 3,
     "Goals": 5.0, "Goals Against Average": 0.0},
]

MY_ROSTER = [
    {"player_key": "p.mine", "player_name": "My Skater", "team_abbr": "EDM",
     "display_position": "C", "roster_slot": "C"},
]
OPP_ROSTER = [
    {"player_key": "p.opp", "player_name": "Opp Skater", "team_abbr": "BOS",
     "display_position": "LW", "roster_slot": "LW"},
]

LASTMONTH = {
    "p.mine": {"Goals": 20.0, "Goals Against Average": 2.50, "games_played": 10},
    "p.opp": {"Goals": 5.0, "Goals Against Average": 3.00, "games_played": 10},
}

GAMES_REMAINING = {"EDM": 3, "BOS": 2}


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


def _patched(
    client,
    query,
    *,
    teams=TEAMS,
    scoreboard=SCOREBOARD,
    remaining_mock=None,
    teams_stats_mock=None,
    rosters=None,
    lastmonth=LASTMONTH,
):
    remaining_mock = remaining_mock or MagicMock(return_value=GAMES_REMAINING)
    teams_stats_mock = teams_stats_mock or MagicMock(return_value=LIVE_STATS)
    rosters = rosters or [MY_ROSTER, OPP_ROSTER]
    with (
        patch("web.routes.projection.make_session", return_value=MagicMock()),
        patch("web.routes.projection.get_settings_and_categories",
              return_value=(SETTINGS, STAT_CATEGORIES)),
        patch("web.routes.projection.get_teams", return_value=teams),
        patch("web.routes.projection.get_all_teams_week_stats", teams_stats_mock),
        patch("web.routes.projection.scoreboard_module.get_current_matchup",
              return_value=scoreboard),
        patch("web.routes.projection.roster_module.get_team_roster",
              side_effect=rosters),
        patch("web.routes.projection.players_module.get_players_lastmonth_stats",
              return_value=lastmonth),
        patch("web.routes.projection.schedule_module.get_remaining_games",
              remaining_mock),
    ):
        return client.get(f"/projection/matchup{query}", cookies={"session_id": "sid-test"})


# ---------------------------------------------------------------------------
# AC1 — 200, context line, three tally cards
# ---------------------------------------------------------------------------

def test_matchup_context_line_and_tally_cards(ctx):
    conn, client = ctx
    _insert_session(conn)
    resp = _patched(client, f"?team_key={T1}")
    assert resp.status_code == 200
    body = resp.text
    assert "base.html" not in body
    assert "<html" not in body.lower()  # bare fragment, no full page
    assert "Week 14 vs Beta · 2026-03-23 – 2026-03-29" in body
    # Three tally cards: my wins, ties, opp wins
    assert "Projected Wins" in body
    assert body.count("Projected Wins") == 2  # my team + opponent
    assert "Tied" in body


# ---------------------------------------------------------------------------
# AC2 — category comparison table with per-cell winner highlighting
# ---------------------------------------------------------------------------

def test_matchup_category_table_winner_highlight(ctx):
    conn, client = ctx
    _insert_session(conn)
    resp = _patched(client, f"?team_key={T1}")
    body = resp.text
    assert "Goals" in body
    assert "Goals Against Average" in body
    # My team wins both categories -> highlight class applied on my column
    assert "bg-green-100" in body
    # My projected Goals = 5 + 20/10*3 = 11.0, opp = 5 + 5/10*2 = 6.0
    assert "11.0" in body
    assert "6.0" in body


# ---------------------------------------------------------------------------
# AC3 — per-team roster breakdown for both teams
# ---------------------------------------------------------------------------

def test_matchup_roster_breakdown_both_teams(ctx):
    conn, client = ctx
    _insert_session(conn)
    resp = _patched(client, f"?team_key={T1}")
    body = resp.text
    assert "Roster Breakdown" in body
    assert "My Skater" in body
    assert "Opp Skater" in body
    # Remaining games shown
    assert ">3<" in body  # EDM remaining
    assert ">2<" in body  # BOS remaining


# ---------------------------------------------------------------------------
# AC4 — bye week -> no matchup message, no table
# ---------------------------------------------------------------------------

def test_matchup_bye_week_message(ctx):
    conn, client = ctx
    _insert_session(conn)
    resp = _patched(client, f"?team_key={T3}")
    assert resp.status_code == 200
    body = resp.text
    assert "no matchup this week" in body.lower()
    assert "Roster Breakdown" not in body


# ---------------------------------------------------------------------------
# AC5 — rate stats 2dp, counting stats 1dp
# ---------------------------------------------------------------------------

def test_matchup_rate_vs_counting_formatting(ctx):
    conn, client = ctx
    _insert_session(conn)
    resp = _patched(client, f"?team_key={T1}")
    body = resp.text
    # Rate stat GAA weighted to my player's rate 2.50 -> 2dp
    assert "2.50" in body
    # Counting stat Goals projected as x.1f (never summed as rate)
    assert "11.0" in body
    # Roster breakdown: my Goals contribution 20/10*3 = 6.0 (1dp)
    assert "6.0" in body


# ---------------------------------------------------------------------------
# Bulk fetch — team stats come from a single teams/stats call
# ---------------------------------------------------------------------------

def test_matchup_uses_single_bulk_team_stats_call(ctx):
    conn, client = ctx
    _insert_session(conn)
    teams_stats_mock = MagicMock(return_value=LIVE_STATS)
    _patched(client, f"?team_key={T1}", teams_stats_mock=teams_stats_mock)
    assert teams_stats_mock.call_count == 1


# ---------------------------------------------------------------------------
# Session guards
# ---------------------------------------------------------------------------

def test_matchup_no_league_redirects_home(ctx):
    conn, client = ctx
    conn.execute(
        "INSERT INTO user_sessions"
        " (session_id, access_token, refresh_token, expires_at, created_at, league_key)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        ("sid-test", "acc", "ref", time.time() + 3600, time.time(), None),
    )
    conn.commit()
    resp = client.get(f"/projection/matchup?team_key={T1}", cookies={"session_id": "sid-test"})
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


def test_matchup_no_cookie_redirects_login(ctx):
    _, client = ctx
    resp = client.get(f"/projection/matchup?team_key={T1}")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


def test_matchup_missing_team_redirects_to_shell(ctx):
    conn, client = ctx
    _insert_session(conn)
    resp = client.get("/projection/matchup", cookies={"session_id": "sid-test"})
    assert resp.status_code == 302
    assert resp.headers["location"] == "/projection"


def test_matchup_my_team_alone_is_not_a_selection(ctx):
    """The removed `my_team` alias is treated as no team selected."""
    conn, client = ctx
    _insert_session(conn)
    resp = client.get(f"/projection/matchup?my_team={T1}", cookies={"session_id": "sid-test"})
    assert resp.status_code == 302
    assert resp.headers["location"] == "/projection"


# ---------------------------------------------------------------------------
# Ticket 034 — roster-breakdown readability
# ---------------------------------------------------------------------------

MIXED_ROSTER = [
    {"player_key": "p.skater", "player_name": "Connor McDavid", "team_abbr": "EDM",
     "display_position": "C", "roster_slot": "C"},
    {"player_key": "p.goalie", "player_name": "Jake Allen", "team_abbr": "EDM",
     "display_position": "G", "roster_slot": "G"},
]
MIXED_LASTMONTH = {
    "p.skater": {"Goals": 20.0, "games_played": 10},
    "p.goalie": {"Goals Against Average": 2.75, "games_played": 10},
    "p.opp": {"Goals": 5.0, "games_played": 10},
}


def _breakdown_sections(body: str) -> list[tuple[str, str]]:
    """Return [(section_label, table_html)] for every roster-breakdown table."""
    tail = body.split("Roster Breakdown", 1)[1]
    return re.findall(
        r'<p[^>]*>(Skaters|Goalies)</p>\s*<div[^>]*>\s*(<table.*?</table>)',
        tail,
        re.S,
    )


def _mixed_response(client):
    return _patched(
        client,
        f"?team_key={T1}",
        rosters=[MIXED_ROSTER, OPP_ROSTER],
        lastmonth=MIXED_LASTMONTH,
    )


def test_breakdown_splits_skaters_and_goalies(ctx):
    """AC1 — a mixed roster renders a Skaters table and a Goalies table."""
    conn, client = ctx
    _insert_session(conn)
    resp = _mixed_response(client)
    assert resp.status_code == 200
    sections = _breakdown_sections(resp.text)
    labels = [label for label, _ in sections]
    # My team: skaters + goalies. Opponent (skater only): skaters only.
    assert labels == ["Skaters", "Goalies", "Skaters"]


def _headers(table_html: str) -> list[str]:
    return re.findall(r"<th(?:\s[^>]*)?>\s*(.*?)\s*</th>", table_html, re.S)


def test_skater_section_has_no_goalie_columns(ctx):
    """AC1 — no `0.00` GAA cell on a skater row; the column isn't there at all."""
    conn, client = ctx
    _insert_session(conn)
    _, skaters = _breakdown_sections(_mixed_response(client).text)[0]
    assert _headers(skaters) == ["Player", "GR", "G"]
    assert "GAA" not in skaters
    assert "0.00" not in skaters
    # The skater's own projected Goals still renders (20/10 * 3 = 6.0).
    assert ">6.0<" in re.sub(r"\s+", "", skaters)


def test_goalie_section_has_no_skater_columns(ctx):
    """AC1 (symmetric) — the goalie row carries only goaltending columns."""
    conn, client = ctx
    _insert_session(conn)
    _, goalies = _breakdown_sections(_mixed_response(client).text)[1]
    assert _headers(goalies) == ["Player", "GR", "GAA"]
    # GAA is a rate stat -> the lastmonth rate rendered at 2dp, not a 0.0 skater cell.
    assert "2.75" in goalies
    assert ">0.0<" not in re.sub(r"\s+", "", goalies)


def test_breakdown_headers_use_abbreviations(ctx):
    """AC2 — headers show the Yahoo abbreviation, not the full stat name."""
    conn, client = ctx
    _insert_session(conn)
    body = _mixed_response(client).text
    headers = [h for _, table in _breakdown_sections(body) for h in _headers(table)]
    assert "G" in headers
    assert "GAA" in headers
    assert "Goals" not in headers
    assert "Goals Against Average" not in headers
    # Full name is still available as the header tooltip.
    assert 'title="Goals Against Average"' in body


def test_breakdown_abbreviates_player_names_with_full_name_title(ctx):
    """AC3 — `Connor McDavid` renders as `C. McDavid` with the full name on hover."""
    conn, client = ctx
    _insert_session(conn)
    sections = _breakdown_sections(_mixed_response(client).text)
    skaters = sections[0][1]
    goalies = sections[1][1]
    assert "C. McDavid" in re.sub(r"\s+", " ", skaters)
    assert ">Connor McDavid<" not in skaters
    assert 'title="Connor McDavid"' in skaters
    assert "J. Allen" in re.sub(r"\s+", " ", goalies)
    assert 'title="Jake Allen"' in goalies


def test_breakdown_values_unchanged_from_ticket_030(ctx):
    """AC5 — presentation-only: the tally cards, comparison table, and a
    spot-checked player value are the same numbers ticket 030 rendered."""
    conn, client = ctx
    _insert_session(conn)
    body = _patched(client, f"?team_key={T1}").text
    # Comparison table: my Goals 5 + 20/10*3 = 11.0, opp 5 + 5/10*2 = 6.0
    assert "11.0" in body
    assert "6.0" in body
    # Rate stat still 2dp in the comparison table
    assert "2.50" in body
    # Tally cards untouched
    assert body.count("Projected Wins") == 2
    assert "Tied" in body
