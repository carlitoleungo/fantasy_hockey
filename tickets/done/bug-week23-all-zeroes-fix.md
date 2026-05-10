## Implementation complete — bug-week23-all-zeroes

**What I did:**
- Added a guard in `get_matchups` so `current_week` is always included in `weeks_to_fetch`, even when already cached. The existing `drop_duplicates(keep="last")` dedup in the same function ensures the fresh data overwrites stale zeroes.
- Added `current_week >= start_week` bound so the guard does not fire when the season hasn't started (`current_week=0`).
- Updated the module docstring to remove the inaccurate claim that the current week is fetched only once.
- Replaced `test_does_not_call_api_when_cache_is_current` with `test_current_week_always_refetched_even_when_cached` — the old test asserted the behaviour that caused the bug.
- Closed the stale "Remove unused `date` import" improvements item — the import was already absent from the file.

**Files changed:**
- [`data/matchups.py`](../data/matchups.py) — added 2-line guard (lines 47–48) to always include `current_week` in `weeks_to_fetch`; updated module docstring
- [`tests/test_matchups.py`](../tests/test_matchups.py) — replaced the now-wrong "no API calls" test with a regression test that asserts the current week is re-fetched and that fresh data replaces stale zeroes
- [`docs/improvements.md`](../docs/improvements.md) — closed stale `date` import item (already resolved)

**How to verify:**
1. Run `python3 -m pytest tests/test_matchups.py -v` — all 12 tests should pass, including the new `test_current_week_always_refetched_even_when_cached`.
2. Manually: seed the cache with all-zero stats for the current week (simulate early-week fetch), then call `get_matchups` again — the returned DataFrame should contain the live stats, not the cached zeroes.

**Scope notes:**
- The improvements backlog item "Leaderboard: all-zero rows when a week has no player activity" (`docs/improvements.md`) still applies to a separate scenario: a user opens the app before any games have been played that day, so live data is legitimately all zero. The fix here ensures stale cache is always overwritten, but cannot conjure stats that don't exist yet. The suggestion of defaulting to the most recent week with non-zero data or showing a notice is a separate UX ticket touching `web/routes/overview.py`.

**Known limitations:**
- `current_week` is now re-fetched on every app visit. This costs 1 extra API call per session. Given the caching strategy note in CLAUDE.md ("Minimise API calls"), this trade-off is intentional and documented in the ticket — correctness wins over call count for intra-week data.
