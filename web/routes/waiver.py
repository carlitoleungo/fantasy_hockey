from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from analysis.team_scores import stat_columns
from auth.oauth import make_session
from data.client import get_stat_categories
from data.leagues import get_user_hockey_leagues
from data.matchups import get_matchups
from db.connection import db_dep
from web.middleware.session import CurrentUser, require_user
from web.routes.overview import _get_league_key
from web.templates import templates

router = APIRouter()
public_router = APIRouter()

_STAT_FALLBACK_ABBREV: dict[str, str] = {
    "Goals": "G",
    "Assists": "A",
    "Points": "Pts",
    "Plus/Minus": "+/-",
    "Penalty Minutes": "PIM",
    "Power Play Goals": "PPG",
    "Powerplay Goals": "PPG",
    "Power Play Assists": "PPA",
    "Powerplay Assists": "PPA",
    "Power Play Points": "PPP",
    "Powerplay Points": "PPP",
    "Short Handed Goals": "SHG",
    "Short Handed Assists": "SHA",
    "Short Handed Points": "SHP",
    "Shots on Goal": "SOG",
    "Hits": "HIT",
    "Blocked Shots": "BLK",
    "Blocks": "BLK",
    "Wins": "W",
    "Save Percentage": "SV%",
    "Goals Against Average": "GAA",
    "Saves": "SV",
    "Shutouts": "SO",
    "Goals Against": "GA",
    "Faceoffs Won": "FOW",
}


@router.get("/waiver")
def waiver_shell(
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
    df = get_matchups(session, league_key)
    stat_cols = stat_columns(df) if df is not None and not df.empty else []
    raw_cats = get_stat_categories(session, league_key)
    stat_abbrev = {
        **_STAT_FALLBACK_ABBREV,
        **{c["stat_name"]: c["abbreviation"] for c in raw_cats if c["is_enabled"]},
    }
    return templates.TemplateResponse(
        request,
        "waiver/index.html",
        {
            "stat_cols": stat_cols,
            "stat_abbrev": stat_abbrev,
            "selected_league_name": selected_league_name,
            "form_action": "/api/waiver/players",
        },
    )


@public_router.get("/demo/waiver")
def demo_waiver_shell(request: Request):
    from data import demo as demo_module

    matchups_df = demo_module.get_matchups()
    stat_cols = stat_columns(matchups_df) if matchups_df is not None and not matchups_df.empty else []
    raw_cats = demo_module.get_stat_categories()
    stat_abbrev = {
        **_STAT_FALLBACK_ABBREV,
        **{c["stat_name"]: c["abbreviation"] for c in raw_cats if c["is_enabled"]},
    }
    return templates.TemplateResponse(
        request,
        "waiver/index.html",
        {
            "stat_cols": stat_cols,
            "stat_abbrev": stat_abbrev,
            "selected_league_name": "Demo League",
            "form_action": "/demo/api/waiver/players",
        },
    )
