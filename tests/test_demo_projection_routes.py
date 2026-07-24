"""
QA tests for ticket 031 — Week Projection demo parity.

Covers:
  - GET /demo/projection returns 200 without a session cookie (AC1)
  - Shell renders "Demo League", a team selector, and a matchup container whose
    HTMX points at /demo/projection/matchup (AC1)
  - GET /demo/projection/matchup?team_key=<key> returns 200 with no auth and a
    bare fragment carrying tally cards, category table, roster breakdowns (AC2)
  - The container auto-loads the default team against the demo fragment URL and
    the fragment shows real Week 14 projected numbers (AC3)
  - /projection and /projection/matchup still require auth when logged out (AC4)
  - The live Yahoo path (make_session) is never touched on the demo routes

The demo routes lazily `from data import demo as demo_module` then call the
demo accessors, so patching `data.demo.*` swaps the data source — the same
technique as test_demo_overview_routes.py (ticket 027).
"""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from fastapi.testclient import TestClient

from web.main import app


# ---------------------------------------------------------------------------
# Fixtures — a minimal two-team demo snapshot matching the committed shapes.
# ---------------------------------------------------------------------------

MY_KEY = "465.l.8977.t.8"
OPP_KEY = "465.l.8977.t.5"
MY_NAME = "AHO-V-O Crew"
OPP_NAME = "Zellmannator"


def _make_context() -> dict:
    return {
        "current_week": 14,
        "stat_categories": [
            {"stat_id": "1", "stat_name": "Goals", "abbreviation": "G",
             "stat_group": "offense", "is_enabled": True, "lower_is_better": False},
            {"stat_id": "2", "stat_name": "Assists", "abbreviation": "A",
             "stat_group": "offense", "is_enabled": True, "lower_is_better": False},
        ],
        "teams": [
            {"team_key": MY_KEY, "team_name": MY_NAME},
            {"team_key": OPP_KEY, "team_name": OPP_NAME},
        ],
        "live_stats_rows": [
            {"team_key": MY_KEY, "team_name": MY_NAME, "week": 14,
             "games_played": 0, "Goals": 0.0, "Assists": 0.0},
            {"team_key": OPP_KEY, "team_name": OPP_NAME, "week": 14,
             "games_played": 0, "Goals": 0.0, "Assists": 0.0},
        ],
        "scoreboard": {
            "week_start": "2026-01-05",
            "week_end": "2026-01-11",
            "matchups": [{"team_a_key": MY_KEY, "team_b_key": OPP_KEY}],
        },
    }


def _make_pair() -> dict:
    return {
        "my_team_key": MY_KEY,
        "opp_team_key": OPP_KEY,
        "my_roster": [
            {"player_key": "465.p.1", "player_name": "Alpha Skater",
             "team_abbr": "STL", "display_position": "C", "roster_slot": "C"},
        ],
        "opp_roster": [
            {"player_key": "465.p.2", "player_name": "Bravo Skater",
             "team_abbr": "TOR", "display_position": "LW", "roster_slot": "LW"},
        ],
        "lastmonth_stats": {
            "465.p.1": {"games_played": 10, "Goals": 5.0, "Assists": 8.0},
            "465.p.2": {"games_played": 10, "Goals": 3.0, "Assists": 4.0},
        },
        "games_remaining": {"STL": 3, "TOR": 2},
    }


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


# ---------------------------------------------------------------------------
# AC1 — GET /demo/projection returns 200 with no session cookie
# ---------------------------------------------------------------------------

def test_demo_projection_shell_returns_200_no_auth(client):
    with patch("data.demo.get_projection_context", return_value=_make_context()):
        response = client.get("/demo/projection")
    # TestClient sends no cookies; the public route must not redirect.
    assert response.status_code == 200


def test_demo_projection_shell_renders_demo_shell(client):
    with patch("data.demo.get_projection_context", return_value=_make_context()):
        response = client.get("/demo/projection")
    body = response.text
    assert response.status_code == 200
    # League label
    assert "Demo League" in body
    # Team selector with one option per demo team
    assert "<select" in body
    assert 'name="team_key"' in body
    assert MY_NAME in body
    assert OPP_NAME in body
    # Matchup container present and its HTMX points at the demo fragment
    assert 'id="projection-matchup"' in body
    assert 'hx-get="/demo/projection/matchup"' in body
    # Must not reference the authenticated fragment.
    assert 'hx-get="/projection/matchup"' not in body


