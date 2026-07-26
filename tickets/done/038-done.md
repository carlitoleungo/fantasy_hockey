## Implementation complete — 038

**What I did:**
- Replaced the `cache.append(...)` call in `get_matchups()` with a new private helper
  `_merge_into_cache()` that reads the cached frame, concatenates the freshly fetched rows
  after it, drops duplicates on `(team_key, week)` with `keep="last"`, and `cache.write()`s
  (overwrites) the result. This is the improvements entry's Option 2 (dedup-then-overwrite),
  as prescribed in the ticket's Notes; the per-week staleness alternative was not used.
- Left the week-selection logic completely untouched: `_last_cached_week()`, the
  `weeks_to_fetch` construction, the unconditional `current_week` append, and the
  `last_updated == today` prev_week re-fetch all behave exactly as before. The fix changes
  only how fetched rows are persisted, not which weeks are fetched.
- Kept the read-side `drop_duplicates(subset=["team_key", "week"], keep="last")` as
  defence in depth for a parquet already bloated by the old behaviour, and updated its
  comment to say that is now its only job.
- Added 4 tests to `tests/test_matchups.py` covering same-day repeat calls, the on-disk
  no-duplicate assertion, current_week freshness across calls, and self-heal of a
  pre-bloated parquet.
- Closed the scoped-from improvements bug (see "Improvements items closed" below).

**Files changed:**
- `data/matchups.py` — `_merge_into_cache()` helper replaces `cache.append()`; module
  docstring step 4 and the read-side dedup comment updated to match.
- `tests/test_matchups.py` — new "Parquet stays clean across repeated same-day calls"
  section: `read_parquet_from_disk()` helper plus 4 tests.
- `docs/improvements.md` / `docs/archive/improvements-closed.md` — DoD entry move.

`data/cache.py` was **not** modified. The fix needed no cache-layer change: it uses only
the existing `cache.read` / `cache.write` API.

**Acceptance criteria status (self-check):**
- [x] AC1 — repeated same-day calls do not grow the parquet.
  Evidence: `test_repeated_same_day_calls_do_not_grow_parquet` seeds nothing, runs
  `get_matchups()` 5 times with `current_week=5` and the *real* `cache.last_updated`
  (not stubbed), so calls 2–5 genuinely re-fetch weeks 4 and 5 (4 rows each). The on-disk
  parquet is read directly with `pd.read_parquet` after every call and asserted at 10 rows
  (5 weeks × 2 teams = the distinct `(team_key, week)` pair count) each time.
- [x] AC2 — `current_week` still re-fetched and reflected (DECISIONS 2026-05-31 preserved).
  Evidence: `test_current_week_updates_are_reflected_and_overwrite_cached_rows` flips the
  fake API's Goals value from 1.0 to 7.0 between two calls and asserts the second returned
  frame *and* the on-disk file both show 7.0 for `current_week`. The pre-existing
  `test_current_week_always_refetched_even_when_cached` also still passes unchanged.
- [x] AC3 — returned DataFrame unchanged in shape and content for the normal delta cases.
  Evidence: all 12 pre-existing `tests/test_matchups.py` tests pass unmodified — empty
  cache (2 tests), partial cache, current-week re-fetch, column/dtype shape (4 tests),
  season-not-started, call-count (2), and both prev-week re-fetch date cases. Not one
  assertion in the existing file was edited.
- [x] AC4 — a test asserts the parquet is clean on disk, not merely after the read-side dedup.
  Evidence: `test_no_duplicate_rows_on_disk_after_repeated_calls` calls `get_matchups()`
  3 times, then reads `tmp_path/{league_key}/matchups.parquet` directly with `pd.read_parquet`
  (bypassing `get_matchups`, `cache.read`, and the read-side dedup entirely) and asserts
  `not on_disk.duplicated(subset=["team_key", "week"]).any()`.
- [x] AC5 — `.venv/bin/python -m pytest tests/` is green: **457 passed** (453 before this
  ticket + the 4 new ones), 0 failed.

**Mutation check (proof the new tests bite):** I temporarily restored
`cache.append(league_key, "matchups", pd.DataFrame(rows))` in place of the new helper and
re-ran `tests/test_matchups.py`: all 4 new tests failed and the 12 pre-existing ones still
passed. Then reverted and re-ran the full suite green. So the new tests fail on the old
behaviour and the old tests do not discriminate — which is exactly why AC4 exists.

