"""
Leaderboard and Head-to-Head display (Overview redesign, docs/design-system.md):
rank shading levels, number formatting, and the demo pages' new layout.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from analysis.team_scores import rank_shade_levels
from web.main import app


# ---------------------------------------------------------------------------
# rank_shade_levels
# ---------------------------------------------------------------------------

def test_leader_gets_4_and_bottom_gets_0_in_10_team_league():
    df = pd.DataFrame({"Goals": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]})
    levels = rank_shade_levels(df)["Goals"].tolist()
    assert levels == [4, 3, 3, 2, 2, 2, 1, 1, 0, 0]


def test_leader_is_bold_in_small_league():
    """A percentile cut would leave an 8-team leader at level 3."""
    df = pd.DataFrame({"Goals": [8, 7, 6, 5, 4, 3, 2, 1]})
    assert rank_shade_levels(df)["Goals"].iloc[0] == 4


def test_lower_is_better_flips():
    df = pd.DataFrame({"Goals Against Average": [2.0, 3.0, 4.0, 5.0]})
    levels = rank_shade_levels(df)["Goals Against Average"].tolist()
    assert levels[0] == 4
    assert levels[-1] == 0


def test_all_tied_column_gets_no_shading():
    """A week with no games yet: every team at 0 must not look like the best."""
    df = pd.DataFrame({"Goals": [0.0] * 6, "Assists": [3, 2, 1, 0, 0, 0]})
    out = rank_shade_levels(df)
    assert out["Goals"].tolist() == [0] * 6
    assert out["Assists"].iloc[0] == 4


def test_tied_leaders_all_get_4():
    df = pd.DataFrame({"Shutouts": [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]})
    assert rank_shade_levels(df)["Shutouts"].tolist()[:3] == [4, 4, 4]


def test_tied_block_below_leaders_uses_average_rank():
    """Nine teams tied on 0 shutouts sit at average rank 8 of 12 (level 1), not rank 4 (level 3)."""
    df = pd.DataFrame({"Shutouts": [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]})
    assert set(rank_shade_levels(df)["Shutouts"].tolist()[3:]) == {1}


def test_missing_values_get_0():
    df = pd.DataFrame({"Goals": [5.0, float("nan"), 3.0, 1.0]})
    out = rank_shade_levels(df)["Goals"].tolist()
    assert out[1] == 0
    assert out[0] == 4


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _df() -> pd.DataFrame:
    rows = []
    data = {
        1: {
            "Alpha": {"Goals": 10.0, "Plus/Minus": 4.0, "Goals Against Average": 2.104},
            "Beta": {"Goals": 7.0, "Plus/Minus": -3.0, "Goals Against Average": 3.5},
            "Gamma": {"Goals": 5.0, "Plus/Minus": 0.0, "Goals Against Average": 2.9},
        },
        2: {
            "Alpha": {"Goals": 6.0, "Plus/Minus": 1.0, "Goals Against Average": 2.5},
            "Beta": {"Goals": 9.0, "Plus/Minus": 2.0, "Goals Against Average": 2.0},
            "Gamma": {"Goals": 4.0, "Plus/Minus": -1.0, "Goals Against Average": 3.1},
        },
    }
    for week, teams in data.items():
        for i, (name, stats) in enumerate(teams.items()):
            rows.append({"team_key": f"t{i}", "team_name": name, "week": week,
                         "games_played": 3, **stats})
    return pd.DataFrame(rows)


@pytest.fixture()
def client():
    return TestClient(app)


def test_leaderboard_formats_and_labels(client):
    with patch("data.demo.get_matchups", return_value=_df()):
        body = client.get("/demo/overview/table?week=1").text
    assert '<td class="s4">+4</td>' in body          # plus/minus carries its sign
    assert '<td class="s4">2.10</td>' in body        # GAA: two decimals, lowest is best
    assert 'title="Goals Against Average">GAA<' in body
    assert "GAA: lower is better" in body


def test_leaderboard_has_phone_grid_with_every_stat(client):
    with patch("data.demo.get_matchups", return_value=_df()):
        body = client.get("/demo/overview/table?week=1").text
    assert 'style="--n: 3"' in body
    assert body.count('class="pg-row"') == 3


def test_overview_page_follows_system_theme_and_has_week_stepper(client):
    with patch("data.demo.get_matchups", return_value=_df()):
        body = client.get("/demo/overview").text
    assert 'data-theme="light"' not in body
    assert 'aria-label="Previous week"' in body
    assert 'aria-label="Next week"' in body
    assert 'href="/demo/overview/head-to-head" class="btn"' in body


def test_head_to_head_averages_and_arrows(client):
    with patch("data.demo.get_matchups", return_value=_df()):
        body = client.get(
            "/demo/overview/head-to-head/table?team_a=Alpha&team_b=Beta&from_week=1&to_week=2"
        ).text
    # Goals: Alpha 8.00 vs Beta 8.00 → tie; Plus/Minus: Alpha +2.50 beats Beta -0.50
    assert '<td class="win">+2.50</td>' in body
    assert '<td class="l lose">-0.50</td>' in body
    assert 'aria-label="Alpha wins">◀' in body
    assert "weeks 1–2" in body


def test_head_to_head_page_follows_system_theme(client):
    with patch("data.demo.get_matchups", return_value=_df()):
        body = client.get("/demo/overview/head-to-head").text
    assert 'data-theme="light"' not in body
    assert 'class="select' in body