# ---------------------------------------------------------------------------
# AC3 — container auto-loads the default team against the demo fragment URL
# ---------------------------------------------------------------------------

def test_demo_projection_shell_autoloads_default_team(client):
    with patch("data.demo.get_projection_context", return_value=_make_context()):
        response = client.get("/demo/projection")
    body = response.text
    assert 'hx-trigger="load"' in body
    assert f'hx-get="/demo/projection/matchup?team_key={MY_KEY}"' in body
    assert f'value="{MY_KEY}" selected' in body


# ---------------------------------------------------------------------------
# AC2 — GET /demo/projection/matchup?team_key=<key> returns a bare fragment with
#        tally cards, category table, and roster breakdowns
# ---------------------------------------------------------------------------

def test_demo_projection_matchup_returns_fragment(client):
    with (
        patch("data.demo.get_projection_context", return_value=_make_context()),
        patch("data.demo.get_projection_pair_data", return_value=_make_pair()),
    ):
        response = client.get(f"/demo/projection/matchup?team_key={MY_KEY}")
    assert response.status_code == 200
    body = response.text
    # Bare fragment, not a full page.
    assert "<html" not in body
    assert "<!DOCTYPE" not in body
    # Tally cards
    assert "Projected Wins" in body
    # Category comparison table headers
    assert f"{MY_NAME} (Proj)" in body
    assert f"{OPP_NAME} (Proj)" in body
    # Roster breakdown section + both players present
    assert "Roster Breakdown" in body
    assert "Alpha Skater" in body
    assert "Bravo Skater" in body


def test_demo_projection_matchup_no_selection_redirects(client):
    with (
        patch("data.demo.get_projection_context", return_value=_make_context()),
        patch("data.demo.get_projection_pair_data", return_value=_make_pair()),
    ):
        response = client.get("/demo/projection/matchup")
    assert response.status_code == 302
    assert response.headers["location"] == "/demo/projection"


def test_demo_projection_matchup_my_team_alone_redirects(client):
    """The removed `my_team` alias (no `team_key`) is treated as no selection."""
    with (
        patch("data.demo.get_projection_context", return_value=_make_context()),
        patch("data.demo.get_projection_pair_data", return_value=_make_pair()),
    ):
        response = client.get(f"/demo/projection/matchup?my_team={MY_KEY}")
    assert response.status_code == 302
    assert response.headers["location"] == "/demo/projection"


# ---------------------------------------------------------------------------
# AC3 — fragment shows real projected numbers computed from the demo snapshot
# ---------------------------------------------------------------------------

def test_demo_projection_matchup_shows_projected_numbers(client):
    with (
        patch("data.demo.get_projection_context", return_value=_make_context()),
        patch("data.demo.get_projection_pair_data", return_value=_make_pair()),
    ):
        response = client.get(f"/demo/projection/matchup?team_key={MY_KEY}")
    body = response.text
    # Alpha Skater: Goals 5.0/10 gp * 3 games left = 1.5 projected goals.
    assert "1.5" in body
    # A projected win count of 0 for a shut-out category would still render,
    # so assert the tally cards carry the win/tie counts (all three present).
    assert body.count("Projected Wins") == 2  # my + opponent card
    assert "Categories" in body  # the "Tied" card


def test_demo_projection_matchup_swaps_orderings(client):
    """Selecting the opponent side swaps the roster breakdowns (both orderings)."""
    with (
        patch("data.demo.get_projection_context", return_value=_make_context()),
        patch("data.demo.get_projection_pair_data", return_value=_make_pair()),
    ):
        default = client.get(f"/demo/projection/matchup?team_key={MY_KEY}").text
        swapped = client.get(f"/demo/projection/matchup?team_key={OPP_KEY}").text
    # Default: my roster (Alpha Skater) renders in the first breakdown table.
    assert default.index("Alpha Skater") < default.index("Bravo Skater")
    # Swapped: the opponent's roster (Bravo Skater) is now the first table.
    assert swapped.index("Bravo Skater") < swapped.index("Alpha Skater")


