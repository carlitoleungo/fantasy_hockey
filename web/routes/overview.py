import pandas as pd
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from analysis.matchup_sim import simulate, tally
from analysis.projection import is_rate_stat
from analysis.team_scores import (
    LOWER_IS_BETTER,
    rank_shade_levels,
    stat_columns,
    weekly_scores_ranked,
)
from auth.oauth import make_session
from data import demo as demo_module
from data.leagues import get_user_hockey_leagues
from data.matchups import get_matchups
from db.connection import db_dep
from web.middleware.session import CurrentUser, require_user
from web.routes.common import STAT_FALLBACK_ABBREV, get_league_key, shell_context
from web.templates import templates

router = APIRouter()
public_router = APIRouter()

_DEMO_PREFIX = "/demo"


# ---------------------------------------------------------------------------
# Shared compute + render (live and demo routes both call these)
# ---------------------------------------------------------------------------

def _has_data(df: pd.DataFrame | None) -> bool:
    return df is not None and not df.empty


def _format_helpers() -> dict:
    """Template helpers shared by the Leaderboard and Head-to-Head tables."""
    return {
        "stat_abbrev": STAT_FALLBACK_ABBREV,
        "is_rate_stat": is_rate_stat,
        "lower_is_better": LOWER_IS_BETTER,
    }


def _week_table_context(df: pd.DataFrame, week: int) -> dict:
    """The ranked-table keys shared by the full page and the week fragment."""
    ranked = weekly_scores_ranked(df, week)
    cols = stat_columns(df)
    shades = rank_shade_levels(ranked[cols])
    return {
        "ranked": ranked,
        "shades": shades.to_dict("index"),
        "stat_cols": cols,
        "team_count": len(ranked),
        "week": week,
        **_format_helpers(),
    }


def _render_overview(request: Request, df: pd.DataFrame | None, *, prefix: str, shell: dict):
    context = {
        "table_url": f"{prefix}/overview/table",
        "head_to_head_url": f"{prefix}/overview/head-to-head",
        **shell,
    }
    if not _has_data(df):
        context.update({"weeks": [], "selected_week": None, "ranked": None, "stat_cols": []})
    else:
        weeks = sorted(df["week"].unique().tolist())
        context.update({
            "weeks": weeks,
            "selected_week": weeks[-1],
            **_week_table_context(df, weeks[-1]),
        })
    return templates.TemplateResponse(request, "overview/index.html", context)


def _render_overview_table(request: Request, df: pd.DataFrame | None, week: int):
    if not _has_data(df):
        context = {"ranked": None, "shades": {}, "stat_cols": [], "team_count": 0, "week": week}
    else:
        context = _week_table_context(df, week)
    return templates.TemplateResponse(request, "overview/_table.html", context)


def _render_head_to_head(request: Request, df: pd.DataFrame | None, *, prefix: str, shell: dict):
    context = {
        "table_url": f"{prefix}/overview/head-to-head/table",
        "overview_url": f"{prefix}/overview",
        **_format_helpers(),
        **shell,
    }
    teams = sorted(df["team_name"].unique().tolist()) if _has_data(df) else []
    if len(teams) < 2:
        context.update({"teams": [], "weeks": [], "not_enough_data": True})
    else:
        weeks = sorted(df["week"].unique().tolist())
        team_a, team_b = teams[0], teams[1]
        from_week, to_week = weeks[0], weeks[-1]
        sim = simulate(df, team_a, team_b, from_week, to_week)
        context.update({
            "teams": teams,
            "weeks": weeks,
            "team_a": team_a,
            "team_b": team_b,
            "from_week": from_week,
            "to_week": to_week,
            "sim": sim,
            "tally": tally(sim, team_a, team_b),
            "not_enough_data": False,
        })
    return templates.TemplateResponse(request, "overview/head_to_head.html", context)


def _render_head_to_head_table(
    request: Request,
    df: pd.DataFrame | None,
    team_a: str,
    team_b: str,
    from_week: int,
    to_week: int,
):
    context = {"team_a": team_a, "team_b": team_b, **_format_helpers()}
    if not _has_data(df):
        context.update({"sim": None, "tally": None})
    else:
        if from_week > to_week:
            from_week, to_week = to_week, from_week
        sim = simulate(df, team_a, team_b, from_week, to_week)
        context.update({
            "sim": sim,
            "tally": tally(sim, team_a, team_b),
            "from_week": from_week,
            "to_week": to_week,
        })
    return templates.TemplateResponse(request, "overview/_head_to_head_table.html", context)


def _league_name(session, league_key: str) -> str | None:
    leagues = get_user_hockey_leagues(session)
    return next((lg["league_name"] for lg in leagues if lg["league_key"] == league_key), None)


def _demo_shell() -> dict:
    return shell_context(None, demo=True, league_name="Demo League")


def _demo_matchups() -> pd.DataFrame:
    return demo_module.get_matchups()


# ---------------------------------------------------------------------------
# Live routes
# ---------------------------------------------------------------------------

@router.get("/overview")
def overview(
    request: Request,
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    league_key = get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)

    session = make_session(current_user.access_token)
    shell = shell_context(current_user, league_name=_league_name(session, league_key))
    df = get_matchups(session, league_key)
    return _render_overview(request, df, prefix="", shell=shell)


@router.get("/overview/table")
def overview_table(
    week: int,
    request: Request,
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    league_key = get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)

    session = make_session(current_user.access_token)
    return _render_overview_table(request, get_matchups(session, league_key), week)


@router.get("/overview/head-to-head")
def head_to_head(
    request: Request,
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    league_key = get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)

    session = make_session(current_user.access_token)
    shell = shell_context(current_user, league_name=_league_name(session, league_key))
    df = get_matchups(session, league_key)
    return _render_head_to_head(request, df, prefix="", shell=shell)


@router.get("/overview/head-to-head/table")
def head_to_head_table(
    team_a: str,
    team_b: str,
    from_week: int,
    to_week: int,
    request: Request,
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    league_key = get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)

    session = make_session(current_user.access_token)
    df = get_matchups(session, league_key)
    return _render_head_to_head_table(request, df, team_a, team_b, from_week, to_week)


# ---------------------------------------------------------------------------
# Demo routes (no auth required)
# ---------------------------------------------------------------------------

@public_router.get("/demo/overview")
def demo_overview(request: Request):
    return _render_overview(request, _demo_matchups(), prefix=_DEMO_PREFIX, shell=_demo_shell())


@public_router.get("/demo/overview/table")
def demo_overview_table(week: int, request: Request):
    return _render_overview_table(request, _demo_matchups(), week)


@public_router.get("/demo/overview/head-to-head")
def demo_head_to_head(request: Request):
    return _render_head_to_head(request, _demo_matchups(), prefix=_DEMO_PREFIX, shell=_demo_shell())


@public_router.get("/demo/overview/head-to-head/table")
def demo_head_to_head_table(
    team_a: str,
    team_b: str,
    from_week: int,
    to_week: int,
    request: Request,
):
    return _render_head_to_head_table(request, _demo_matchups(), team_a, team_b, from_week, to_week)
