## Implementation complete — 014

**What I did:**
- Added `<header>` to `web/templates/base.html` with app-name link to `/`, optional league name label (rendered only when `selected_league_name` is truthy), and logout link to `/auth/logout`
- Removed the logout `<a>` from `web/templates/home.html`; simplified the heading row to a plain `<h1>`
- Updated `web/routes/home.py` to derive `selected_league_name` from the already-fetched `leagues` list and the session `league_key` — no extra API call
- Added three new tests (TC8–TC10) to `tests/test_home_routes.py` covering: header renders app-name + logout, header shows league name when selected, header has no separator when no league selected
- Resolved open improvement: removed stale `xmltodict` comment, dead `sys.modules` guard, and unused `sys` import from `tests/test_home_routes.py`; marked closed in `docs/improvements.md`

**Files changed:**
- `web/templates/base.html` — added `<header>` with nav shell before `{% block content %}`
- `web/templates/home.html` — removed logout link; simplified heading row to `<h1>`
- `web/routes/home.py` — derived `selected_league_name` and added it to template context
- `tests/test_home_routes.py` — added TC8/TC9/TC10; removed stale xmltodict stub and `sys` import
- `docs/improvements.md` — moved stale-comment item to Closed

**How to verify:**
- Run `python -m pytest tests/test_home_routes.py -v` — all 10 tests should pass
- Start the app (`uvicorn web.main:app --reload`), visit `/` logged in with no league selected → header shows "Fantasy Hockey" and "Logout", no separator
- Select a league via the form → refresh `/` → header shows the league name as a muted secondary label after `·`
- Confirm the old logout link no longer appears inside the page content (only in the header)

**Scope notes:**
- Feature navigation links (Overview / Waiver / Projection) intentionally not added per ticket spec and decisions.md entry 2026-04-19

**Known limitations:**
- Pages that extend `base.html` but don't pass `selected_league_name` in their context will silently omit the league label (the `{% if %}` guard handles this). Ticket 015 will add a shared helper to resolve this value for feature pages.
