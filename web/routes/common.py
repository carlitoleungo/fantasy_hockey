"""Helpers shared across route modules.

Canonical home for route-layer helpers used by more than one feature module
(see docs/DECISIONS.md 2026-05-30 "Shared route helpers").
"""

from __future__ import annotations

from web.middleware.session import CurrentUser


def shell_context(
    current_user: CurrentUser | None,
    *,
    demo: bool = False,
    league_name: str | None = None,
) -> dict:
    """Nav/shell keys consumed by base.html.

    Takes the user already resolved by the route's require_user/optional_user
    dependency — never re-derives auth from the cookie or DB (see
    docs/DECISIONS.md 2026-07-03 "Nav shell: conditional on auth/demo state via
    shared shell-context").
    """
    return {
        "is_authenticated": current_user is not None,
        "demo_mode": demo,
        "selected_league_name": league_name,
    }


def unknown_auth_shell_context() -> dict:
    """Nav/shell keys for a render site that cannot resolve a user.

    FastAPI exception handlers get only the Request and no dependency
    injection, so there is no CurrentUser to hand to shell_context(). Rather
    than derive one — the second auth path this codebase does not allow — the
    page declares the state unknown and base.html renders nav-free (see
    docs/DECISIONS.md 2026-07-25 "Nav shell: render sites that cannot resolve a
    user declare the state unknown and render nav-free; exception handlers
    never derive auth").
    """
    return {"auth_state_unknown": True}


def get_league_key(db, session_id: str) -> str | None:
    """The league this session selected on the home page, or None."""
    row = db.execute(
        "SELECT league_key FROM user_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["league_key"] if row and row["league_key"] else None


# Short labels for Yahoo stat names, used when the league's own stat categories
# (which carry Yahoo's abbreviations) aren't fetched for a page.
STAT_FALLBACK_ABBREV: dict[str, str] = {
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
