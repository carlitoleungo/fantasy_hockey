# 028 — Extract shared route helper to web/routes/common.py

## Status
ready

## Type
refactor

## Process
light

## Touches
- web/routes/common.py
- web/routes/overview.py
- web/routes/waiver.py

## Why
`_get_league_key` currently lives in `web/routes/overview.py` and is imported
cross-module by `waiver.py` via an underscore-prefixed name, which reads as
accidental/fragile to any new reader. `docs/DECISIONS.md` (2026-05-30, "Shared
route helpers: web/routes/common.py is the canonical home") ruled this an interim
state to be resolved **in a dedicated refactor ticket before the next feature
route ships**. The Week Projection route (029) is that next route — so this
prerequisite is now due. Pure mechanical move; no behaviour change.

## Acceptance criteria
- [ ] `web/routes/common.py` exists and defines `_get_league_key(db, session_id)` with the same signature and body it had in `overview.py`.
- [ ] `overview.py` and `waiver.py` import `_get_league_key` from `web.routes.common` (no local definition, no import from `overview`).
- [ ] `GET /overview` still returns 200 for an authenticated session and renders the leaderboard (behaviour unchanged).
- [ ] `GET /waiver` still returns 200 for an authenticated session and renders the filter form (behaviour unchanged).

## Out of scope
- Moving any other helper (e.g. `_compute_cell_ranks`, `_STAT_FALLBACK_ABBREV`) — only `_get_league_key`.
- Any change to the demo routes or to route behaviour.

## Notes for the Engineer
- `_get_league_key` is defined at `web/routes/overview.py:18-23` and imported by `web/routes/waiver.py:20` (`from web.routes.overview import _get_league_key`).
- Conform to `docs/DECISIONS.md` 2026-05-30 "Shared route helpers: web/routes/common.py is the canonical home" — this ticket implements exactly that decision.
- Keep the underscore prefix (`_get_league_key`) — the decision endorses the name, only the location changes.
- No new tests required beyond the smoke checks below; this is a move, and the function has no dedicated tests today.

## Verification
- Start the app (`uvicorn web.main:app --reload`), log in, visit `/overview` and `/waiver` — both render as before.
- `grep -rn "_get_league_key" web/routes/` shows the definition only in `common.py` and imports (not definitions) elsewhere.

## Dependencies
- None
