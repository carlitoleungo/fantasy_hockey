## Code Review — 011

**Files reviewed:**
- `web/routes/home.py` — new file; `GET /` and `POST /leagues/select` route handlers
- `web/templates/home.html` — new template extending `base.html`
- `web/main.py` — registers `home_router`
- `requirements-web.txt` — adds `xmltodict` (QA bug fix)
- `tests/test_home_routes.py` — 7 new tests covering all acceptance criteria

### Scope: CLEAN

All changes match the ticket. The `requirements-web.txt` addition was a QA-identified blocker — appropriate to include.

### Architecture: CLEAN

- No framework imports in `data/` or `analysis/`
- No per-entity API loops — `get_user_hockey_leagues` is one call
- No raw stat values or un-normalized array responses (not applicable to this ticket)
- No new `data/` functions introduced, so no demo counterpart required

### Issues

- **Must fix:** None
- **Should fix:** None
- **Nit:** The module docstring in `tests/test_home_routes.py` (lines 8–10) says `xmltodict` is "not in requirements-web.txt" — that was true before the fix but is now wrong. The `if "xmltodict" not in sys.modules` guard is also effectively dead code once the package is installed. Neither affects correctness, but the stale comment will mislead the next reader. Logged to `docs/improvements.md`.

### Verdict: APPROVED

Implementation is correct and complete. Season filtering matches the spec. Template covers all required elements (heading, league list, selected indicator, empty state, logout link). All 7 tests pass and cover the acceptance criteria plus the HTTPError edge case. No architectural violations.
