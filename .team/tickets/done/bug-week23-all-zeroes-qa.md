## QA Report — bug-week23-all-zeroes

**Ticket:** Week 23 Shows All Zeroes for All Teams
**Engineer handoff:** `.team/tickets/bug-week23-all-zeroes-fix.md`
**QA date:** 2026-04-26

---

### Test results

| # | Acceptance criterion | Result | Notes |
|---|---------------------|--------|-------|
| 1 | `current_week` is always included in `weeks_to_fetch` even when already cached | PASS | Guard present at `matchups.py:44–46`: `if current_week >= start_week and current_week not in weeks_to_fetch: weeks_to_fetch.append(current_week)` |
| 2 | Fresh data replaces stale zeroes (not just appended) | PASS | `test_current_week_always_refetched_even_when_cached`: seeds week 5 Goals=0.0, asserts result Goals=10.0 after re-fetch; `drop_duplicates(keep="last")` at line 74–76 ensures fresh row wins |
| 3 | Guard does not fire when season hasn't started (`current_week=0`) | PASS | `current_week >= start_week` is False when current_week=0, start_week=1; `test_returns_none_when_season_not_started` passes; no API calls made, returns None |
| 4 | Old `test_does_not_call_api_when_cache_is_current` test is removed | PASS | `grep` confirms the name is absent from `tests/test_matchups.py` |
| 5 | New regression test `test_current_week_always_refetched_even_when_cached` exists and passes | PASS | Present at `tests/test_matchups.py:128`; passes under system Python 3.9.6 |
| 6 | Module docstring no longer says current week is fetched only once | PASS | `matchups.py:15–17`: "On subsequent runs it fetches only missing weeks plus always re-fetches current_week, because intra-week stats update as games are played." — accurate |

---

### Automated tests

- **Command run:** `python3 -m pytest tests/test_matchups.py -v` (system Python 3.9.6, the project's working environment)
- **Tests run:** 12 tests in `test_matchups.py`
- **New tests written by engineer:** `test_current_week_always_refetched_even_when_cached` — replaces the now-invalid `test_does_not_call_api_when_cache_is_current`
- **All passing:** YES — 12/12

**Broader suite (all collectible tests):**
- Command: `python3 -m pytest tests/ --ignore=tests/test_auth_routes.py --ignore=tests/test_error_handling.py --ignore=tests/test_head_to_head_routes.py --ignore=tests/test_home_routes.py --ignore=tests/test_overview_routes.py --ignore=tests/test_overview_routes_qa.py --ignore=tests/test_session_middleware.py -v`
- Result: **239 passed, 0 failed**
- The 7 ignored files fail to import due to `fastapi` not installed in the system Python 3.9 environment — this is a pre-existing environment issue, not introduced by this ticket (confirmed: all 7 files require `from fastapi.testclient import TestClient` and none of them touch matchups logic).

**Note on python3.11:** Running with `python3.11` (which has fastapi) causes most matchups and cache tests to fail due to missing `pyarrow`/`fastparquet` in that environment. The working test environment for this project is unambiguously the system Python 3.9.6. This is a pre-existing env issue not related to this ticket.

---

### Manual verification

Independently traced the fix logic line by line:

1. **Stale-cache scenario** (`current_week` already in cache with zeroes, `last_week == current_week`):
   - `fetch_from = last_week + 1 = current_week + 1`
   - `weeks_to_fetch = range(current_week + 1, current_week + 1) = []` — empty
   - Guard fires: `current_week >= start_week` ✓, `current_week not in []` ✓ → appends `current_week`
   - API called for `current_week`; fresh rows appended to cache
   - `drop_duplicates(subset=["team_key", "week"], keep="last")` at line 74 ensures fresh row overwrites stale zero

2. **Pre-season scenario** (`current_week=0`, `start_week=1`):
   - `fetch_from = start_week = 1` (cache is empty)
   - `weeks_to_fetch = range(1, 1) = []` — empty
   - Guard condition: `0 >= 1` is **False** → guard does not fire
   - `weeks_to_fetch` remains empty → no API call → `cache.read` returns None ✓

3. **Normal mid-season scenario** (weeks 1–4 cached, `current_week=5`):
   - `fetch_from = 5`, `weeks_to_fetch = [5]`
   - Guard: `5 not in [5]` is False → guard does not fire (not needed)
   - Week 5 fetched once as part of normal delta — correct

4. **Docstring:** "always re-fetches current_week, because intra-week stats update as games are played" — matches the implementation.

---

### Issues found

None.

---

### Verdict: APPROVED

All 6 acceptance criteria pass. The regression test directly encodes the bug scenario (stale zeroes in cache → re-fetch → fresh data replaces zeroes). Guard is correct for the pre-season edge case. Full test suite (239 tests) is green. Docstring is accurate.
