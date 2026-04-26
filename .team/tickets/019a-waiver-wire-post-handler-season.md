# 019a — Waiver Wire: POST handler, season path, pagination, demo mode

## Summary
Implement `POST /api/waiver/players` and `POST /demo/api/waiver/players` with the
season stat path only. The handler receives `position`, `stats[]`, `period`, and `page`
on every request; for each selected stat it checks the disk cache and fetches from Yahoo
on a miss. Results flow through `_merge_pool`, position filtering, and `rank_players`,
then are sliced for pagination and rendered as the `web/templates/waiver/_table.html`
HTMX fragment with player name cells, stat columns, and a footer bar. Demo mode is a
separate route prefix that skips all cache and Yahoo calls. `period` is accepted as a
form field but treated as `"Season"` for all values until 019b ships; the Last 30 days
radio may render in the shell but should be visually disabled. Games-remaining column is
omitted entirely (the column does not appear in the fragment).

## Acceptance criteria

### Route shape and auth
- [ ] `POST /api/waiver/players` accepts form fields: `position` (str, default `"All"`),
  `stats` (list[str], default `[]`), `period` (str, default `"Season"`), `page` (int,
  default `0`). Returns an HTML fragment (content-type `text/html`).
- [ ] The route uses `Depends(require_user)` and `Depends(db_dep)`, consistent with
  `web/routes/overview.py`. A missing session returns 401 (handled by the dependency,
  not the handler).
- [ ] `POST /demo/api/waiver/players` is registered on the public router (no
  `require_user`). It accepts the same form fields. It calls `data.demo` equivalents and
  shares the same ranking and rendering logic as the authenticated path.

### Empty-state guard
- [ ] If `stats` is empty, return the `_table.html` fragment containing only the
  instructional message: "Select one or more stat categories above to rank available
  players." No `<table>` element is present in the response.

### Season pool fetch
- [ ] For each stat in `stats`:
  1. If `not cache.is_player_pool_stale(league_key, position, stat)`: call
     `cache.read_player_pool(league_key, position, stat)` and merge into `season_pool`
     via `_merge_pool`.
  2. Else (stale or missing): resolve `sort_id = name_to_id[stat]`; call
     `fetch_season_pool(session, league_key, sort_id, id_to_name, position=api_position)`;
     call `cache.write_player_pool(league_key, position, stat, new_df)` if `new_df` is
     non-empty; merge via `_merge_pool`.
  - `api_position` is `None` when `position == "All"`, otherwise the position string.
    The cache key uses `position` (the string `"All"` or the abbreviation), not
    `api_position`.
  - Stats not found in `name_to_id` are silently skipped.
- [ ] If `season_pool` is empty after processing all stats, return the empty-state
  fragment ("No available players match the selected filters.").

### `_merge_pool`
- [ ] `_merge_pool(existing: pd.DataFrame, new_rows: pd.DataFrame) → pd.DataFrame` is
  defined in `web/routes/waiver.py` (not in `data/` or `analysis/`). Semantics ported
  from `pages/03_waiver_wire.py` lines 130–143: union on `player_key`; rows whose
  `player_key` already exists in `existing` are discarded from `new_rows` — existing
  data is preferred. Used for both the season pool accumulation loop and (in 019b) the
  lastmonth merge.

### Ranking and position filtering
- [ ] `filtered_df = filter_by_position(base_df, position)` from `analysis.waiver_ranking`.
- [ ] Before calling `rank_players`, filter `stats` to columns actually present in
  `filtered_df`: `safe_cats = [s for s in stats if s in filtered_df.columns]`.
- [ ] `ranked_df = rank_players(filtered_df, safe_cats)` from `analysis.waiver_ranking`.
- [ ] If `ranked_df` is empty after filtering, return the empty-state fragment.

### Pagination
- [ ] `PAGE_SIZE = 25`. The handler slices `ranked_df.iloc[page * PAGE_SIZE :
  (page + 1) * PAGE_SIZE]`. If `page >= total_pages`, clamp: `page = max(0,
  total_pages - 1)` before slicing.
