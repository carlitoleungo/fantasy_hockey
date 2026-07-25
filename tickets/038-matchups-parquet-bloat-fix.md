# 038 — Fix matchups.py re-fetch loop that bloats the parquet on every page load

## Status
ready

## Type
bug

## Milestone
m1

## Model
opus

## Touches
- data/matchups.py
- tests/test_matchups.py

## Why
On every page load for the rest of a given day, `get_matchups()` re-fetches `prev_week`
(and always `current_week`) from Yahoo and **appends** the rows to the matchups parquet.
The data stays correct in memory — `drop_duplicates(keep="last")` on read collapses the
duplicates — but the parquet grows by up to two rows-per-team per session and adds read +
rewrite latency on every load, unbounded over a season. The M1 deployment's 1 GB volume
sizing (DECISIONS 2026-07-23 "Deployment: M1 shape") explicitly assumes `matchups` growth
is bounded "once the parquet-bloat bug is fixed", so this closes for M1: an M1 friend
loading Overview repeatedly across a day should not pay steadily rising latency for a table
whose real content never changes. This resolves the `docs/improvements.md` bug **"matchups.py
re-fetch loop causes parquet bloat and unnecessary API calls"** (discovered 2026-03-30).

## Acceptance criteria
- [ ] Calling `get_matchups()` repeatedly within the same day (same `current_week`, cache last-written today) does not grow the on-disk matchups parquet: after the second and subsequent calls the parquet row count equals the number of distinct `(team_key, week)` pairs, not `distinct_pairs + rows_appended_per_call`.
- [ ] `current_week` is still re-fetched and reflected on every call (the always-re-fetch behaviour from DECISIONS 2026-05-31 is preserved) — a test where `current_week` stats change between two calls shows the updated values in the returned DataFrame.
- [ ] The returned DataFrame is unchanged in shape and content from today's behaviour for the normal delta-fetch cases (empty cache first run, partial cache filling missing weeks, prev_week same-day re-fetch) — existing `tests/test_matchups.py` cases still pass.
- [ ] A test asserts the parquet stays clean directly (read the file after N same-day calls and assert no duplicate `(team_key, week)` rows exist on disk, not merely after the read-side dedup).
- [ ] `.venv/bin/python -m pytest tests/` is green.

## Out of scope
- **`data/cache.py`** — do not modify the cache layer here. The atomic-write + locking
  hardening is ticket 037; this ticket uses the existing `cache.read`/`cache.write` API. If
  you conclude the clean fix needs a cache-layer change, stop and flag it rather than
  widening scope.
- The `current_week`-always-re-fetched behaviour itself (DECISIONS 2026-05-31) — keep it.
  This ticket removes the *duplicate accumulation*, not the re-fetch.
- The separate `docs/improvements.md` item "League settings and stat categories re-fetched
  from Yahoo on every request" — different bug, different fix (that one is M2 rate-limit
  work touching `data/client.py`). Do not fold it in.
- Any change to the delta-fetch week-selection logic (`_last_cached_week`, the
  `weeks_to_fetch` construction) beyond what's needed to stop the bloat.

## Notes for the Engineer
- **Prescribed fix — the dedup-then-overwrite approach (improvements entry, Option 2).**
  After building `rows`, instead of `cache.append(league_key, "matchups", pd.DataFrame(rows))`
  at `data/matchups.py:67`, merge the new rows with the existing cached frame, drop
  duplicates on `(team_key, week)` keeping the newly fetched rows, and `cache.write()`
  (overwrite) the deduplicated frame. This absorbs both the `prev_week` same-day re-fetch and
  the unconditional `current_week` append without changing which weeks get fetched — the
  parquet stays clean regardless of how many times the re-fetch runs. The improvements entry
  lists a "per-week staleness check" as an alternative; prefer the overwrite approach — it is
  simpler and also absorbs the intended `current_week` growth.
- The existing read-side `drop_duplicates(subset=["team_key", "week"], keep="last")` at
  `data/matchups.py:74-76` becomes redundant once the parquet is clean, but **keep it** as
  cheap defence against any pre-existing bloated parquet already on the volume (it will
  self-heal on the next write). Do not rely on it as the fix — AC4 checks the *on-disk* file.
- Preserve fetch ordering when overwriting: the current code prepends `prev_week`
  (`data/matchups.py:54`) and the fetched rows must win over stale cached copies of the same
  `(team_key, week)`. `keep="last"` with existing-rows-first, new-rows-appended before the
  dedup gives the newer fetch priority — mirror the `keep="last"` semantics the read path
  already uses.
- **DECISIONS to conform to:** `docs/DECISIONS.md` **"matchups.py: current_week always
  re-fetched to reflect intra-week stats" (2026-05-31)** (do not regress this) and
  **"matchups.py: delta fetch uses max(week) from cache data, not last_updated timestamp"
  (2026-03-03)** (`_last_cached_week` stays as-is).
- **Sequencing:** land after ticket 037 so the overwrite runs against the hardened,
  atomic `cache.write()`. Functionally 038 does not require 037's internals, but doing 037
  first avoids re-verifying the matchups write path against a mid-flight cache change.
- **DoD:** this ticket resolves the `docs/improvements.md` item "matchups.py re-fetch loop
  causes parquet bloat and unnecessary API calls". On handoff, move that entry to the closed
  archive `docs/archive/improvements-closed.md` with a resolution note citing ticket 038.

## Verification
- `.venv/bin/python -m pytest tests/test_matchups.py` green, including the new on-disk
  no-duplicate-rows assertion after N same-day calls.
- Manual (authenticated): load `/overview` several times in one day with a warm cache;
  confirm the leaderboard renders identical data each time and the matchups parquet under
  `CACHE_DIR/{league_key}/matchups.parquet` does not grow (check row count / file size
  before and after).
- Demo mode is unaffected (demo overview reads the snapshot, not `get_matchups`), but
  sanity-check `GET /demo/overview` still renders.

## Dependencies
- Ticket 037 must complete first (sequencing — land the cache hardening, then the matchups
  fix on top of the hardened `cache.write()`).
</content>
