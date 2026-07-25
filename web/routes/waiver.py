from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from analysis.projection import _is_rate_stat
from analysis.team_scores import stat_columns
from analysis.waiver_ranking import filter_by_position, rank_players
from auth.oauth import make_session
from data import cache
from data.client import get_stat_categories
from data.leagues import get_user_hockey_leagues
from data.matchups import get_matchups
from data.players import fetch_lastmonth_batch, fetch_season_pool
from data.schedule import get_remaining_games
from data.scoreboard import get_current_matchup
from db.connection import db_dep
from web.middleware.session import CurrentUser, require_user
from web.routes.common import _get_league_key, shell_context
from web.templates import templates

PAGE_SIZE = 25

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
            "form_action": "/api/waiver/players",
            **shell_context(current_user, league_name=selected_league_name),
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
            "form_action": "/demo/api/waiver/players",
            **shell_context(None, demo=True, league_name="Demo League"),
        },
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _merge_pool(existing: pd.DataFrame, new_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Union two DataFrames on player_key, keeping existing rows on conflict.

    New rows whose player_key is already present are discarded — the existing
    data is preferred so we don't overwrite season stats with a different sort's
    copy of the same player.
    """
    if new_rows.empty:
        return existing
    if existing.empty:
        return new_rows.copy()
    fresh = new_rows[~new_rows["player_key"].isin(existing["player_key"])]
    return pd.concat([existing, fresh], ignore_index=True)


def _waiver_post_impl(
    positions: list[str],
    stats: list[str],
    period: str,
    page: int,
    request: Request,
    *,
    demo: bool = False,
    session=None,
    league_key: str | None = None,
):
    form_action = "/demo/api/waiver/players" if demo else "/api/waiver/players"

    # Empty list or an "All" selection means "no position filter" — fetch and
    # show the combined "All" pool. Otherwise fetch/filter each selected position.
    selected = [p for p in positions if p and p != "All"]

    # Empty-state: no stats selected
    if not stats:
        return templates.TemplateResponse(
            request,
            "waiver/_table.html",
            {
                "rows": None,
                "stats": [],
                "period": period,
                "total_rows": 0,
                "total_pages": 1,
                "current_page": 0,
                "form_action": form_action,
            },
        )

    if demo:
        from data import demo as demo_module
        season_pool = demo_module.load_season_pool()
    else:
        cats = get_stat_categories(session, league_key)
        name_to_id = {c["stat_name"]: c["stat_id"] for c in cats if c["is_enabled"]}
        id_to_name = {c["stat_id"]: c["stat_name"] for c in cats if c["is_enabled"]}

        # Fetch each selected position's pool separately (per-position cache
        # keys). fetch_season_pool returns only the top-25 per stat sort, so a
        # single "All" fetch would crowd out sparse positions (D, G). Empty
        # selection ⇒ fetch the combined "All" pool as before.
        fetch_positions = selected if selected else ["All"]

        season_pool = pd.DataFrame()
        for pos in fetch_positions:
            api_position = None if pos == "All" else pos
            for stat in stats:
                if stat not in name_to_id:
                    continue
                if not cache.is_player_pool_stale(league_key, pos, stat):
                    cached = cache.read_player_pool(league_key, pos, stat)
                    if cached is not None:
                        season_pool = _merge_pool(season_pool, cached)
                        continue
                sort_id = name_to_id[stat]
                fetched = fetch_season_pool(
                    session, league_key, sort_id, id_to_name, position=api_position
                )
                if not fetched.empty:
                    cache.write_player_pool(league_key, pos, stat, fetched)
                season_pool = _merge_pool(season_pool, fetched)

    # ---------------------------------------------------------------------------
    # Last 30 days branch
    # ---------------------------------------------------------------------------
    games_remaining_map: dict = {}

    if period == "Last 30 days":
        if demo:
            from data import demo as demo_module
            lm_pool = demo_module.load_lastmonth_pool()
            games_remaining_map = demo_module.get_games_remaining()
        else:
            pool_keys = set(season_pool["player_key"]) if not season_pool.empty else set()

            # Read from cache if fresh; otherwise start with empty
            lm_pool = pd.DataFrame()
            if not cache.is_lastmonth_stale(league_key):
                cached_lm = cache.read_lastmonth_cache(league_key)
                if cached_lm is not None and not cached_lm.empty:
                    lm_pool = cached_lm[cached_lm["player_key"].isin(pool_keys)].copy()

            # Fetch stats for any keys missing from the cache
            cached_keys = set(lm_pool["player_key"]) if not lm_pool.empty else set()
            missing_keys = pool_keys - cached_keys
            if missing_keys:
                new_lm = fetch_lastmonth_batch(session, list(missing_keys), id_to_name)
                if not new_lm.empty:
                    cache.upsert_lastmonth_cache(league_key, new_lm)
                    lm_pool = _merge_pool(lm_pool, new_lm)

        if lm_pool.empty:
            # Fallback: use season stats
            base_df = season_pool
        else:
            if not demo:
                meta_cols = ["player_key", "player_name", "team_abbr", "display_position", "status"]
                season_meta = season_pool[[c for c in meta_cols if c in season_pool.columns]]
                base_df = season_meta.merge(lm_pool, on="player_key", how="inner")
            else:
                base_df = lm_pool

        if not demo:
            # Games remaining — fetch from scoreboard; fall back to empty map on any error
            try:
                matchups_df = get_matchups(session, league_key)
                if matchups_df is not None and not matchups_df.empty:
                    current_week = int(matchups_df["week"].max())
                    matchup = get_current_matchup(session, league_key, current_week)
                    from_date = date.fromisoformat(matchup["week_start"])
                    to_date = date.fromisoformat(matchup["week_end"])
                    team_abbrs = base_df["team_abbr"].unique().tolist() if not base_df.empty else []
                    if team_abbrs:
                        games_remaining_map = get_remaining_games(team_abbrs, from_date, to_date)
            except Exception:
                games_remaining_map = {}
    else:
        base_df = season_pool

    # Union the pool across each selected position, de-duplicated on player_key.
    # "All"/empty ⇒ no position filter.
    if not selected or base_df.empty:
        filtered_df = base_df
    else:
        filtered_df = (
            pd.concat(
                [filter_by_position(base_df, p) for p in selected],
                ignore_index=True,
            )
            .drop_duplicates(subset="player_key")
            .reset_index(drop=True)
        )

    # Guard rank_players against missing columns
    safe_cats = [s for s in stats if s in filtered_df.columns]
    if safe_cats and not filtered_df.empty:
        ranked_df = rank_players(filtered_df, safe_cats)
    else:
        ranked_df = filtered_df.copy()
        if "composite_rank" not in ranked_df.columns:
            ranked_df["composite_rank"] = None

    if period == "Last 30 days" and games_remaining_map and "team_abbr" in ranked_df.columns:
        ranked_df["games_remaining"] = ranked_df["team_abbr"].map(
            lambda a: games_remaining_map.get(a, 0)
        )

    total_rows = len(ranked_df)
    total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)

    # Clamp page to valid range
    page = max(0, min(page, total_pages - 1))

    page_df = ranked_df.iloc[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    return templates.TemplateResponse(
        request,
        "waiver/_table.html",
        {
            "rows": page_df,
            "stats": safe_cats,
            "period": period,
            "total_rows": total_rows,
            "total_pages": total_pages,
            "current_page": page,
            "form_action": form_action,
            "is_rate_stat": _is_rate_stat,
        },
    )


# ---------------------------------------------------------------------------
# POST handlers
# ---------------------------------------------------------------------------

@router.post("/api/waiver/players")
def waiver_players(
    request: Request,
    positions: list[str] = Form([]),
    stats: list[str] = Form([]),
    period: str = Form("Season"),
    page: int = Form(0),
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    league_key = _get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)
    session = make_session(current_user.access_token)
    return _waiver_post_impl(
        positions, stats, period, page, request,
        demo=False, session=session, league_key=league_key,
    )


@public_router.post("/demo/api/waiver/players")
def demo_waiver_players(
    request: Request,
    positions: list[str] = Form([]),
    stats: list[str] = Form([]),
    period: str = Form("Season"),
    page: int = Form(0),
):
    return _waiver_post_impl(
        positions, stats, period, page, request,
        demo=True,
    )
