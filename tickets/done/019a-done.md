## Implementation complete — 019a

**What I did:**
- Added `_merge_pool` helper to `web/routes/waiver.py` (ported from `pages/03_waiver_wire.py` lines 130–143 exactly).
- Added `_waiver_post_impl` shared helper that handles the per-stat cache loop, `filter_by_position`, `rank_players` with missing-column guard, pagination with clamping, and demo path bypass.
- Added `POST /api/waiver/players` (authenticated, `Depends(require_user)`) on `router`.
- Added `POST /demo/api/waiver/players` (public, no auth) on `public_router`.
- Added imports: `pd`, `Form`, `_is_rate_stat`, `filter_by_position`, `rank_players`, `cache`, `fetch_season_pool`, and `PAGE_SIZE = 25`.
- Created `web/templates/waiver/_table.html`: HTMX fragment with the dark-themed table card (CSS ported from `pages/03_waiver_wire.py` lines 576–665), player name + meta + status badge in first column (sticky), per-stat value cells (`.2f` for rate stats, `.0f` for counting, `—` for NaN), Prev/Next pagination buttons with `hx-post`/`hx-include`/`hx-vals`, footer with total rows and page info.
- Created `tests/test_waiver.py` with 13 tests covering `_merge_pool` (4 unit tests), empty-state, authenticated POST with table, unauthenticated 302, demo POST with table, pagination page 0 and 1, page clamping, cache-hit skipping API, position filter returning no rows, and demo with no cache writes.

**Files changed:**
- `web/routes/waiver.py` — extended with `_merge_pool`, `_waiver_post_impl`, `POST /api/waiver/players`, `POST /demo/api/waiver/players`, and new imports
- `web/templates/waiver/_table.html` — new HTMX fragment template
- `tests/test_waiver.py` — new test file (13 tests)

**Acceptance criteria status (self-check):**
- [x] `POST /api/waiver/players` with `stats=[]` returns 200 HTML with empty-state message and no `<table>` — verified by TC1 (`test_waiver_post_empty_stats_returns_empty_state`)
- [x] `POST /api/waiver/players` with `stats=["Goals"]`, `position="All"`, `period="Season"` returns 200 HTML with `<table>`; second identical request within 24h served from cache with no Yahoo API call — verified by TC2 (`test_waiver_post_with_stats_returns_table`) and TC7 (`test_waiver_post_cache_hit_skips_api`)
- [x] `POST /api/waiver/players` with no session cookie returns 302 to `/auth/login` — verified by TC3 (`test_waiver_post_no_cookie_returns_redirect`)
- [x] `POST /demo/api/waiver/players` with no session cookie returns 200 HTML with `<table>`; no Yahoo API calls; no cache files written — verified by TC4 (`test_demo_waiver_post_returns_table_no_yahoo_calls`) and TC9 (`test_demo_waiver_post_no_cache_writes`)
- [x] Pagination: `page=0` returns ≤25 rows; `page=1` returns next slice; `page=99` on 30-row set clamped to page 1 (5 rows, no 500) — verified by TC5 (`test_waiver_post_pagination_page0_and_page1`) and TC6 (`test_waiver_post_page_clamped_to_last`)

**How to verify (for QA):**
1. `POST /api/waiver/players` body `stats=&position=All&period=Season&page=0` with valid session — response contains empty-state message, no `<table>`.
2. `POST /api/waiver/players` body `stats=Goals&position=All&period=Season&page=0` — first call hits Yahoo (confirm log or mock), writes cache; second identical call within 24h hits cache (no API call). Both return 200 with `<table>`.
3. `POST /api/waiver/players` with no `session_id` cookie — 302 to `/auth/login`.
4. `POST /demo/api/waiver/players` body `stats=Goals&position=All&period=Season&page=0` (no cookie) — 200 with `<table>`; confirm no parquet files created under `.cache/` and no live API calls in logs.
5. Using a 30-player demo fixture: `page=0` → 25 rows, "Page 1 of 2"; `page=1` → 5 rows, "Page 2 of 2"; `page=99` → clamped to page 1, 5 rows, no 500.
6. Manual: load `/waiver`, select a stat chip → HTMX swaps in the table without a full page reload. Change position pill → table re-renders. Next → page 2 → Prev → page 1; position and chip state preserved (via `hx-include="#waiver-filters"`).
7. `position=G` with `stats=Goals` — goalies pool has no Goals column; confirm empty-result message renders, not a 500.
8. Run `python3.11 -m pytest tests/test_waiver.py tests/test_waiver_routes.py -v` — 20 tests pass.

**Scope notes:**
- "Last 30 days" period radio renders in the shell but `_waiver_post_impl` treats all period values as "Season" per the ticket's out-of-scope clause. The `period` param is received and ignored. Ticket 019b enables this.
- `_is_rate_stat` is imported as a private function from `analysis/projection.py`. Flagged here per ticket note: promote to a public name (`is_rate_stat`) when `projection.py` is next touched.
- The `cats` variable in the demo branch of `_waiver_post_impl` is fetched but not used (demo path does not need `name_to_id`/`id_to_name` — the full pool is pre-merged). This is harmless and consistent with the ticket spec.

**Known limitations / things I couldn't fully test:**
- The cache TTL path (second request within 24h is a cache hit) was verified via mock (`is_player_pool_stale=False`), not with a live parquet file. The actual parquet read/write path requires pyarrow which is not installed in this Python environment (pre-existing environment issue — `test_cache.py` has 18 identical failures). Integration verification requires a live Yahoo session.
- Browser HTMX behaviour (no full-page reload on stat chip select, Prev/Next preserving filter state) was not verified — requires a running server and browser session. The `hx-include="#waiver-filters"` attribute is present in `_table.html` pagination buttons and correct per the HTMX docs.
- NaN rendering in the template uses `v == v` (False for NaN) — this is the standard Jinja2 approach since Jinja does not expose `pd.notna`. Verified works with the test fixture.
