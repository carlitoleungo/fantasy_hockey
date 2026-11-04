> Written under the old ticket workflow (pre-2026-11-04). References to `tickets/`, `docs/ROADMAP.md`, `docs/backlog.md`, `docs/improvements.md` or persona roles point to files now removed; read them with `git show 409b7ab:<path>`. "Touches" is guidance, not a hard limit.

# 047 — NHL per-night slate: expose the dates `get_remaining_games` throws away

## Status
ready

## Type
feature

## Milestone
none

## Touches
- data/schedule.py
- data/demo.py
- demo/data/nightly_slate.json
- tests/test_schedule.py

## Why
The app can tell a manager *how many* games a waiver-wire player's team has left this week, but
not *which nights* they fall on. Every downstream question the owner actually wants answered —
"is this an off-night pickup?", "could I start him on all those nights?" — needs per-night
granularity, and today `data/schedule.py` deliberately discards it: the parse already walks
`gameWeek[] → date → games[]` and then collapses everything into `nhl_counts[abbr] += 1`. This
ticket recovers the dates from the NHL response the app already fetches. It is a pure re-parse:
no new endpoint, no new auth, and no additional HTTP calls.

## Acceptance criteria
- [ ] `data.schedule.get_nightly_slate(from_date, to_date)` returns `{"YYYY-MM-DD": [nhl_abbr, ...]}`
      covering the **whole league's** slate for each date in range (not a filtered subset), with
      each game contributing both its away and home team, abbrs sorted, and dates with no
      qualifying games absent from the mapping.
- [ ] The new function applies the same filters as `get_remaining_games`: `_COUNTED_GAME_TYPES`
      only, `_FINAL_STATES` excluded, LIVE counted, de-duplicated by game id, and the same
      two-window fetch when the range spans 7+ days.
- [ ] `get_remaining_games` produces identical results to today and makes the same number of HTTP
      calls: the existing `tests/test_schedule.py` suite passes **unmodified**, verified by
      patching `data.schedule._nhl_get` and asserting its call count for both a short and a
      7+-day range.
- [ ] A public `to_nhl_abbr(yahoo_abbr)` helper maps Yahoo 2-letter abbrs to NHL 3-letter codes
      via the existing `_YAHOO_TO_NHL` table, so callers can look a Yahoo-sourced team up in the
      slate; unknown abbrs pass through unchanged.
- [ ] `data.demo.load_nightly_slate()` returns the same shape from a committed
      `demo/data/nightly_slate.json` snapshot whose dates and teams are consistent with the
      existing `demo/data/games_remaining.json` counts.

## Out of scope
- Caching the NHL schedule response. It is uncached today by an active decision (see Notes) and
  stays that way in this ticket.
- Any off-night rule, threshold, or league-proportion maths — ticket 048.
- Any route or template change — ticket 049.
- Per-team date lists as a separate return shape. The full slate is a superset; callers invert it.

## Notes for the Engineer
- **Read first:** `data/schedule.py` in full (the parse loop is ~lines 77–97), and
  `data/demo.py:99` (`get_games_remaining`) for the demo counterpart pattern.
- **Design requirement — one fetch, not two.** Build the slate as the primitive and make
  `get_remaining_games` a thin consumer of it (filter the slate to the requested abbrs, count).
  If both functions each drive their own `_nhl_get` calls, ticket 049's page doubles the live
  third-party calls on the "Last 30 days" hot path, which the cache decision below explicitly
  calls out as already a concern. Keep `get_remaining_games`'s signature and return type exactly
  as they are — `web/routes/waiver.py:251` and `web/routes/projection.py:154` both call it.
- **Return NHL abbrs, not Yahoo abbrs, in the slate.** Mapping back is only well-defined for the
  abbrs a caller asked for (`get_remaining_games` can do it because it has the input list); a
  whole-league slate cannot. Hence the `to_nhl_abbr` helper in the criteria.
- **Layer purity:** `data/` is framework-free pure Python (`docs/ARCHITECTURE.md` Key patterns
  #6). No pandas needed here — plain dicts and lists.
- **DECISIONS.md entries this ticket must conform to** (all verified active in `docs/DECISIONS.md`;
  none of these are the superseded copies in `docs/archive/decisions-superseded.md`):
  - **2026-07-23 "Cache: league-independent data gets a shared tier at M2; M1 only preserves the
    affordance"** — this is the covering decision for *where NHL schedule data lives*. It names
    `schedule.get_remaining_games` explicitly, records that the NHL schedule is league-independent
    and **not cached at all**, and defers the shared tier to M2. So: do not add a cache tier, do
    not add a `CACHE_DIR/_shared/` path for this, and do not treat "it's uncached" as a defect.
  - **2026-05-30 "Web routes: demo route pairing policy"** — demo counterparts may only be
    deferred with a backlog ticket filed in the same commit. This ticket does not defer: the demo
    counterpart ships here, which is why `data/demo.py` and the snapshot JSON are in `Touches`.
  - **2026-07-26 "Tests: one module per feature surface, named for the surface"** — the new tests
    belong in the existing `tests/test_schedule.py`, not a new author-named module.
  - **2026-07-03 "Dev/test: no runtime past-week override; use captured fixtures + demo mode
    instead"** — test with fixture payloads patched over `_nhl_get`; do not add a date override
    knob to make off-season testing easier.
- **LEARNINGS.md gotchas that apply:** "Tests must patch the importing module's namespace" —
  patch `data.schedule._nhl_get`, and note `web.routes.waiver.get_remaining_games` /
  `web.routes.projection.schedule_module.get_remaining_games` are the existing patch targets in
  the route tests, which must keep working. "Off-season → no live data" — the NHL API returns an
  empty `gameWeek` off-season, so the slate must return `{}` rather than raising.
  The xmltodict / `_as_list` / `_coerce` gotchas do **not** apply: the NHL API is plain JSON, not
  Yahoo XML.
- **Open `docs/improvements.md` items on files in `Touches`:**
  - `data/schedule.py:37` — "Cross-league duplication: `ww_lastmonth` and NHL schedule are cached
    per league or not at all", **Type: quality**. Normally the Engineer's input #6 would sweep
    this, but **it is explicitly out of scope here**: DECISIONS 2026-07-23 defers exactly this
    item to M2, and the item's own text says so. Leave it open, do not close it, do not
    partially implement it.
  - `data/demo.py`, `demo/data/nightly_slate.json`, `tests/test_schedule.py` — none.

## Verification
- `.venv/bin/python -m pytest tests/` — full suite green, with `tests/test_schedule.py`'s
  pre-existing cases unedited.
- Confirm the HTTP-call count is unchanged: patch `data.schedule._nhl_get`, call
  `get_remaining_games` over a 3-day range (expect 1 call) and a 10-day range (expect 2).
- Demo-mode step (this ticket adds a `data/` function, so demo parity is in scope): in a Python
  shell, `from data import demo; demo.load_nightly_slate()` returns a non-empty
  date → team-list mapping, and for a team present in `demo/data/games_remaining.json` the number
  of dates that team appears on equals its games-remaining count.
- "Done" in the running app: **nothing visible changes.** This is a data-layer ticket; the waiver
  and projection pages must render exactly as before. Spot-check `/waiver` with "Last 30 days"
  and `/projection/matchup` to confirm the GR column and projection numbers are unchanged.

## Dependencies
- None. (But see the audit note in the PM handoff — `scripts/audit_due.py` reads AUDIT DUE.)