- [ ] `_table.html` includes Prev and Next buttons. Each uses `hx-post` targeting
  `#waiver-table-container`, `hx-include="#waiver-filters"` to re-send the current
  filter state, and `hx-vals='{"page": N}'` to override the page number.
  - Prev button: disabled (HTML `disabled` attribute) when `page == 0`.
  - Next button: disabled when `page >= total_pages - 1`.
  - Both buttons use `form_action` (passed in the template context) for `hx-post` so
    the URL is not hardcoded.

### Demo mode
- [ ] A shared helper `_waiver_post_impl(position, stats, period, page, request, *,
  demo=False, session=None, league_key=None)` is called by both routes. When
  `demo=True`:
  - `season_pool = demo_module.load_season_pool()` (pre-merged; per-stat loop does not run).
  - `stat_cats = demo_module.get_stat_categories()`.
  - All `cache.*`, `fetch_season_pool`, and Yahoo API calls are skipped.
  - Period branching and rendering logic run identically to the live path.
- [ ] Demo mode is detected via route path, not a query param or session flag.

### `_table.html` fragment
- [ ] Player name column: two-line cell — `player_name` in Newsreader serif (primary);
  `team_abbr · display_position` plus optional inline status badge (DTD / IR / OUT /
  HEALTHY) ported from `pages/03_waiver_wire.py` lines 512–517. First column is sticky
  (`position: sticky; left: 0`).
- [ ] Games-remaining column is **omitted** from the fragment entirely in 019a.
- [ ] One column per selected stat, in the order of `stats[]`. Header label uses
  `stat_abbrev` (same fallback logic as the shell). Header colour `#90d4c1` for selected
  stats. Format: `.2f` for rate stats (`_is_rate_stat(col)` from `analysis.projection`),
  `.0f` for counting stats, `—` for NaN. Guard formatting: check `pd.notna(v) and
  isinstance(v, (int, float))` before calling `format`.
- [ ] Footer bar inside the card: left side "{total_rows} players · season stats";
  right side "Page {current_page + 1} of {total_pages}".
- [ ] Card and table CSS (`.ww-card`, `.ww-table`, `.fh-player-name`, `.fh-player-meta`,
  `.fh-badge`) embedded in `_table.html` as an inline `<style>` block or in
  `web/static/waiver.css`. Ported from `pages/03_waiver_wire.py` lines 576–665.

### Unit tests
- [ ] `_merge_pool(pd.DataFrame(), fixture_df)` returns a copy of `fixture_df` unchanged.
- [ ] `_merge_pool(fixture_df, overlap_df)` — where `overlap_df` shares one `player_key`
  with `fixture_df` and adds one new row — returns `len(fixture_df) + 1` rows (the
  overlapping row is discarded; the new row is appended).
- [ ] Given a `ranked_df` with 30 rows: `page=0` slice is 25 rows; `page=1` slice is 5
  rows; `page=2` is clamped to page 1 (last valid page) and returns 5 rows.
- [ ] `POST /api/waiver/players` (or the helper called directly) with `stats=[]` returns
  HTML containing the empty-state message and no `<table>` element.

## Files likely affected
- `web/routes/waiver.py` (extend from 018 — add routes, `_merge_pool`,
  `_waiver_post_impl`)
- `web/templates/waiver/_table.html` (new)

## Dependencies
- Requires 018 (`web/routes/waiver.py` exists, template directory created, router
  registered in `web/main.py`, form shape defined).
- Consumes without changes:
  - `data.cache`: `is_player_pool_stale`, `read_player_pool`, `write_player_pool`
  - `data.players`: `fetch_season_pool`
  - `data.client`: `get_stat_categories`
  - `data.demo`: `load_season_pool`, `get_stat_categories`
  - `analysis.waiver_ranking`: `filter_by_position`, `rank_players`
  - `analysis.projection`: `_is_rate_stat`

## Notes for the engineer

