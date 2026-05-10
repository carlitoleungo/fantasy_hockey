# 019a — Waiver Wire: POST handler, season path, pagination, demo mode

## Status
done

## Type
feature

## Touches
- `web/routes/waiver.py`
- `web/templates/waiver/_table.html`
- `tests/test_waiver.py`

## Why
The waiver wire shell (ticket 018) renders a filter form but returns no results — clicking
a stat chip does nothing. Until the POST handler exists, users cannot see available
players ranked by any stat. This ticket wires up the core request/response cycle for the
season stat path: form submission fetches (or cache-hits) a player pool, ranks it, paginates
it, and returns an HTMX fragment without a full page reload. Demo mode is included so
unauthenticated visitors can explore the tool without Yahoo credentials.

## Acceptance criteria
- [ ] `POST /api/waiver/players` with `stats=[]` returns 200 HTML containing the
  empty-state message "Select one or more stat categories above to rank available players"
  and no `<table>` element.
- [ ] `POST /api/waiver/players` with `stats=["Goals"]`, `position="All"`,
  `period="Season"` returns 200 HTML with a `<table>`; a second identical request within
  24 h is served from cache with no Yahoo API call.
- [ ] `POST /api/waiver/players` with no session cookie returns 401.
- [ ] `POST /demo/api/waiver/players` with no session cookie returns 200 HTML with a
  `<table>`; no Yahoo API calls are made and no cache files are written.
- [ ] Pagination: `page=0` returns ≤25 rows; `page=1` returns the next slice; `page=99`
  on a 30-row result set is clamped to the last valid page (5 rows, no 500).

## Out of scope
- Last 30 days stat period — period field is parsed but treated as `"Season"` for all
  values; "Last 30 days" radio may render but must be visually disabled (019b enables it).
- Games-remaining column — omitted entirely from the fragment in this ticket.
- Any changes to `data/`, `analysis/`, or `auth/` layers.

## Notes for the Engineer

**Route shape and auth.** Follow `web/routes/overview.py` — use `Depends(require_user)`
and `Depends(db_dep)`. Form fields: `position: str = Form("All")`,
`stats: list[str] = Form([])`, `period: str = Form("Season")`, `page: int = Form(0)`.
The demo route is registered on the public router (no `require_user`); same form fields.

**Shared helper.** Both routes call `_waiver_post_impl(position, stats, period, page,
request, *, demo=False, session=None, league_key=None)`. Set `form_action` at the top:
```python
form_action = "/demo/api/waiver/players" if demo else "/api/waiver/players"
```
Pass to the template for Prev/Next `hx-post` so the URL is not hardcoded.

**Build both dicts from one call.** `fetch_season_pool` requires `id_to_name` as well as
`sort_stat_id`. Build both from a single `get_stat_categories` call:
```python
cats = get_stat_categories(session, league_key)
name_to_id = {c["stat_name"]: c["stat_id"] for c in cats if c["is_enabled"]}
id_to_name  = {c["stat_id"]: c["stat_name"] for c in cats if c["is_enabled"]}
```

**`_merge_pool`.** Defined in `web/routes/waiver.py` (not in `data/` or `analysis/`).
Union on `player_key`; rows whose `player_key` already exists in `existing` are discarded
from `new_rows`. Port from `pages/03_waiver_wire.py` lines 130–143 exactly.

**Cache key vs API position.** Cache functions take `position` as the string `"All"` or
the abbreviation. `fetch_season_pool`'s `position` kwarg must be `None` for all-positions:
```python
api_position = None if position == "All" else position
```

**Per-stat cache loop.** For each stat in `stats`: if
`not cache.is_player_pool_stale(league_key, position, stat)`, call
`cache.read_player_pool(league_key, position, stat)` and merge via `_merge_pool`. Else
resolve `sort_id = name_to_id[stat]`, call `fetch_season_pool`, write to cache if
non-empty, merge via `_merge_pool`. Stats not in `name_to_id` are silently skipped.

