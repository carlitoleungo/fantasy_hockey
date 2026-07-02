"""
QA tests for ticket 027 — demo mode overview routes.

Covers:
  - GET /demo/overview returns 200 without a session cookie (AC1, AC4)
  - Shell HTMX points at the demo fragment /demo/overview/table (AC2)
  - GET /demo/overview/table?week=N returns a bare fragment, not a full page (AC3)
  - GET /demo/overview with no cookie returns 200, not 302 (AC4)
  - Live Yahoo path (make_session / get_matchups) is never touched (AC5)

The demo routes lazily `from data import demo as demo_module` then call
`demo_module.get_matchups()`, so patching `data.demo.get_matchups` swaps the
data source — the same technique as test_demo_head_to_head_routes.py.
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
    """2 teams × 2 weeks fixture (minimal valid demo shape)."""
    rows = [
        {"team_key": "t1", "team_name": "Alpha", "week": 1, "games_played": 7,
         "Goals": 10.0},
        {"team_key": "t2", "team_name": "Beta", "week": 1, "games_played": 7,
         "Goals": 7.0},
        {"team_key": "t1", "team_name": "Alpha", "week": 2, "games_played": 7,
         "Goals": 8.0},
        {"team_key": "t2", "team_name": "Beta", "week": 2, "games_played": 7,
         "Goals": 5.0},
    ]
    return pd.DataFrame(rows)


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


# ---------------------------------------------------------------------------
# AC1 / AC4 — GET /demo/overview returns 200 with no session cookie
# ---------------------------------------------------------------------------

def test_demo_overview_shell_returns_200(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# AC4 — no session cookie returns 200, not a 302 redirect to login
# ---------------------------------------------------------------------------

def test_demo_overview_no_auth_required(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview")
    # TestClient sends no cookies here; the public route must not redirect.
    assert response.status_code == 200
    assert response.status_code != 302


# ---------------------------------------------------------------------------
# AC2 — shell HTMX points at the demo fragment, not the authenticated one
# ---------------------------------------------------------------------------

def test_demo_overview_table_url_targets_demo(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview")

    body = response.text
    # The template renders table_url as hx-get="{{ table_url }}".
    assert 'hx-get="/demo/overview/table"' in body
    # Must NOT reference the authenticated fragment. The hx-get=" anchor keeps
    # this from matching the demo path as a substring.
    assert 'hx-get="/overview/table"' not in body


# ---------------------------------------------------------------------------
# AC3 — GET /demo/overview/table?week=N returns a bare fragment
# ---------------------------------------------------------------------------

def test_demo_overview_table_returns_fragment(client):
    df = _make_matchups_df()
    with patch("data.demo.get_matchups", return_value=df):
        response = client.get("/demo/overview/table?week=2")

    assert response.status_code == 200
    body = response.text
    # Fragment, not a full page: body starts with <div (possibly after
    # leading whitespace from the {% if %} line), no <html>, no <!DOCTYPE>.
    assert body.lstrip().startswith("<div")
    assert "<html" not in body
    assert "<!DOCTYPE" not in body


# ---------------------------------------------------------------------------
# AC5 — no live Yahoo path is touched on the shell
# ---------------------------------------------------------------------------

def test_demo_overview_no_yahoo_calls(client):
    df = _make_matchups_df()
    with (
        patch("data.demo.get_matchups", return_value=df),
        patch("web.routes.overview.make_session") as mock_make_session,
        patch("web.routes.overview.get_matchups") as mock_live_matchups,
    ):
        response = client.get("/demo/overview")

    assert response.status_code == 200
    mock_make_session.assert_not_called()
    mock_live_matchups.assert_not_called()


# ---------------------------------------------------------------------------
# AC5 — no live Yahoo path is touched on the table fragment
# ---------------------------------------------------------------------------

def test_demo_overview_table_no_yahoo_calls(client):
    df = _make_matchups_df()
    with (
        patch("data.demo.get_matchups", return_value=df),
        patch("web.routes.overview.make_session") as mock_make_session,
        patch("web.routes.overview.get_matchups") as mock_live_matchups,
    ):
        response = client.get("/demo/overview/table?week=1")

    assert response.status_code == 200
    mock_make_session.assert_not_called()
    mock_live_matchups.assert_not_called()
