## Code Review — 018

**Files reviewed:**
- `web/routes/waiver.py` — new file; `GET /waiver` and `GET /demo/waiver` route handlers, `_STAT_FALLBACK_ABBREV` dict
- `web/templates/waiver/index.html` — new file; full filter-control shell template
- `web/templates/base.html` — "Waiver" nav link appended after "Overview"
- `web/main.py` — both waiver routers registered
- `tests/test_waiver_routes.py` — new file; TC1–TC7 covering all acceptance criteria

### Scope: CLEAN

All changes match the ticket exactly. The post-QA fix (replacing `load_season_pool()` with `get_matchups()` as the stat-column source for the demo route) is the correct scope; it resolves the bug without touching anything outside this ticket.

### Architecture: CLEAN

- No framework imports in `data/` or `analysis/`.
- No per-entity API loops — `get_matchups`, `get_stat_categories`, and `stat_columns` are all bulk/collection calls.
- No raw `stat['value']` access — all stat data flows through the existing `data/` layer.
- No Yahoo API array responses accessed without normalization in this code.
- No new live data functions added to `data/` — the demo route consumes existing `data.demo` functions.

### Issues

- **Must fix:** None.

- **Should fix:** TC4 (`test_demo_waiver_shell_returns_200`) only asserts status 200 and that the form action string is present. It does not check for position radio values, stat checkboxes, or the empty-state container. The original bug — metadata columns appearing as stat chips — was caught by manual QA, not by TC4. If `stat_cols` regresses again (returns metadata columns or is unexpectedly empty), TC4 passes. TC1 sets a good precedent: assert the 6 position values and the expected stat chip values for the demo route too. Logging to `docs/improvements.md`.

- **Nit:** `from data import demo as demo_module` is placed inside the `demo_waiver_shell` function body rather than at module level. It matches the ticket's reference implementation exactly and causes no problems, but it's inconsistent with every other import in the file. The only reason to inline it would be to defer a slow or side-effectful import — `data.demo` is neither. Could be moved to the top of the file with the rest.

### Verdict: APPROVED

Implementation is correct, clean, and complete. All 7 acceptance criteria pass per the QA report (307/307 tests). The TC4 coverage gap is logged for a future pass and does not block merge.