**Guard `rank_players` against missing columns.** Filter stats to columns present before
calling, or it raises `KeyError`:
```python
safe_cats = [s for s in stats if s in filtered_df.columns]
ranked_df  = rank_players(filtered_df, safe_cats)
```

**Pagination.** `PAGE_SIZE = 25`. Slice `ranked_df.iloc[page * PAGE_SIZE : (page + 1) *
PAGE_SIZE]`. If `page >= total_pages`, clamp: `page = max(0, total_pages - 1)`. Prev
button: `disabled` when `page == 0`. Next button: `disabled` when
`page >= total_pages - 1`. Both use `hx-post` with `hx-include="#waiver-filters"` and
`hx-vals='{"page": N}'`.

**Template.** Player name cell: two lines — `player_name` in Newsreader serif (primary);
`team_abbr · display_position` plus inline status badge (DTD / IR / OUT / HEALTHY) from
`pages/03_waiver_wire.py` lines 512–517. First column sticky (`position: sticky; left: 0`).
One column per stat in `stats[]` order; header colour `#90d4c1`. Format: `.2f` for rate
stats via `_is_rate_stat(col)` from `analysis.projection`, `.0f` for counting stats, `—`
for NaN (guard: `pd.notna(v) and isinstance(v, (int, float))`). Footer: left side
"{total_rows} players · season stats"; right side "Page {current_page + 1} of
{total_pages}". CSS (`.ww-card`, `.ww-table`, `.fh-player-name`, `.fh-player-meta`,
`.fh-badge`) from `pages/03_waiver_wire.py` lines 576–665.

**`_is_rate_stat` is private.** `from analysis.projection import _is_rate_stat` works but
flag it in the PR for promotion to a public name when `projection.py` is next touched.

**Demo mode.** When `demo=True`: `season_pool = demo_module.load_season_pool()` (pre-merged;
per-stat loop does not run); `stat_cats = demo_module.get_stat_categories()`. All
`cache.*`, `fetch_season_pool`, and Yahoo calls are skipped.

**Decision references (`docs/decisions.md` 2026-04-19):**
- HTMX fragment pattern: `_table.html` is the fragment swapped into the shell's
  `#waiver-table-container`; route shape follows the shell + fragment split convention.
- League context: `league_key` resolved from session row via `require_user`; routes
  stay bare (`/api/waiver/players`, not `/leagues/{key}/api/waiver/players`).

## Verification
1. `POST /api/waiver/players` with `stats=[]` — response contains the instructional
   message and no `<table>` tag.
2. `POST /api/waiver/players` with `stats=["Goals"]`, `position="All"`, `period="Season"`
   — first call (cache cold) fetches from Yahoo and writes a cache file to disk; second
   identical call within 24 h hits the cache. Both return 200 with a `<table>`.
3. `POST /api/waiver/players` with `page=1` on a 30-player result — fragment shows 5
   rows; Prev enabled; Next disabled.
4. `POST /api/waiver/players` with `page=99` on a 30-player result — clamped to page 1;
   5 rows; no 500.
5. `POST /demo/api/waiver/players` (no cookie) — 200 HTML with `<table>`; confirm no
   cache files created and no live Yahoo calls (check logs or mock).
6. `POST /api/waiver/players` (no cookie) — 401.
7. `position="G"` with stat `"Goals"` — goalie pool likely has no Goals column; confirm
   empty-state message renders, not a 500.
8. Manual: select a stat chip → table appears via HTMX (no full page reload). Change
   position dropdown → table re-renders. Next → page 2 → Prev → page 1; confirm position
   and chip state are preserved.

## Dependencies
- Ticket 018 must be complete (`web/routes/waiver.py` exists, template directory created,
  router registered in `web/main.py`, form shape defined).
- Consumes without changes: `data.cache`, `data.players`, `data.client`,
  `data.demo`, `analysis.waiver_ranking`, `analysis.projection`.