**Build both `name_to_id` and `id_to_name` from the same call.**
`fetch_season_pool` requires `id_to_name` as its third argument in addition to
`sort_stat_id`. Build both dicts from a single `get_stat_categories` call at the top of
the live path:
```python
cats = get_stat_categories(session, league_key)
name_to_id = {c["stat_name"]: c["stat_id"] for c in cats if c["is_enabled"]}
id_to_name  = {c["stat_id"]: c["stat_name"] for c in cats if c["is_enabled"]}
```
Omitting `id_to_name` causes a `NameError` on the first fetch call.

**Guard `rank_players` against missing stat columns.**
`rank_players` does `result[col]` for each selected category. If a stat column is absent
from `filtered_df` (e.g. a goalie stat requested with `position="C"`), it raises
`KeyError`. Always filter before calling:
```python
safe_cats = [s for s in stats if s in filtered_df.columns]
ranked_df = rank_players(filtered_df, safe_cats)
```

**`_merge_pool` is one function.**
It handles both the season pool accumulation loop and (in 019b) the lastmonth pool
build — the same union-on-`player_key` semantics apply to both. Port it exactly from
`pages/03_waiver_wire.py` lines 130–143; do not simplify.

**Cache key vs API position.**
Cache functions accept `position` as the string `"All"` or a position abbreviation.
`fetch_season_pool`'s `position` kwarg must be `None` for all-positions and the
abbreviated string otherwise. Map at the handler boundary:
```python
api_position = None if position == "All" else position
```

**`period` is accepted but ignored in 019a.**
The form field is parsed and passed through `_waiver_post_impl` so the template can
render the radio, but all period values are treated as `"Season"`. If the shell renders
a "Last 30 days" radio button, disable it (`disabled` attribute) or add a tooltip
indicating the feature is coming soon. Remove the disable/tooltip in 019b.

**`form_action` in the fragment context.**
Set at the top of `_waiver_post_impl`:
```python
form_action = "/demo/api/waiver/players" if demo else "/api/waiver/players"
```
Pass it to the template so Prev/Next `hx-post` values are correct without hardcoding.

**`_is_rate_stat` is a private function.**
`from analysis.projection import _is_rate_stat` works for v1 but is fragile. Flag it
in the PR for promotion to a non-underscore name when `projection.py` is next touched.

**Formatting guard.**
Before `format(v, fmt)`, always check `pd.notna(v) and isinstance(v, (int, float))`
and fall back to `"—"`. `rank_players` should have coerced string `'-'` values, but
guard defensively.

## Notes for QA
- Test 1: `POST /api/waiver/players` with `stats=["Goals"]`, `position="All"`,
  `period="Season"` — first call (cache cold) fetches from Yahoo and writes to disk;
  second call within 24 hours is a cache hit. Both return 200 HTML with a `<table>`.
- Test 2: `POST /api/waiver/players` with `stats=[]` → HTML contains the empty-state
  message and no `<table>`.
- Test 3: `POST /api/waiver/players` with `page=1` on a result set of 30 players →
  fragment shows 5 rows; Prev button is enabled; Next button is disabled.
- Test 4: `POST /api/waiver/players` with `page=99` on a result set of 30 players →
  clamped to page 1; fragment shows 5 rows; no 500.
- Test 5: `POST /demo/api/waiver/players` (no session cookie) → 200 HTML; no Yahoo API
  calls made and no cache writes occur.
- Test 6: `POST /api/waiver/players` with no session cookie → 401 (or 302, per
  `require_user`).
- Edge case: `position="G"` with stat `"Goals"` — goalie pool may have no Goals column;
  `safe_cats` is empty; confirm empty-state message renders, not a 500.
- Edge case: stale cache (manually set mtime on a cache file) → next POST triggers a
  fresh Yahoo fetch and overwrites the cache.
- Manual: select a stat chip → table appears; change position → table re-renders.
  Confirm each filter change is an XHR to `/api/waiver/players`, not a full page reload.
- Manual: Next → page 2 → Prev → back to page 1. Confirm position, period, and chip
  state are preserved across pagination.
