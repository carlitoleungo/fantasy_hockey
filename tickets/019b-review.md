## Code Review — 019b

**Files reviewed:**
- `web/routes/waiver.py` — lastmonth branch, games-remaining block, demo path, empty-state period fix
- `web/templates/waiver/_table.html` — GP/GR column headers and cells, footer text conditional
- `tests/test_waiver.py` — TC10–TC15 covering all 019b acceptance criteria
- `docs/improvements.md` — dead-`cats` item closed; no new items added by Engineer

---

### Scope: CLEAN

Diff stays inside the ticket's `Touches` list (`web/routes/waiver.py`, `web/templates/waiver/_table.html`, `tests/test_waiver.py`). The `docs/improvements.md` update closes the dead-`cats` item that was flagged in 019a — this is the explicitly permitted "improvements.md close-out" operation. The 019a ticket lifecycle files moved to `tickets/done/` are administrative and out of scope per the task brief.

---

### Architecture: CLEAN

- **No framework imports in `data/`, `analysis/`, or `auth/`.** The diff is confined to `web/routes/waiver.py` and templates.
- **Bulk endpoint used correctly.** `fetch_lastmonth_batch` is called once with the full set of missing keys — not in a per-player loop. Conforms to the project's "minimise API calls" rule.
- **`_coerce()` / `_as_list()` not bypassed.** Stat parsing happens inside `data/players.py` (unchanged) before results reach the route. The route does not touch raw `stat['value']`.
- **Cache function separation respected.** Season path uses `is_player_pool_stale` / `read_player_pool` / `write_player_pool`; lastmonth path uses `is_lastmonth_stale` / `read_lastmonth_cache` / `upsert_lastmonth_cache`. No cross-contamination.
- **DECISIONS.md entries honoured.** HTMX fragment pattern (2026-04-19): route returns `_table.html` fragment swapped into `#waiver-table-container`. League context (2026-04-19): `league_key` resolved from session via `require_user`; route stays bare (`/api/waiver/players`).
- **No new implicit conventions.** The change uses existing module structure, route shape, and template patterns. No new directory, naming scheme, or session-handling pattern introduced without a DECISIONS.md entry.
- **Demo counterpart present.** `demo_module.load_lastmonth_pool()` and `demo_module.get_games_remaining()` are called in the demo branch. These are calls into the existing `data/demo.py` — not new live data functions in `data/` requiring a new demo counterpart.

---

### Issues

- **should-fix (logged to `docs/improvements.md`):** TC10 (`test_waiver_post_lastmonth_returns_gp_column_and_footer`) asserts `>GP<` but not `>GR<`. AC1 requires both a `games_played` column and a games-remaining column to appear. The test does not assert the GR column header. QA manually confirmed `>GR<` is present, but the test gap means a regression that removes the GR header would not be caught by the suite. Add `assert ">GR<" in body` to TC10.

---

### Verdict: APPROVED

No blockers. One test gap (TC10 missing `>GR<` assertion) logged to `docs/improvements.md`.

**Improvements logged:**
- TC10 missing `>GR<` assertion in `tests/test_waiver.py`.
