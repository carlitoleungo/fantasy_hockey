import pandas as pd
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from analysis.matchup_sim import simulate, tally
from analysis.team_scores import LOWER_IS_BETTER, stat_columns, weekly_scores_ranked
from auth.oauth import make_session
from data.leagues import get_user_hockey_leagues
from data.matchups import get_matchups
from db.connection import db_dep
from web.middleware.session import CurrentUser, require_user
from web.templates import templates

router = APIRouter()


def _get_league_key(db, session_id: str) -> str | None:
    row = db.execute(
        "SELECT league_key FROM user_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["league_key"] if row and row["league_key"] else None


def _compute_cell_ranks(ranked_df: pd.DataFrame, stat_cols: list[str]) -> pd.DataFrame:
    ranks = pd.DataFrame(index=ranked_df.index)
    for col in stat_cols:
        ranks[col] = ranked_df[col].rank(
            method="min", ascending=(col in LOWER_IS_BETTER),
        )
    return ranks


@router.get("/overview")
def overview(
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
        (lg["league_name"] for lg in leagues if lg["league_key"] == league_key), None
    )

    df = get_matchups(session, league_key)
    if df is None or df.empty:
        return templates.TemplateResponse(
            request,
            "overview/index.html",
            {
                "weeks": [],
                "selected_week": None,
                "ranked": None,
                "stat_cols": [],
                "selected_league_name": selected_league_name,
            },
        )

    weeks = sorted(df["week"].unique().tolist())
    selected_week = weeks[-1]
    ranked = weekly_scores_ranked(df, selected_week)
    cols = stat_columns(df)
    cell_ranks = _compute_cell_ranks(ranked, cols)
    return templates.TemplateResponse(
        request,
        "overview/index.html",
        {
            "weeks": weeks,
            "selected_week": selected_week,
            "ranked": ranked,
            "cell_ranks": cell_ranks,
            "stat_cols": cols,
            "team_count": len(ranked),
            "selected_league_name": selected_league_name,
        },
    )


@router.get("/overview/table")
def overview_table(
    week: int,
    request: Request,
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    league_key = _get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)

    session = make_session(current_user.access_token)
    df = get_matchups(session, league_key)
    if df is None or df.empty:
        return templates.TemplateResponse(
            request,
            "overview/_table.html",
            {"ranked": None, "cell_ranks": None, "stat_cols": [], "team_count": 0},
        )

    ranked = weekly_scores_ranked(df, week)
    cols = stat_columns(df)
    cell_ranks = _compute_cell_ranks(ranked, cols)
    return templates.TemplateResponse(
        request,
        "overview/_table.html",
        {
            "ranked": ranked,
            "cell_ranks": cell_ranks,
            "stat_cols": cols,
            "team_count": len(ranked),
        },
    )


@router.get("/overview/head-to-head")
def head_to_head(
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
        (lg["league_name"] for lg in leagues if lg["league_key"] == league_key), None
    )

    df = get_matchups(session, league_key)
    teams = sorted(df["team_name"].unique().tolist()) if df is not None and not df.empty else []

    if len(teams) < 2:
        return templates.TemplateResponse(
            request,
            "overview/head_to_head.html",
            {
                "teams": [],
                "weeks": [],
                "not_enough_data": True,
                "selected_league_name": selected_league_name,
            },
        )

    weeks = sorted(df["week"].unique().tolist())
    team_a = teams[0]
    team_b = teams[1]
    from_week = weeks[0]
    to_week = weeks[-1]

    sim = simulate(df, team_a, team_b, from_week, to_week)
    tally_result = tally(sim, team_a, team_b)

    return templates.TemplateResponse(
        request,
        "overview/head_to_head.html",
        {
            "teams": teams,
            "weeks": weeks,
            "team_a": team_a,
            "team_b": team_b,
            "from_week": from_week,
            "to_week": to_week,
            "sim": sim,
            "tally": tally_result,
            "not_enough_data": False,
            "selected_league_name": selected_league_name,
        },
    )


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
    league_key = _get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)

    session = make_session(current_user.access_token)
    df = get_matchups(session, league_key)

    if df is None or df.empty:
        return templates.TemplateResponse(
            request,
            "overview/_head_to_head_table.html",
            {"sim": None, "tally": None, "team_a": team_a, "team_b": team_b},
        )

    if from_week > to_week:
        from_week, to_week = to_week, from_week

    sim = simulate(df, team_a, team_b, from_week, to_week)
    tally_result = tally(sim, team_a, team_b)

    return templates.TemplateResponse(
        request,
        "overview/_head_to_head_table.html",
        {
            "sim": sim,
            "tally": tally_result,
            "team_a": team_a,
            "team_b": team_b,
        },
    )