# ---------------------------------------------------------------------------
# No live Yahoo path is touched on the demo routes
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Ticket 034 AC4 — the demo fragment renders the improved breakdown too
# ---------------------------------------------------------------------------

def _make_context_with_goalie_category() -> dict:
    ctx = _make_context()
    ctx["stat_categories"].append(
        {"stat_id": "23", "stat_name": "Goals Against Average", "abbreviation": "GAA",
         "stat_group": "goaltending", "is_enabled": True}
    )
    for row in ctx["live_stats_rows"]:
        row["Goals Against Average"] = 0.0
    return ctx


def _make_pair_with_goalie() -> dict:
    pair = _make_pair()
    pair["my_roster"].append(
        {"player_key": "465.p.3", "player_name": "Charlie Goalie",
         "team_abbr": "STL", "display_position": "G", "roster_slot": "G"}
    )
    pair["lastmonth_stats"]["465.p.3"] = {
        "games_played": 10, "Goals Against Average": 2.75
    }
    return pair


def test_demo_projection_matchup_splits_skaters_and_goalies(client):
    """AC1/AC4 — the demo render separates goalie stats from skater stats."""
    with (
        patch("data.demo.get_projection_context",
              return_value=_make_context_with_goalie_category()),
        patch("data.demo.get_projection_pair_data",
              return_value=_make_pair_with_goalie()),
    ):
        response = client.get(f"/demo/projection/matchup?team_key={MY_KEY}")
    assert response.status_code == 200
    body = response.text
    assert ">Skaters<" in body
    assert ">Goalies<" in body
    tables = re.findall(
        r'<p[^>]*>(Skaters|Goalies)</p>\s*<div[^>]*>\s*(<table.*?</table>)', body, re.S
    )
    labels = [label for label, _ in tables]
    assert labels == ["Skaters", "Goalies", "Skaters"]
    my_skaters = tables[0][1]
    my_goalies = tables[1][1]
    # Skater table carries no GAA column and therefore no 0.00 filler cell.
    assert "GAA" not in my_skaters
    assert "0.00" not in my_skaters
    # Goalie table carries only the goaltending column.
    assert "GAA" in my_goalies
    assert "2.75" in my_goalies


def test_demo_projection_matchup_abbreviates_headers_and_names(client):
    """AC2/AC3/AC4 — abbreviated headers and player names in the demo render."""
    with (
        patch("data.demo.get_projection_context",
              return_value=_make_context_with_goalie_category()),
        patch("data.demo.get_projection_pair_data",
              return_value=_make_pair_with_goalie()),
    ):
        response = client.get(f"/demo/projection/matchup?team_key={MY_KEY}")
    body = response.text
    tables = re.findall(
        r'<p[^>]*>(Skaters|Goalies)</p>\s*<div[^>]*>\s*(<table.*?</table>)', body, re.S
    )
    headers = [
        h
        for _, table in tables
        for h in re.findall(r"<th(?:\s[^>]*)?>\s*(.*?)\s*</th>", table, re.S)
    ]
    assert "G" in headers and "A" in headers and "GAA" in headers
    assert "Goals" not in headers and "Assists" not in headers
    # Player names abbreviated, full name kept as the hover title.
    squashed = re.sub(r"\s+", " ", body)
    assert "A. Skater" in squashed
    assert 'title="Alpha Skater"' in body
    assert "C. Goalie" in squashed
    assert 'title="Charlie Goalie"' in body


def test_demo_projection_no_yahoo_calls(client):
    with (
        patch("data.demo.get_projection_context", return_value=_make_context()),
        patch("data.demo.get_projection_pair_data", return_value=_make_pair()),
        patch("web.routes.projection.make_session") as mock_make_session,
    ):
        shell = client.get("/demo/projection")
        frag = client.get(f"/demo/projection/matchup?team_key={MY_KEY}")
    assert shell.status_code == 200
    assert frag.status_code == 200
    mock_make_session.assert_not_called()


# ---------------------------------------------------------------------------
# AC4 — authenticated routes still require auth (unchanged)
# ---------------------------------------------------------------------------

def test_authenticated_projection_still_requires_auth(client):
    response = client.get("/projection")
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


def test_authenticated_projection_matchup_still_requires_auth(client):
    response = client.get(f"/projection/matchup?team_key={MY_KEY}")
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"
