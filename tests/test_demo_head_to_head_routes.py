"""
QA tests for ticket 021 — demo mode head-to-head routes.

Covers:
  - GET /demo/overview/head-to-head returns 200 without auth
  - Two team dropdowns populated from demo data
  - Week-range selectors populated
  - Initial comparison table rendered in shell
  - hx-get points to /demo/overview/head-to-head/table
  - GET /demo/overview/head-to-head/table fragment: 200, no full HTML, table + tally
  - Not-enough-data guard renders empty-state message
  - No Yahoo API calls made (no make_session, no get_matchups from live)
  - from_week > to_week swapped correctly in demo fragment
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from fastapi.testclient import TestClient

from web.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_matchups_df() -> pd.DataFrame:
    """2 teams × 2 weeks × 2 stats fixture (minimal valid demo shape)."""
    rows = [
        {"team_key": "t1", "team_name": "Alpha", "week": 1, "games_played": 7,
         "Goals": 10.0, "Assists": 5.0},
        {"team_key": "t2", "team_name": "Beta", "week": 1, "games_played": 7,
         "Goals": 7.0, "Assists": 9.0},
        {"team_key": "t1", "team_name": "Alpha", "week": 2, "games_played": 7,
         "Goals": 8.0, "Assists": 8.0},
        {"team_key": "t2", "team_name": "Beta", "week": 2, "games_played": 7,
         "Goals": 5.0, "Assists": 4.0},
    ]
    return pd.DataFrame(rows)


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


# ---------------------------------------------------------------------------
# TC-D01 — GET /demo/overview/head-to-head returns 200 without auth
# ---------------------------------------------------------------------------

def test_demo_head_to_head_returns_200_no_auth(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview/head-to-head")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# TC-D02 — Shell has team dropdowns populated from demo data
# ---------------------------------------------------------------------------

def test_demo_head_to_head_team_dropdowns_populated(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview/head-to-head")

    body = response.text
    # Both team names appear in option elements
    assert 'value="Alpha"' in body
    assert 'value="Beta"' in body
    # Both team dropdown selects present
    assert 'name="team_a"' in body
    assert 'name="team_b"' in body


# ---------------------------------------------------------------------------
# TC-D03 — Shell has week-range selectors populated
# ---------------------------------------------------------------------------

def test_demo_head_to_head_week_selectors_populated(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview/head-to-head")

    body = response.text
    assert 'name="from_week"' in body
    assert 'name="to_week"' in body
    assert "Week 1" in body
    assert "Week 2" in body


# ---------------------------------------------------------------------------
# TC-D04 — Shell renders initial comparison table
# ---------------------------------------------------------------------------

def test_demo_head_to_head_initial_table_rendered(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview/head-to-head")

    body = response.text
    assert "<table" in body
    assert "wins" in body


# ---------------------------------------------------------------------------
# TC-D05 — hx-get targets the demo fragment URL, not the authenticated one
# ---------------------------------------------------------------------------

def test_demo_head_to_head_htmx_targets_demo_url(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview/head-to-head")

    body = response.text
    assert 'hx-get="/demo/overview/head-to-head/table"' in body
    # Must NOT reference the authenticated fragment
    assert 'hx-get="/overview/head-to-head/table"' not in body


# ---------------------------------------------------------------------------
# TC-D06 — Fragment endpoint returns 200 with partial HTML (no <html> tag)
# ---------------------------------------------------------------------------

def test_demo_head_to_head_table_returns_fragment(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get(
            "/demo/overview/head-to-head/table"
            "?team_a=Alpha&team_b=Beta&from_week=1&to_week=2"
        )

    assert response.status_code == 200
    body = response.text
    assert "<html" not in body
    assert "<!DOCTYPE" not in body
    assert "<table" in body


# ---------------------------------------------------------------------------
# TC-D07 — Fragment contains tally (wins / ties) line
# ---------------------------------------------------------------------------

def test_demo_head_to_head_table_tally_present(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get(
            "/demo/overview/head-to-head/table"
            "?team_a=Alpha&team_b=Beta&from_week=1&to_week=2"
        )

    body = response.text
    assert "wins" in body
    assert "ties" in body


# ---------------------------------------------------------------------------
# TC-D08 — Fragment contains winner highlighting (bg-green-100)
# ---------------------------------------------------------------------------

def test_demo_head_to_head_table_has_winner_cells(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get(
            "/demo/overview/head-to-head/table"
            "?team_a=Alpha&team_b=Beta&from_week=1&to_week=2"
        )

    assert "bg-green-100" in response.text


# ---------------------------------------------------------------------------
# TC-D09 — not_enough_data guard: <2 teams renders empty-state, no crash
# ---------------------------------------------------------------------------

def test_demo_head_to_head_not_enough_data_guard(client):
    one_team = pd.DataFrame([{
        "team_key": "t1", "team_name": "Lonely", "week": 1,
        "games_played": 7, "Goals": 5.0,
    }])
    with patch("data.demo.get_matchups", return_value=one_team):
        response = client.get("/demo/overview/head-to-head")

    assert response.status_code == 200
    assert "Not enough team data" in response.text


# ---------------------------------------------------------------------------
# TC-D10 — No Yahoo API calls on demo shell (make_session never called)
# ---------------------------------------------------------------------------

def test_demo_head_to_head_no_yahoo_calls(client):
    df = _make_matchups_df()
    with (
        patch("data.demo.get_matchups", return_value=df) as mock_demo,
        patch("web.routes.overview.make_session") as mock_make_session,
        patch("web.routes.overview.get_matchups") as mock_live_matchups,
    ):
        response = client.get("/demo/overview/head-to-head")

    assert response.status_code == 200
    mock_make_session.assert_not_called()
    mock_live_matchups.assert_not_called()


# ---------------------------------------------------------------------------
# TC-D11 — No Yahoo API calls on demo fragment (make_session never called)
# ---------------------------------------------------------------------------

def test_demo_head_to_head_table_no_yahoo_calls(client):
    df = _make_matchups_df()
    with (
        patch("data.demo.get_matchups", return_value=df),
        patch("web.routes.overview.make_session") as mock_make_session,
        patch("web.routes.overview.get_matchups") as mock_live_matchups,
    ):
        response = client.get(
            "/demo/overview/head-to-head/table"
            "?team_a=Alpha&team_b=Beta&from_week=1&to_week=2"
        )

    assert response.status_code == 200
    mock_make_session.assert_not_called()
    mock_live_matchups.assert_not_called()


# ---------------------------------------------------------------------------
# TC-D12 — from_week > to_week is swapped in demo fragment (same as live)
# ---------------------------------------------------------------------------

def test_demo_head_to_head_table_swaps_inverted_week_range(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        r_normal = client.get(
            "/demo/overview/head-to-head/table"
            "?team_a=Alpha&team_b=Beta&from_week=1&to_week=2"
        )
        r_inverted = client.get(
            "/demo/overview/head-to-head/table"
            "?team_a=Alpha&team_b=Beta&from_week=2&to_week=1"
        )

    assert r_normal.status_code == 200
    assert r_inverted.status_code == 200
    assert r_normal.text == r_inverted.text


# ---------------------------------------------------------------------------
# TC-D13 — Authenticated /overview/head-to-head still redirects to login
# ---------------------------------------------------------------------------

def test_live_head_to_head_still_requires_auth(client):
    response = client.get("/overview/head-to-head")
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# TC-D14 — Ticket 025: demo /overview "Compare two teams" link points at the
#          demo head-to-head route, not the authenticated one
# ---------------------------------------------------------------------------

def test_demo_overview_compare_link_targets_demo_route(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview")

    body = response.text
    assert 'href="/demo/overview/head-to-head"' in body
    assert 'href="/overview/head-to-head"' not in body


# ---------------------------------------------------------------------------
# TC-D15 — Ticket 025: demo /demo/overview/head-to-head "Back to Leaderboard"
#          link points at the demo overview route, not the authenticated one
# ---------------------------------------------------------------------------

def test_demo_head_to_head_back_link_targets_demo_route(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview/head-to-head")

    body = response.text
    # Scope to the "Back to Leaderboard" anchor — base.html's nav also links
    # to /overview, so a bare href="/overview" substring is ambiguous.
    demo_back_link = (
        'href="/demo/overview" class="text-sm text-gray-500 hover:text-gray-700">'
        "&larr; Back to Leaderboard"
    )
    auth_back_link = (
        'href="/overview" class="text-sm text-gray-500 hover:text-gray-700">'
        "&larr; Back to Leaderboard"
    )
    assert demo_back_link in body
    assert auth_back_link not in body
