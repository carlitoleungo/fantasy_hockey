# 032 — Waiver wire multi-position filter

## Status
done

<!-- PM 2026-07-04: Un-blocked. tests/test_waiver.py added to Touches (was an
oversight — see Notes "Test coverage"). Code for the two app files is already done and
self-verified (tickets/032-done.md); re-orchestration should carry that work forward,
fix the one rename-broken test, and land the AC coverage. -->


## Type
feature

## Process
full

## Touches
- web/routes/waiver.py
- web/templates/waiver/index.html
- tests/test_waiver.py

## Why
On the waiver wire page a manager can currently pick only one position at a time (the
Position control is single-select radio pills: All / C / LW / RW / D / G). Managers
routinely hunt for dual-eligible players — "show me everyone eligible at C **or** LW" —
and today that means running two separate searches and mentally merging them. This ticket
lets the user select multiple positions at once and see the combined, ranked pool in one
table.

## Acceptance criteria
- [ ] `GET /demo/waiver` returns 200 and the Position control renders
  `<input type="checkbox" name="positions">` options for C, LW, RW, D, and G (the position
  inputs are checkboxes, not `type="radio"`).
- [ ] `POST /demo/api/waiver/players` with two position values (`positions=C` and
  `positions=LW`) plus at least one stat selected returns a table fragment in which every
  listed player is eligible at C or LW (no player whose `display_position` is only D, G, or
  RW appears).
- [ ] `POST /demo/api/waiver/players` with `positions=D` and `positions=G` returns the
  **union**: at least one D-eligible player and at least one G-eligible player both appear
  in the same table.
- [ ] `POST /demo/api/waiver/players` with no position values submitted (or `positions=All`)
  returns players spanning more than one position group — i.e. the current default
  "all positions" behaviour is preserved.

## Out of scope
- Any change to `data/cache.py` or its on-disk layout (the pool cache is already keyed by
  position — reuse those keys).
- Any change to `analysis/waiver_ranking.py` (`filter_by_position` stays single-position;
  call it per selected position and union, or rely on the per-position API fetch).
- Any change to `data/players.py` / `data/client.py` fetch functions.
- Stat-category or period (Season / Last 30 days) controls — leave them exactly as they are.
- Persisting position selection across page loads / server-side state.

## Notes for the Engineer
- **Current single-select mechanics** (read before changing):
  - Template `web/templates/waiver/index.html` lines ~25–41: position pills are
    `<input type="radio" name="position" value="...">` inside a `{% for pos in ["All","C","LW","RW","D","G"] %}`
    loop. The form uses `hx-trigger="change"` and resets `#page-input` to 0 on change, so
    HTMX re-POSTs automatically — keep that wiring.
  - Route `web/routes/waiver.py`: both POST handlers take `position: str = Form("All")`
    (lines ~293 and ~316) and pass it into `_waiver_post_impl(position, ...)`.
  - Inside `_waiver_post_impl`: the live branch uses `position` for the API filter and
    cache key — `api_position = None if position == "All" else position` (line ~170), then
    per-stat `cache.is_player_pool_stale/read_player_pool/write_player_pool(league_key,
    position, stat)` and `fetch_season_pool(..., position=api_position)` (lines ~176–187).
    The final in-memory filter is `filter_by_position(base_df, position)` at line ~246,
    used by **both** live and demo paths.
- **Required change shape (route + template only):**
  1. Template: convert the position radios to `<input type="checkbox" name="positions">`
     for C/LW/RW/D/G. Keep an "All" option (default-checked) representing "no position
     filter". Add a small `hx-on:change` / Alpine handler so checking a specific position
     clears "All" and checking "All" clears the specifics — mirror the existing pill
     styling (the stat-category chips at lines ~61–70 are the checkbox pattern to copy).
  2. Route: change the form field on both POST handlers to
     `positions: list[str] = Form([])` and thread a list into `_waiver_post_impl`.
     Normalise server-side: **empty list or a list containing `"All"` ⇒ treat as "All"
     (no position filter, fetch the "All" pool as today).**
  3. Live fetch branch: when specific positions are selected, **loop the existing
     per-stat fetch over each selected position** — reuse `cache.*_player_pool(league_key,
     <pos>, stat)` with each position string and `fetch_season_pool(..., position=<pos>)`,
     then `_merge_pool` everything into one `season_pool`. Do NOT collapse to a single
     "All" fetch — see the sparse-position note below.
  4. Final filter: replace `filter_by_position(base_df, position)` with a union across the
     selected positions, e.g. `pd.concat([filter_by_position(base_df, p) for p in
     selected])` de-duplicated on `player_key`; "All"/empty means no filter (return
     `base_df`). This path serves demo too, giving demo parity for free.
