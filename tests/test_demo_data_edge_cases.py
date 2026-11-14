"""
The committed demo snapshot covers the edge cases the UI has to handle, so they can be
checked on /demo/* pages without a Yahoo key (see scripts/add_demo_edge_cases.py).

Reads the real files in demo/data/; no mocks, no network.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from data import demo
from web.main import app

client = TestClient(app)


def _lastmonth_with_meta():
    season = demo.load_season_pool()
    meta = season[["player_key", "player_name", "display_position", "status"]]
    return meta.merge(demo.load_lastmonth_pool(), on="player_key", how="inner")


def test_lastmonth_pool_has_defence_and_goalies():
    positions = set(_lastmonth_with_meta()["display_position"])
    assert {"D", "G"} <= positions


def test_lastmonth_goalies_have_goalie_stats():
    goalies = _lastmonth_with_meta().query("display_position == 'G'")
    assert goalies["Goals Against Average"].notna().all()
    assert goalies["Goals"].isna().all()
    assert (goalies["games_played"] == 1).any()  # small-sample case


def test_every_status_code_appears_in_last30_views():
    statuses = set(_lastmonth_with_meta()["status"])
    assert {"", "DTD", "O", "IR", "IR-LT", "IR-NR", "NA", "SUSP", "GTD"} <= statuses


def test_games_remaining_covers_all_teams_and_extremes():
    games = demo.get_games_remaining()
    teams = set(demo.load_season_pool()["team_abbr"])
    assert teams <= set(games)
    assert {0, 4} <= set(games.values())


def test_demo_waiver_last30_renders_defence_goalies_and_accented_name():
    response = client.post(
        "/demo/api/waiver/players",
        data={"positions": ["D", "G"], "stats": ["Points", "Saves"], "period": "Last 30 days"},
    )
    assert response.status_code == 200
    body = response.text
    assert "Joey Daccord" in body
    assert "Sam Malinski" in body
    assert "Charles-Édouard D" in body

