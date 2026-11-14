from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from auth.oauth import make_session
from data.leagues import get_user_hockey_leagues
from db.connection import db_dep
from web.middleware.session import CurrentUser, optional_user, require_user
from web.routes.common import get_league_key, shell_context
from web.templates import templates

router = APIRouter()


@router.get("/")
def home(
    request: Request,
    current_user: CurrentUser | None = Depends(optional_user),
    db=Depends(db_dep),
):
    if current_user is None:
        return templates.TemplateResponse(
            request,
            "home.html",
            {"leagues": None, **shell_context(None)},
        )

    session = make_session(current_user.access_token)
    all_leagues = get_user_hockey_leagues(session)

    if all_leagues:
        current_season = max(lg["season"] for lg in all_leagues)
        leagues = [lg for lg in all_leagues if lg["season"] == current_season]
    else:
        leagues = []

    selected_key = get_league_key(db, current_user.session_id)
    selected_league_name = next(
        (lg["league_name"] for lg in leagues if lg["league_key"] == selected_key),
        None,
    ) if selected_key else None

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "leagues": leagues,
            "selected_key": selected_key,
            **shell_context(current_user, league_name=selected_league_name),
        },
    )


@router.post("/leagues/select")
def select_league(
    league_key: str = Form(...),
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    db.execute(
        "UPDATE user_sessions SET league_key = ? WHERE session_id = ?",
        (league_key, current_user.session_id),
    )
    db.commit()
    return RedirectResponse("/", status_code=302)
