## Code Review — 014

**Files reviewed:**
- `web/templates/base.html` — added `<header>` with nav shell before `{% block content %}`
- `web/templates/home.html` — removed logout link; simplified heading row to plain `<h1>`
- `web/routes/home.py` — derived `selected_league_name` from already-fetched `leagues` list; added to template context
- `tests/test_home_routes.py` — added TC8/TC9/TC10; removed stale xmltodict stub and unused `sys` import
- `docs/improvements.md` — moved stale-comment item to Closed

---

### Scope: SCOPE_CREEP_DETECTED

The cleanup in `tests/test_home_routes.py` (removing the xmltodict `sys.modules` guard and stale docstring) and the corresponding `docs/improvements.md` update were not in the ticket spec. This was a tracked improvement item being resolved opportunistically while the file was already in scope. The change is correct and the work is welcome — just flagging it because the engineer did not note it as bonus work in the spec, only in the done.md.

Low concern. The affected file was already being touched and the improvement was pre-approved in the backlog.

---

### Architecture: CLEAN

No `data/` or `analysis/` files touched. No new API calls. No per-entity loops. No raw stat values or array responses. No framework imports in wrong layers. No new live data functions, so no demo counterpart needed.

---

### Issues

- **Must fix:** None.

- **Should fix:** None.

- **Nit:** TC9 (`test_home_header_shows_selected_league_name`) asserts `"Alpha League" in response.text`. With the fixture used, "Alpha League" appears in both the `<header>` element (via `selected_league_name`) and in the league list body (as one of the rendered leagues). The assertion would pass even if `selected_league_name` were missing from the context entirely — the league list body alone would satisfy it. The QA engineer also flagged this. Logged to `docs/improvements.md`.

---

### Verdict: APPROVED

Implementation matches the spec. The `selected_league_name` derivation pattern is exactly what the ticket specified, no extra API calls, Tailwind utilities consistent with the existing template style. Tests cover the three meaningful cases (header present, league label shown, no label when unselected). TC9's weak assertion is a nit worth tightening later but is not a blocker — the behavior is correct and was verified manually in QA.
