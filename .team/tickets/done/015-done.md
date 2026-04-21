## Implementation complete — 015

**What I did:**
- Created `web/routes/overview.py` with `GET /overview` (shell) and `GET /overview/table` (fragment) route handlers
- Defined `_get_league_key` as a named module-level function (importable by ticket 016 per spec)
- Defined `_compute_cell_ranks` in the route layer (not in `analysis/`) per the ticket's single-responsibility note
- Created `web/templates/overview/index.html` — shell with week selector using HTMX (`hx-get="/overview/table"`, `hx-target="#leaderboard-table"`)
- Created `web/templates/overview/_table.html` — fragment with color-coded stat cells; uses `iterrows()` (not `itertuples()`) so column names with spaces like "Goals Against Average" work correctly in Jinja2
- Added `rank_color` Jinja filter to `web/templates.py`
- Added "Overview" nav link to `web/templates/base.html` header (between app-name and logout, inside a `<nav>`)
- Included `overview_router` in `web/main.py`
- Added `tests/test_overview_routes.py` with 6 tests covering the acceptance criteria

**Files changed:**
- `web/routes/overview.py` — new; contains `_get_league_key`, `_compute_cell_ranks`, `/overview`, `/overview/table`
- `web/templates/overview/index.html` — new; page shell with week selector and HTMX fragment target
- `web/templates/overview/_table.html` — new; leaderboard table fragment with bg-green-100/bg-red-100 coloring
- `web/templates/base.html` — added "Overview" link in header nav
- `web/templates.py` — registered `rank_color` Jinja filter
- `web/main.py` — included overview router
- `tests/test_overview_routes.py` — new; 6 tests, all passing

**How to verify:**
- Run `.venv/bin/pytest tests/test_overview_routes.py -v` — all 6 tests should pass
- Run `.venv/bin/pytest tests/ -q` — all 282 tests should pass (no regressions)
- Start the app with `uvicorn web.main:app --reload`, log in, select a league at `/`, then navigate to `/overview` — week selector and leaderboard table should render
- Change the week selector — devtools network tab should show an XHR to `/overview/table?week=<n>`, not a full page navigation
- Confirm the "Overview" link appears in the header on `/`, `/overview`, and the error page

**Scope notes:**
- `_get_league_key` is defined as a module-level private function as specified; ticket 016 can import it directly from `web.routes.overview`
- `iterrows()` was used in the template instead of `itertuples()` (which the ticket pseudocode suggested) because `itertuples()` cannot access column names with spaces (like "Goals Against Average") via attribute lookup — `iterrows()` gives a Series where `row[col]` with string keys works correctly
- No demo counterpart was added for this ticket (no new `data/` function was introduced — it only calls the existing `get_matchups`). Demo mode for `/overview` will need a separate ticket if `/demo/overview` is required.

**Known limitations:**
- Ties on `method='min'` can leave the worst cell uncolored (e.g. two teams tied for second-worst in a 12-team league both get rank 11, not 12). Acceptable for v1 per the ticket; added to `docs/improvements.md` below.
