## Implementation complete — 016

**What I did:**
- Added `GET /overview/head-to-head` shell route and `GET /overview/head-to-head/table` fragment route to `web/routes/overview.py`
- Created `web/templates/overview/head_to_head.html` (shell: team/week selectors in an HTMX form, initial comparison table rendered via include)
- Created `web/templates/overview/_head_to_head_table.html` (fragment: category table with winner highlighting and tally row)
- Added "Compare two teams →" in-page link to `web/templates/overview/index.html`
- Wrote 11 unit tests in `tests/test_head_to_head_routes.py` (all pass)
- Resolved open improvement: `stat_columns(df)` called twice in `overview()` and `overview_table()` — extracted to local `cols` in both handlers; marked closed in `docs/improvements.md`

**Files changed:**
- `web/routes/overview.py` — imported `simulate`/`tally`; fixed `stat_columns` duplication in existing handlers; added `head_to_head` and `head_to_head_table` handlers
- `web/templates/overview/head_to_head.html` — new shell template
- `web/templates/overview/_head_to_head_table.html` — new fragment template
- `web/templates/overview/index.html` — added "Compare two teams →" link inside the `{% if weeks %}` block
- `tests/test_head_to_head_routes.py` — new test file (11 tests)
- `docs/improvements.md` — moved `stat_columns` duplication item to Closed

**How to verify:**
- Run `.venv/bin/python -m pytest tests/test_head_to_head_routes.py -v` — all 11 tests should pass
- Run `.venv/bin/python -m pytest tests/test_overview_routes.py tests/test_overview_routes_qa.py -v` — all 13 existing tests should still pass
- Start the app with `uvicorn web.main:app --reload`, log in, select a league, navigate to `/overview` and confirm "Compare two teams →" link is present
- Click the link → `/overview/head-to-head` loads with two team dropdowns, two week dropdowns, and an initial comparison table
- Change any dropdown → table updates without a full page reload (HTMX)
- Confirm winner cells show `bg-green-100`, tied cells show `bg-gray-100`, and the tally line below the table is correct
- Navigate back via "← Back to Leaderboard"

**Scope notes:**
- The HTMX form's `hx-trigger="change"` fires on every individual dropdown change. If a user changes two dropdowns quickly, two fragment fetches fire; the second one wins. This is standard HTMX behaviour and acceptable for v1.
- Demo mode: this ticket adds two new route handlers that call `get_matchups` live. If demo mode needs head-to-head, a follow-up ticket should wire up `data/demo.py` to serve the demo matchups DataFrame from the `/overview/head-to-head` routes.

**Known limitations:**
- No manual browser test was performed (CLI-only environment). The HTMX partial-update behaviour is covered by template inspection but not end-to-end browser testing.
- `team_a == team_b` edge case (same team picked twice) renders a table where all categories are "Tie" — acceptable per ticket spec.
