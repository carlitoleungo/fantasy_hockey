## Code Review — bug-week23-all-zeroes

**Files reviewed:**
- `data/matchups.py` — 2-line guard added at lines 44–46; module docstring updated
- `tests/test_matchups.py` — `test_does_not_call_api_when_cache_is_current` replaced with `test_current_week_always_refetched_even_when_cached`
- `docs/improvements.md` — "Remove unused `date` import" improvement closed

---

### Scope: CLEAN

All three touched files are squarely within the bug's stated scope. The `docs/improvements.md` closure is the explicitly-allowed housekeeping class of change. No bonus features, no collateral cleanup.

---

### Architecture: CLEAN

The DECISIONS.md conflict flagged during initial review has been resolved. The Tech Lead wrote a superseding entry dated 2026-05-31 ("matchups.py: current_week always re-fetched to reflect intra-week stats") at the top of `docs/DECISIONS.md`. It records the new behaviour, the +1-API-call trade-off, the trigger (this bug), and a `Revisit if` clause (Yahoo rate-limit warnings). The original 2026-03-03 entry is marked superseded with a correct cross-reference. No outstanding DECISIONS.md conflicts.

---

### Issues

None.

---

### Verification adequacy

The replacement test `test_current_week_always_refetched_even_when_cached` (line 128) accurately encodes the bug scenario and is not trivially passing:

- Seeds the cache with week 5 all-zero stats (simulating the early-week fetch that triggered the bug).
- Monkeypatches `cache.last_updated` to yesterday, which ensures the pre-existing `prev_week` re-fetch path does **not** fire — isolating the new guard's behaviour.
- Asserts week 5 appears in `fetched_weeks` (the guard fires).
- Asserts `Goals == 10.0` (`fake_all_teams_week_stats` returns `week * 2 = 10`), confirming `drop_duplicates(keep="last")` overwrites the stale zeroes with fresh data.

Without the fix, `current_week` would not appear in `weeks_to_fetch`, no API call would be made, and `Goals` would remain `0.0` — the test would fail for the right reason. This is a good regression test.

The pre-season edge case (`current_week=0`, `start_week=1`) is covered by the existing `test_returns_none_when_season_not_started`, which verifies the `current_week >= start_week` bound suppresses the guard. The normal mid-season path (week not yet cached → fetched in the standard delta range, guard does not fire) is implicitly covered by `test_fetches_all_weeks_when_cache_empty` and `test_fetches_only_missing_weeks_when_cache_partial`.

The QA manual trace correctly walks all three code paths. No verification gaps found.

---

### Verdict: APPROVED

Code is correct, test accurately encodes the bug scenario, DECISIONS.md is now in sync. Ticket is done.
