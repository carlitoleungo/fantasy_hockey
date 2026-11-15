"""Week Projection page display (2026-11 redesign): CLOSE tags, verdict blocks, number
formatting, the week line, and the roster tabs. Numbers are covered elsewhere; these
check what the page shows. Rendered through the demo route, which shares
`_render_matchup` with the live route."""

from __future__ import annotations

import re
from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from analysis.projection import CLOSE_MARGIN, compare_projections, lead_margin
from tests.test_demo_projection_routes import MY_KEY, _make_context, _make_pair
from web.main import app
from web.routes.projection import _fmt_stat, _week_dates

CATS = [
    {"stat_name": "Goals", "is_enabled": True},
    {"stat_name": "Goals Against Average", "is_enabled": True},
]


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


def _render(client, ctx=None, pair=None) -> str:
    with (
        patch("data.demo.get_projection_context", return_value=ctx or _make_context()),
        patch("data.demo.get_projection_pair_data", return_value=pair or _make_pair()),
    ):
        resp = client.get(f"/demo/projection/matchup?team_key={MY_KEY}")
    assert resp.status_code == 200
    return resp.text


def _row(body: str, category: str) -> str:
    m = re.search(r'<tr data-category="' + re.escape(category) + r'">(.*?)</tr>', body, re.S)
    assert m, category
    return m.group(1)


# --- lead_margin / close -------------------------------------------------------------

def test_lead_margin_is_relative_to_the_larger_total():
    assert lead_margin(10.0, 9.0) == pytest.approx(0.1)
    assert lead_margin(9.0, 10.0) == pytest.approx(0.1)
    assert lead_margin(0.0, 0.0) == 0.0
    assert lead_margin(-2.0, 2.0) == pytest.approx(2.0)  # +/- can go negative


def test_compare_projections_flags_close_but_not_ties():
    rows = compare_projections(
        {"Goals": 10.0, "Goals Against Average": 2.50},
        {"Goals": 9.5, "Goals Against Average": 2.50},
        CATS,
    )
    goals, gaa = rows
    assert goals["winner"] == "team_a" and goals["close"] is True
    assert goals["margin"] == pytest.approx(0.05)
    assert gaa["winner"] == "Tie" and gaa["close"] is False


def test_compare_projections_wide_margin_is_not_close():
    (goals, _) = compare_projections({"Goals": 10.0}, {"Goals": 5.0}, CATS)
    assert goals["margin"] > CLOSE_MARGIN and goals["close"] is False


# --- formatting and week line ------------------------------------------------------

@pytest.mark.parametrize("name,value,expected", [
    ("Goals", 3.14159, "3.1"),
    ("Plus/Minus", -0.04, "0.0"),            # never "-0.0"
    ("Plus/Minus", -0.4, "-0.4"),
    ("Goals Against Average", 2.456, "2.46"),
    ("Save Percentage", 0.9184, "0.918"),
    ("SV%", 0.9184, "0.918"),
])
def test_fmt_stat(name, value, expected):
    assert _fmt_stat(name, value) == expected


def test_week_dates_mid_week_counts_today():
    d = _week_dates("2026-11-09", "2026-11-15", today=date(2026, 11, 11))
    assert d == {"week_range": "Nov 9 – Nov 15", "days_left": 5, "today_label": "Wed"}


def test_week_dates_outside_the_week_has_no_days_left():
    assert _week_dates("2026-01-05", "2026-01-11", today=date(2026, 11, 11))["days_left"] is None


# --- rendered fragment ---------------------------------------------------------------

def test_verdict_blocks_show_counts_and_team_names(client):
    body = _render(client)
    # Alpha (mine) out-projects Bravo in both categories.
    verdict = body[body.index('class="pj-verdict"'):body.index('id="pj-categories"')]
    assert re.search(r'pj-me">\s*<span class="pj-n">2<', verdict)
    assert re.search(r'pj-tie">\s*<span class="pj-n">0<', verdict)
    assert re.search(r'pj-opp">\s*<span class="pj-n">0<', verdict)
    assert "My wins" in verdict and "Their wins" in verdict and "Zellmannator" in verdict


def test_close_category_gets_close_tag_and_wide_one_does_not(client):
    ctx = _make_context()
    # Bank 10 goals each: Goals 11.5 vs 10.6 (close); Assists 2.4 vs 0.8 (not close).
    for row in ctx["live_stats_rows"]:
        row["Goals"] = 10.0
    body = _render(client, ctx=ctx)
    assert "CLOSE" in _row(body, "Goals")
    assert "CLOSE" not in _row(body, "Assists")


def test_category_cells_show_abbreviation_and_full_name(client):
    row = _row(_render(client), "Goals")
    assert ">G<" in row and ">Goals<" in row


def test_roster_tabs_hold_both_teams_my_team_first(client):
    body = _render(client)
    me = body.index('data-team="me"')
    opp = body.index('data-team="opp"')
    assert me < body.index("A. Skater", me) < opp < body.index("B. Skater", opp)
    # The opponent panel starts hidden until Alpine shows it.
    assert re.search(r'data-team="opp"[^>]*x-cloak', body)


def test_player_with_no_games_left_is_dimmed(client):
    pair = _make_pair()
    pair["games_remaining"] = {"STL": 0, "TOR": 2}
    body = _render(client, pair=pair)
    mine = body[body.index('data-team="me"'):body.index('data-team="opp"')]
    theirs = body[body.index('data-team="opp"'):]
    assert 'class="pj-idle"' in mine
    assert "pj-idle" not in theirs
