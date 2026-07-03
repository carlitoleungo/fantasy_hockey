from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from auth.oauth import make_session
from data.client import get_teams
from data.leagues import get_user_hockey_leagues
from db.connection import db_dep
from web.middleware.session import CurrentUser, require_user
from web.routes.common import _get_league_key
from web.templates import templates

router = APIRouter()


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
