## Code Review — 015

**Files reviewed:**
- `web/routes/overview.py` — new; `_get_league_key`, `_compute_cell_ranks`, `/overview` shell handler, `/overview/table` fragment handler
- `web/templates/overview/index.html` — new; page shell with week selector and HTMX fragment target
- `web/templates/overview/_table.html` — new; leaderboard table fragment with rank-based color classes
- `web/templates/base.html` — "Overview" nav link added to header
- `web/templates.py` — `rank_color` Jinja filter registered
- `web/main.py` — `overview_router` included
- `requirements-web.txt` — `pandas` added (QA fix)
- `tests/test_overview_routes.py` — new; 6 acceptance-criteria tests

---

### Scope: CLEAN

`requirements-web.txt` was not in the ticket's "files likely affected" list, but the `pandas` addition is a direct consequence of the ticket (first web route that imports from `analysis/`) and was correctly treated as a blocker fix rather than scope creep. No other changes beyond what the ticket specified.

---

### Architecture: CLEAN

- No framework imports in `data/` or `analysis/` ✓
- No per-entity API loops ✓
- `_compute_cell_ranks` is correctly in the route layer, not in `analysis/` ✓
- No new `data/` functions introduced → no demo counterpart required ✓
- `rank_color` correctly registered in `web/templates.py`, not in `__init__.py` ✓

---

### Issues

**Must fix:** None.

**Should fix:**

- **`stat_columns(df)` called twice in `overview()`** (`web/routes/overview.py` lines 66 and 75). Both calls are on the same unmodified `df`. Extract to a local variable (`cols = stat_columns(df)`) before the `_compute_cell_ranks` call and reuse it. Low cost and eliminates the redundant traversal. Logged in `docs/improvements.md`.

**Nit:**

- **`_get_league_key` uses `_` prefix but is designed for cross-module import.** The ticket explicitly specified this name and noted ticket 016 will import it. It works fine — Python's `_` convention is advisory, not enforced. No action needed; just worth knowing when ticket 016 arrives.

- **`rank_color` compares a float rank to an int `team_count`** (`rank == team_count`). Pandas `.rank()` returns floats (e.g. `3.0` not `3`). Python's `==` handles this correctly (`3.0 == 3` is `True`), so this is not a bug — but it's worth noting if the filter is reused in a context where `rank` might be a string or NaN. The existing `None` guard doesn't cover NaN. Low risk for v1.

---

### Verdict: APPROVED

Clean implementation. All 8 acceptance criteria pass (QA confirmed). Architecture rules followed. The `iterrows()` deviation from the ticket's `itertuples()` pseudocode is the right call and is correctly explained in the done file — `itertuples()` can't access columns with spaces by attribute. The QA-caught `pandas` dependency gap was fixed during QA and is now in `requirements-web.txt`.
