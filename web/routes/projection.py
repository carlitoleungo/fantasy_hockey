from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from analysis.matchup_sim import tally
from analysis.projection import _is_rate_stat, compare_projections, project_team_stats
from analysis.team_scores import lower_is_better_from_categories
from auth.oauth import make_session
from data import players as players_module
from data import roster as roster_module
from data import schedule as schedule_module
from data import scoreboard as scoreboard_module
from data.client import (
    get_all_teams_week_stats,
    get_settings_and_categories,
    get_teams,
)
from data.leagues import get_user_hockey_leagues
from db.connection import db_dep
from web.middleware.session import CurrentUser, require_user
from web.routes.common import _get_league_key
from web.templates import templates

router = APIRouter()
public_router = APIRouter()


@router.get("/projection")
def projection_shell(
    request: Request,
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    league_key = _get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)
    session = make_session(current_user.access_token)
    leagues = get_user_hockey_leagues(session)
    selected_league_name = next(
        (lg["league_name"] for lg in leagues if lg["league_key"] == league_key),
        None,
    )
    teams = get_teams(session, league_key)
    return templates.TemplateResponse(
        request,
        "projection/index.html",
        {
            "teams": teams,
            "selected_league_name": selected_league_name,
            "matchup_url": "/projection/matchup",
        },
    )


# ---------------------------------------------------------------------------
# Matchup fragment
# ---------------------------------------------------------------------------

def _player_breakdown(roster, lastmonth_stats, games_remaining, enabled_stats):
    """Per-player projected contribution for one team.

    Counting stat → lastmonth / games_played * remaining_games.
    Rate stat (GAA, SV%) → the lastmonth rate directly (never summed).
    Ports pages/04_week_projection.py:504-527.
    """
    rows = []
    for player in roster:
        remaining = games_remaining.get(player["team_abbr"], 0)
        lm = lastmonth_stats.get(player["player_key"], {})
        gp = lm.get("games_played", 0)
        stats = {}
        for stat in enabled_stats:
            if _is_rate_stat(stat):
                stats[stat] = lm.get(stat, 0.0)
            else:
                stats[stat] = (lm.get(stat, 0.0) / gp * remaining) if gp > 0 else 0.0
        rows.append({
            "player_name": player["player_name"],
            "position": player.get("display_position", ""),
            "team_abbr": player.get("team_abbr", ""),
            "games_left": remaining,
            "stats": stats,
        })
    rows.sort(key=lambda r: r["games_left"], reverse=True)
    return rows


def _matchup_impl(request: Request, session, league_key: str, my_team_key: str):
    settings, stat_categories = get_settings_and_categories(session, league_key)
    current_week = settings["current_week"]
    enabled_stats = [c["stat_name"] for c in stat_categories if c["is_enabled"]]

    teams = get_teams(session, league_key)
    scoreboard_data = scoreboard_module.get_current_matchup(
        session, league_key, current_week
    )

    # Resolve opponent from scoreboard matchup pairings (04_week_projection:352-369)
    opponent_key = None
    for m in scoreboard_data["matchups"]:
        if m["team_a_key"] == my_team_key:
            opponent_key = m["team_b_key"]
            break
        elif m["team_b_key"] == my_team_key:
            opponent_key = m["team_a_key"]
            break

    my_team_name = next(
        (t["team_name"] for t in teams if t["team_key"] == my_team_key),
        my_team_key,
    )

    if opponent_key is None:
        return templates.TemplateResponse(
            request,
            "projection/_matchup.html",
            {
                "has_matchup": False,
                "current_week": current_week,
                "my_team_name": my_team_name,
            },
        )

    opponent_name = next(
        (t["team_name"] for t in teams if t["team_key"] == opponent_key),
        opponent_key,
    )

    # Live week-to-date for all teams in one bulk call (never per-team).
    live_stats_rows = get_all_teams_week_stats(
        session, league_key, current_week, stat_categories
    )
    live_by_key = {row["team_key"]: row for row in live_stats_rows}

    # Today's date excludes players dropped mid-week (04_week_projection:396-398).
    today_str = date.today().isoformat()
    my_roster = roster_module.get_team_roster(session, my_team_key, date=today_str)
    opp_roster = roster_module.get_team_roster(session, opponent_key, date=today_str)

    all_player_keys = [p["player_key"] for p in my_roster + opp_roster]
    all_abbrs = list({p["team_abbr"] for p in my_roster + opp_roster if p["team_abbr"]})

    # Bulk last-30-day stats for both rosters at once (batches of 25 internally).
    lastmonth_stats = players_module.get_players_lastmonth_stats(
        session, league_key, all_player_keys
    )

    week_end = date.fromisoformat(scoreboard_data["week_end"])
    from_date = max(date.today(), date.fromisoformat(scoreboard_data["week_start"]))
    games_remaining = schedule_module.get_remaining_games(all_abbrs, from_date, week_end)

    my_current = {s: float(live_by_key.get(my_team_key, {}).get(s, 0.0)) for s in enabled_stats}
    opp_current = {s: float(live_by_key.get(opponent_key, {}).get(s, 0.0)) for s in enabled_stats}

    return _render_matchup(
        request,
        current_week=current_week,
        week_start=scoreboard_data["week_start"],
        week_end=scoreboard_data["week_end"],
        stat_categories=stat_categories,
        enabled_stats=enabled_stats,
        my_team_name=my_team_name,
        opponent_name=opponent_name,
        my_current=my_current,
        opp_current=opp_current,
        my_roster=my_roster,
        opp_roster=opp_roster,
        lastmonth_stats=lastmonth_stats,
        games_remaining=games_remaining,
    )