**How to verify (for QA):**
- `.venv/bin/python -m pytest tests/test_matchups.py -q` → 16 passed.
- `.venv/bin/python -m pytest tests/ -q` → 457 passed.
- To re-run the mutation check: swap line 68 of `data/matchups.py` back to
  `cache.append(league_key, "matchups", pd.DataFrame(rows))` and confirm the 4 new tests
  fail, then restore.
- Demo mode: I booted `.venv/bin/uvicorn web.main:app --port 8747` and curled
  `GET /demo/overview` → **200**, body contains "Leaderboard". Demo reads the snapshot via
  `data/demo.py`, not `get_matchups`, so it is untouched by this change; this was the
  sanity check the ticket's Verification section asks for.
- Reading the file on disk is the load-bearing check. If you want to confirm by hand:
  ```
  .venv/bin/python -c "import pandas as pd; d=pd.read_parquet('.cache/<league_key>/matchups.parquet'); print(len(d), d.duplicated(subset=['team_key','week']).sum())"
  ```
  The second number must be 0 after any number of `/overview` loads.

**Scope notes:**
- The ticket's Verification also asks for a manual authenticated `/overview` walk with a
  warm cache. **I could not do this and did not claim to.** It is the NHL off-season, so per
  `docs/LEARNINGS.md` ("Off-season → no live data") an authenticated week-keyed page can only
  exercise the empty state — there is no real `current_week` data to warm the matchups
  parquet with, so a "load it several times and watch the file not grow" walk has nothing to
  measure. The automated tests cover the same loop deterministically, including the on-disk
  assertion the manual walk was meant to produce, and the mutation check proves they would
  have caught the bug. QA should treat this as the substitute, or re-run the manual walk
  in-season.
- Two open improvements items name `data/matchups.py` and I deliberately did **not** fix
  either, per the ticket's Out of scope: "League settings and stat categories re-fetched from
  Yahoo on every request" (fix lives in `data/client.py`, M2) and "Leaderboard: all-zero rows
  when a week has no player activity" (fix lives in `web/routes/overview.py`, not in Touches).
  I did not touch code adjacent to either.
- Observation, not a defect: `get_matchups()` now performs the same 3 parquet reads + 1 write
  per call as before (`_last_cached_week`, the merge read, the final read; `cache.append` also
  read internally), so there is no added I/O. There is a plausible follow-up to thread the
  frame `_last_cached_week()` already read through to the merge and the return, saving 2 reads
  per call, but that would rework the week-selection code the ticket puts out of scope. Worth
  a separate ticket only if `/overview` latency is ever measured as a problem.
- No new dependency, env var, or config knob was needed. Nothing in the ticket was ambiguous.

**Improvements items closed:**
- "`matchups.py` re-fetch loop causes parquet bloat and unnecessary API calls"
  (`Type: bug`, discovered 2026-03-30) — moved from `docs/improvements.md` § Open to
  `docs/archive/improvements-closed.md` § Closed with a `**Resolved:** Ticket 038` note
  recording the dedup-then-overwrite mechanism, that Option 2 was chosen over the per-week
  staleness check, and that neither DECISIONS entry changed. Per the ticket's "Open items on
  files in Touches" check, there were no `Type: quality` items on `data/matchups.py` or
  `tests/test_matchups.py` for the input-#6 sweep, so the diff is the fix and its tests only.

**Known limitations / things I couldn't fully test:**
- The authenticated live-data path was not exercised against Yahoo (off-season, as above).
  Everything verified here ran against monkeypatched `client` functions and a real parquet
  cache redirected to `tmp_path` — no live API calls, per the testing strategy.
- The tests assert on-disk row counts in a single-threaded test process. Concurrent
  `get_matchups()` calls for the same league are serialised by `cache.write()`'s per-league
  lock (ticket 037), but the read-modify-write in `_merge_into_cache` spans a `cache.read`
  outside that lock, so two interleaved calls could each write a frame built from the same
  pre-merge snapshot. The result is still duplicate-free and still contains every week either
  call fetched only if the second writer's snapshot included the first's write; in the worst
  interleaving the losing writer's freshly fetched week is overwritten and simply re-fetched
  on the next call. No bloat and no corruption either way, which is what this ticket is about.
  I did not test this interleaving, and I did not widen scope into `data/cache.py` to close it
  (the ticket forbids it). Flagging it for the Reviewer as a possible follow-up: the clean fix
  is a `cache.merge_on(...)` primitive holding the league lock across the read and the write,
  which is a cache-layer change and needs its own ticket.
</content>
