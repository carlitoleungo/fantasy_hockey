## Implementation complete — 019b

**What I did:**
- Added `period` branching to `_waiver_post_impl`: when `period == "Last 30 days"`, builds `lm_pool` from cache + fetch, merges with season metadata, falls back to season stats if `lm_pool` is empty.
- Added games-remaining fetch block (wrapped in `try/except`): reads matchups df → derives `current_week` → calls `get_current_matchup` → calls `get_remaining_games` → maps result onto `ranked_df["games_remaining"]`. Any error produces an empty map and the table still renders.
- Demo path for `period == "Last 30 days"` uses `demo_module.load_lastmonth_pool()` and `demo_module.get_games_remaining()` — no cache reads, no Yahoo calls.
- Added `period` to the empty-state context dict so the template never errors on an undefined variable.
- Passed `period` through to `_table.html` in the main response context.
- Removed dead `cats = demo_module.get_stat_categories()` line from the demo branch (improvements.md item, file was in Touches).
- Updated `_table.html`: GP and GR column headers appear when `period == "Last 30 days"`; per-row GP and GR cells render as integers or `—` for null/NaN; footer left-side text switches between "last 30 days stats" and "season stats" based on `period`.
- Added 6 new tests (TC10–TC15) covering: lastmonth returns GP column + correct footer, season path unchanged, demo lastmonth no Yahoo/cache calls, `get_matchups` returns None → no 500, `get_current_matchup` raises → no 500, empty `lm_pool` → fallback to season stats.
- Closed improvements.md item: dead `cats` variable in demo branch.

**Files changed:**
- `web/routes/waiver.py` — added imports (`date`, `fetch_lastmonth_batch`, `get_remaining_games`, `get_current_matchup`); added lastmonth branch and games-remaining block to `_waiver_post_impl`; removed dead `cats` line; added `period` to both response contexts.
- `web/templates/waiver/_table.html` — GP and GR columns gated on `period == "Last 30 days"`; footer text conditional on period.
- `tests/test_waiver.py` — updated module docstring; added `_make_lastmonth_pool`, `_make_matchups_df`, `_make_matchup_dict` helpers; added TC10–TC15.
- `docs/improvements.md` — closed dead-`cats` item.

**Acceptance criteria status (self-check):**
- [x] AC1: `POST /api/waiver/players` with `period="Last 30 days"` and at least one stat returns 200 HTML with a `games_played` column and footer reading "last 30 days stats" — verified by TC10 (`test_waiver_post_lastmonth_returns_gp_column_and_footer`): asserts status 200, `<table` present, `last 30 days stats` in body, `>GP<` in body.
- [x] AC2: `POST /api/waiver/players` with `period="Season"` renders identically to 019a — verified by TC11 (`test_waiver_post_season_footer_unchanged`): asserts `season stats` in body, `last 30 days stats` absent, `>GP<` absent, `>GR<` absent.
- [x] AC3: `POST /demo/api/waiver/players` with `period="Last 30 days"` returns 200 HTML with a games-remaining column; no Yahoo API calls and no cache writes occur — verified by TC12 (`test_demo_waiver_post_lastmonth_no_yahoo_no_cache`): asserts 200, `<table`, `last 30 days stats`; `mock_upsert.assert_not_called()`, `mock_fetch.assert_not_called()`, `mock_matchup.assert_not_called()`.
- [x] AC4: When `get_matchups` returns None or the games-remaining fetch throws, the table still renders with `games_remaining == 0` for all players; no 500 — verified by TC13 (matchups None) and TC14 (`get_current_matchup` raises): both assert status 200, `<table` present.
- [x] AC5: When `lm_pool` is empty after both cache read and fetch, `base_df` falls back to `season_pool` and the table renders with season stats; no 500 — verified by TC15 (`test_waiver_post_lastmonth_empty_lm_pool_falls_back_to_season`): asserts 200, `<table`, `Player 0` (season data) in body.

**How to verify (for QA):**
1. Start the app: `uvicorn web.main:app --reload` from `/Users/carlin/dev/fantasy_hockey`.
2. Log in, navigate to `/waiver`, select a stat (e.g. Goals), select "Last 30 days" radio — confirm table re-renders, footer reads "last 30 days stats", GP and GR columns appear after the Player column.
3. Switch back to "Season" radio — confirm GP and GR columns disappear, footer reverts to "season stats".
4. Navigate to `/demo/waiver`, select a stat, select "Last 30 days" — confirm 200 HTML with GP/GR columns; check server logs to confirm no Yahoo HTTP calls and no cache writes.
5. Run the test suite: `.venv/bin/python -m pytest tests/test_waiver.py -v` — all 19 tests pass.
6. To verify the games-remaining fallback, mock `get_matchups` to return None (or temporarily disconnect network) and confirm the table renders without error with `—` in the GR column.

**Scope notes:**
- Demo mode `load_lastmonth_pool()` returns a DataFrame that may or may not include `team_abbr` depending on how the demo snapshot was generated. The code guards `ranked_df["games_remaining"]` assignment with `"team_abbr" in ranked_df.columns` to handle both cases safely.
- Demo `get_games_remaining()` reads from `demo/data/games_remaining.json`. If that file is absent, `get_games_remaining()` returns `{}`, the guard `games_remaining_map` is falsy, and no GR column is added. This is correct behavior — a follow-up ticket should verify the demo snapshot file exists and has correct data.

**Known limitations / things I couldn't fully test:**
- The GR column values in the live authenticated path depend on a live NHL schedule API call (`data/schedule.get_remaining_games`). The test mocks this; the actual values were not verified against a live league.
- GAA recomputation in `fetch_lastmonth_batch` is performed inside `data/players._parse_stats` (confirmed at lines 289–293) before the result reaches `_waiver_post_impl`. The route does not re-derive GAA. Verified by code inspection only; no end-to-end test with a real GAA fixture was run.
- Browser-side: selecting "Last 30 days" radio triggers an HTMX form change event and re-renders the fragment. This was confirmed by code inspection of the `hx-trigger="change"` on `#waiver-filters` in `index.html`; not exercised in a live browser.