def _render_matchup(
    request: Request,
    *,
    current_week,
    week_start,
    week_end,
    stat_categories,
    enabled_stats,
    my_team_name,
    opponent_name,
    my_current,
    opp_current,
    my_roster,
    opp_roster,
    lastmonth_stats,
    games_remaining,
):
    """Project both teams, tally categories, and render the matchup fragment.

    Shared by the live (`_matchup_impl`) and demo compute paths — both assemble
    the same resolved inputs (rosters, last-30 stats, games remaining, live
    week-to-date) and hand them here for identical compute + render.
    """
    my_projected = project_team_stats(
        my_current, my_roster, lastmonth_stats, games_remaining, stat_categories
    )
    opp_projected = project_team_stats(
        opp_current, opp_roster, lastmonth_stats, games_remaining, stat_categories
    )

    comparison = compare_projections(
        my_projected, opp_projected, stat_categories,
        lower_is_better=lower_is_better_from_categories(stat_categories),
    )

    # Tally: map "team_a"/"team_b"/"Tie" to names (04_week_projection:457-469).
    sim_rows = [
        {
            "category": r["category"],
            "team_a": r["team_a"],
            "team_b": r["team_b"],
            "winner": my_team_name if r["winner"] == "team_a"
                      else (opponent_name if r["winner"] == "team_b" else "Tie"),
        }
        for r in comparison
    ]
    counts = tally(pd.DataFrame(sim_rows), my_team_name, opponent_name)

    my_breakdown = _player_breakdown(my_roster, lastmonth_stats, games_remaining, enabled_stats)
    opp_breakdown = _player_breakdown(opp_roster, lastmonth_stats, games_remaining, enabled_stats)

    return templates.TemplateResponse(
        request,
        "projection/_matchup.html",
        {
            "has_matchup": True,
            "current_week": current_week,
            "week_start": week_start,
            "week_end": week_end,
            "my_team_name": my_team_name,
            "opponent_name": opponent_name,
            "my_wins": counts[my_team_name],
            "ties": counts["Tie"],
            "opp_wins": counts[opponent_name],
            "comparison": comparison,
            "enabled_stats": enabled_stats,
            "my_breakdown": my_breakdown,
            "opp_breakdown": opp_breakdown,
            "is_rate_stat": _is_rate_stat,
        },
    )


@router.get("/projection/matchup")
def projection_matchup(
    request: Request,
    team_key: str | None = None,
    my_team: str | None = None,
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    league_key = _get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)
    selected = team_key or my_team
    if not selected:
        return RedirectResponse("/projection", status_code=302)
    session = make_session(current_user.access_token)
    return _matchup_impl(request, session, league_key, selected)


# ---------------------------------------------------------------------------
# Demo routes (no auth required)
# ---------------------------------------------------------------------------

@public_router.get("/demo/projection")
def demo_projection_shell(request: Request):
    from data import demo as demo_module

    ctx = demo_module.get_projection_context()
    return templates.TemplateResponse(
        request,
        "projection/index.html",
        {
            "teams": ctx.get("teams", []),
            "selected_league_name": "Demo League",
            "matchup_url": "/demo/projection/matchup",
        },
    )


@public_router.get("/demo/projection/matchup")
def demo_projection_matchup(
    request: Request,
    team_key: str | None = None,
    my_team: str | None = None,
):
    from data import demo as demo_module

    selected = team_key or my_team
    if not selected:
        return RedirectResponse("/demo/projection", status_code=302)

    ctx = demo_module.get_projection_context()
    pair = demo_module.get_projection_pair_data()

    stat_categories = ctx["stat_categories"]
    enabled_stats = [c["stat_name"] for c in stat_categories if c["is_enabled"]]
    scoreboard = ctx["scoreboard"]
    teams = ctx["teams"]
    live_by_key = {row["team_key"]: row for row in ctx["live_stats_rows"]}
    lastmonth_stats = pair["lastmonth_stats"]
    games_remaining = pair["games_remaining"]

    # Fixed demo matchup: resolve the pair directly (no scoreboard loop). The
    # selector only offers the two teams in the pair; swap orderings so the
    # roster breakdowns stay correct whichever side is selected.
    if selected == pair["opp_team_key"]:
        my_team_key = pair["opp_team_key"]
        opponent_key = pair["my_team_key"]
        my_roster = pair["opp_roster"]
        opp_roster = pair["my_roster"]
    else:
        my_team_key = pair["my_team_key"]
        opponent_key = pair["opp_team_key"]
        my_roster = pair["my_roster"]
        opp_roster = pair["opp_roster"]

    my_team_name = next(
        (t["team_name"] for t in teams if t["team_key"] == my_team_key), my_team_key
    )
    opponent_name = next(
        (t["team_name"] for t in teams if t["team_key"] == opponent_key), opponent_key
    )

    my_current = {s: float(live_by_key.get(my_team_key, {}).get(s, 0.0)) for s in enabled_stats}
    opp_current = {s: float(live_by_key.get(opponent_key, {}).get(s, 0.0)) for s in enabled_stats}

    return _render_matchup(
        request,
        current_week=ctx["current_week"],
        week_start=scoreboard["week_start"],
        week_end=scoreboard["week_end"],
        stat_categories=stat_categories,
        enabled_stats=enabled_stats,
        my_team_name=my_team_name,
        opponent_name=opponent_name,
        my_current=my_current,
        opp_current=opp_current,
        my_roster=my_roster,
        opp_roster=opp_roster,
        lastmonth_stats=lastmonth_stats,
        games_remaining=games_remaining,
    )