- **Why per-position fetch matters (do not skip):** `fetch_season_pool` returns only the
  top-25 players per stat sort (`count=25`). Fetching one "All" pool would crowd out sparse
  positions (D, G) — you must ask Yahoo for each position's pool separately so a D/G search
  returns real results. The archive Streamlit page documents this at
  `pages/03_waiver_wire.py` ~lines 247–249.
- **`display_position` is composite** (`docs/LEARNINGS.md`): values like `"C,LW"` — always
  split on comma when matching a position. `filter_by_position` already does this correctly;
  don't reimplement matching.
- Historical note: the Streamlit prototype was single-select too, so there is no prior
  behaviour to match — this is net-new UX. Follow the checkbox pattern already used by the
  stat-category chips in the same template for visual consistency.
- Not an architectural surface: no OAuth, cache-layer, API-client, routing/middleware, or
  template shell/fragment-split changes — no Tech Lead consult required.
- **Test coverage (`tests/test_waiver.py` — in Touches):** this file was missing from the
  original Touches; that was an oversight (tickets 019a/019b, same route surface, both
  listed it), corrected 2026-07-04. Two required changes:
  1. **Fix the one rename-broken test.** `test_waiver_post_position_no_matching_rows`
     (`tests/test_waiver.py:358`) posts the removed `position=G` field — update it to post
     `positions=["G"]`. This is the only regression the `position`→`positions` rename
     introduces (full suite was `1 failed, 384 passed` for this reason alone).
  2. **Add committed AC coverage** — one test per acceptance criterion, plus `positions=All`
     and the per-position live-fetch-loop assertion. A proven-green draft (7 tests) already
     exists at
     `/private/tmp/claude-501/.../ccad68c1-061c-4aa9-bde6-cbb0322adcc4/scratchpad/proposed_tests_032.py`
     — reuse it if the path still resolves; if it doesn't (session scratchpad may be gone),
     re-derive from the AC list above and the self-check notes in `tickets/032-done.md`.
     Confirm the full suite is green before handoff to QA.
- The `analysis/waiver_ranking.rank_players` NaN-composite ranking behaviour the code author
  flagged (D+G ranked on disjoint skater/goalie stats buries one group on later pages) is
  **out of scope here** and logged separately in `docs/backlog.md`. Do not touch
  `analysis/waiver_ranking.py`. If AC3 needs a deterministic assertion, use a fixture where a
  D and a G share the ranking stat (as the draft tests do).

## Verification
- Run the app (`uvicorn web.main:app --reload`) and open `/demo/waiver` (no auth needed).
- Confirm the Position control shows checkboxes; select **C + LW**, then pick a couple of
  skater stats (e.g. Goals, Assists). Confirm the ranked table lists only players whose Pos
  includes C or LW, and that selecting C+LW yields a superset of selecting C alone.
- Select **D + G** and a relevant stat; confirm both defencemen and goalies appear together.
- Deselect all positions (or pick "All"); confirm players from multiple position groups
  appear (default behaviour unchanged).
- Confirm changing the position selection auto-refreshes the table (HTMX `change` trigger)
  and resets to page 1.
- Live-mode smoke check (requires a logged-in Yahoo session): on `/waiver`, select two
  positions and confirm the table populates without error and that a sparse-position pick
  (e.g. G) still returns goalies — this exercises the per-position fetch loop and the
  existing per-position cache keys. If no live session is available, note it; the demo
  steps above are the authoritative acceptance path.

## Dependencies
- None (independent of the 028–031 projection chain).
