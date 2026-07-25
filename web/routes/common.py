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


def _get_league_key(db, session_id: str) -> str | None:
    row = db.execute(
        "SELECT league_key FROM user_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["league_key"] if row and row["league_key"] else None
