"""
Fetch a team's roster for a given fantasy week.
"""
from __future__ import annotations

from data.client import BASE_URL, _as_list, _get

# Slots that don't score fantasy points — excluded from projections
IR_SLOTS = frozenset({"IR", "IR+", "IL", "IL+"})


def get_team_roster(
    session,
    team_key: str,
    week: int | None = None,
    date: str | None = None,
) -> list[dict]:
    """
    Fetch the roster for a team.

    Pass `date` (ISO string, e.g. "2026-03-26") to get today's live lineup —
    this correctly excludes players who have been dropped since the week started.
    Pass `week` for historical lookups. Exactly one should be provided.

    Excludes players in IR/IR+/IL/IL+ slots. Bench (BN) players are included
    because they can be moved to an active slot.

    Returns list of:
        {
            "player_key":       str,
            "player_name":      str,
            "team_abbr":        str,   # NHL team abbr — matches NHL schedule API
            "display_position": str,
            "roster_slot":      str,   # actual lineup slot (C, LW, BN, etc.)
        }
    """
    if date is not None:
        url = f"{BASE_URL}/team/{team_key}/roster;date={date}"
    else:
        url = f"{BASE_URL}/team/{team_key}/roster;week={week}"
    data = _get(session, url)

    raw_players = (
        data.get("fantasy_content", {})
        .get("team", {})
        .get("roster", {})
        .get("players", {})
    )

    player_list = _as_list(raw_players.get("player", []))

    roster = []
    for p in player_list:
        slot = p.get("selected_position", {}).get("position", "")
        if slot in IR_SLOTS:
            continue
        roster.append({
            "player_key": p["player_key"],
            "player_name": p["name"]["full"],
            "team_abbr": p.get("editorial_team_abbr", ""),
            "display_position": p.get("display_position", ""),
            "roster_slot": slot,
        })

    return roster
