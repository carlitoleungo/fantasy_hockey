"""Helpers shared across route modules.

Canonical home for route-layer helpers used by more than one feature module
(see docs/DECISIONS.md 2026-05-30 "Shared route helpers").
"""


def _get_league_key(db, session_id: str) -> str | None:
    row = db.execute(
        "SELECT league_key FROM user_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["league_key"] if row and row["league_key"] else None
