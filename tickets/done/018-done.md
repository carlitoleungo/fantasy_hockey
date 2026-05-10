## Implementation complete — 018

**What I did:**
- Created `web/routes/waiver.py` with `GET /waiver` (authenticated) and `GET /demo/waiver` (public) route handlers
- Ported `_STAT_FALLBACK_ABBREV` dict from `pages/03_waiver_wire.py` into the new router; merged with live API abbreviations before passing to the template
- Created `web/templates/waiver/` directory and `web/templates/waiver/index.html` with the full filter shell: position pills (All/C/LW/RW/D/G), period radio (Season/Last 30 days), stat category chips, HTMX form wired to `hx-post`, `hx-target`, `hx-trigger="change"`, and the empty-state `#waiver-table-container`
- Added the hidden `<input id="page-input">` and `hx-on:change` reset as specified for pagination support in ticket 019
- Added "Waiver" nav link to `web/templates/base.html` between Overview and Logout
- Registered both `waiver_router` and `waiver_public_router` in `web/main.py`
- Wrote `tests/test_waiver_routes.py` with 7 tests covering all acceptance criteria

**Files changed:**
- `web/routes/waiver.py` — new; both route handlers + `_STAT_FALLBACK_ABBREV`
- `web/templates/waiver/index.html` — new; filter shell template
- `web/templates/base.html` — added "Waiver" nav link after "Overview"
- `web/main.py` — registered `waiver_router` and `waiver_public_router`
- `tests/test_waiver_routes.py` — new; 7 unit tests

**How to verify:**
- Run `pytest tests/test_waiver_routes.py -v` — all 7 tests should pass
- Run `pytest` — 307 tests pass, no regressions
- Start the app (`uvicorn web.main:app --reload`) and navigate to `/waiver` with a valid session; confirm position pills, period radio, stat chips, and empty-state message render
- Navigate to `/demo/waiver` (no session needed); confirm the same shell renders with demo data and the form action points to `/demo/api/waiver/players`
- Confirm the "Waiver" link appears in the header on all pages

**Scope notes:**
- `get_user_hockey_leagues` is called on every `GET /waiver` to resolve `selected_league_name` — this is one live Yahoo API call per page load. Flagged in ticket notes as a future candidate for session-level caching (ticket 018 Tech Lead flag #5).
- Demo `stat_cols` are derived from `load_season_pool()` column names (via `stat_columns()`), not from the matchups DataFrame. This matches the ticket spec but means the demo chip labels reflect player-pool column names, not league matchup column names. They should be equivalent for demo data.

**Known limitations:**
- The POST handler (`/api/waiver/players`) does not exist yet — ticket 019. Any filter change will POST and receive a 404/422 until 019 ships. The empty-state message remains visible until the POST handler is wired up.
