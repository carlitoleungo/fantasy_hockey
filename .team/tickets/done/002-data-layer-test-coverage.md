# 002 — Expand data/analysis layer test coverage

## Summary

The `data/` and `analysis/` layers are the safety net for the entire migration: if these tests pass before migration and still pass after, the preserved Python logic is intact regardless of what framework wraps it. Three gaps exist: the pure helper functions in `auth/oauth.py` (nonce lifecycle, token expiry checks) are untested; the prev-week re-fetch path in `data/matchups.py` has only one direction covered; and `analysis/projection.py`'s `_is_rate_stat` function has no test. This ticket closes all three gaps using only in-memory inputs and `tests/fixtures/` — no live API calls, no Streamlit imports.

## Acceptance criteria

- [ ] `tests/test_oauth_helpers.py` is created and all tests in it pass with `pytest tests/test_oauth_helpers.py`. The file must not import `streamlit` directly (verify with `grep -n "^import streamlit\|^from streamlit" tests/test_oauth_helpers.py` returning no matches). It covers: `_stamp_expiry` adds `expires_at ≈ time.time() + expires_in`; `_is_valid` returns `False` when `expires_at` is in the past; `_is_valid` returns `False` when within the 60-second buffer; `_is_valid` returns `True` when more than 60 seconds remain; `validate_and_consume_state` returns `False` for an unknown nonce; `validate_and_consume_state` returns `True` exactly once for a known unexpired nonce and `False` on the second call (one-time use); `validate_and_consume_state` returns `False` for an expired nonce.
- [ ] `tests/test_matchups.py` gains at least two new test functions covering both directions of the prev-week re-fetch path: one asserts the most recently completed week is re-fetched when `cache.last_updated` returns today's date; one asserts it is not re-fetched when `cache.last_updated` returns yesterday. Both use `monkeypatch` on `cache.last_updated` and `client.get_all_teams_week_stats` — no disk I/O.
- [ ] `tests/test_projection.py` gains at least one new test asserting that `_is_rate_stat` returns `True` for `"GAA"`, `"SV%"`, `"Goals Against Average"`, and `"Save Percentage"`, and `False` for `"Goals"` and `"Assists"`. The function must be importable via `from analysis.projection import _is_rate_stat`.
- [ ] `pytest tests/` passes with zero failures and zero errors (all pre-existing tests continue to pass unchanged).

## Files likely affected

- `tests/test_oauth_helpers.py` (created)
- `tests/test_matchups.py` (new test functions added)
- `tests/test_projection.py` (new test function added)

## Dependencies

None — can be done in parallel with ticket 001.

## Notes for the engineer

**Streamlit import workaround**: `auth/oauth.py` has `import streamlit as st` at the top level and calls `st.secrets` inside several functions. The functions under test don't call `st.secrets`, but the module import will fail without Streamlit installed in the test environment. Patch it before importing:

```python
import sys
from unittest.mock import MagicMock
sys.modules["streamlit"] = MagicMock()
from auth.oauth import _stamp_expiry, _is_valid, validate_and_consume_state, _STATE_TTL
```

Place this at the very top of `tests/test_oauth_helpers.py`, before any other `from auth` imports.

**Nonce file redirect**: `validate_and_consume_state` reads/writes `.streamlit/oauth_states.json` via `_STATE_FILE`. Use `monkeypatch` with `tmp_path` to redirect `auth.oauth._STATE_FILE` to a temp file, exactly as `tests/test_cache.py` redirects `cache.CACHE_DIR`. Call `_save_state(nonce)` in the test setup to seed a valid nonce before calling `validate_and_consume_state`.

**Matchups re-fetch test**: Look at the existing `test_does_not_call_api_when_cache_is_current` test for the pattern. The missing test is the mirror: monkeypatch `cache.last_updated` to return `datetime.combine(date.today(), time.min)`, seed the cache with week 4, set `current_week=5`, and assert that `client.get_all_teams_week_stats` was called with week=4 (the re-fetch) and week=5 (the new week).

**`_is_rate_stat` location**: Verify the function is in `analysis/projection.py` before writing the test — if it's private it can still be imported directly for testing purposes.

## Notes for QA

Run `pytest tests/` before this ticket to capture the baseline pass count. After: (a) count must be strictly higher, (b) zero regressions. Specifically check that `test_oauth_helpers.py` has no Streamlit import: `grep -rn "streamlit" tests/test_oauth_helpers.py` must return nothing beyond the `MagicMock` patch line.

## Tech Lead Review

**Files likely affected — verdict: correct.** No hidden files. `analysis/projection.py` exists and `_is_rate_stat` is defined at line 17 — it can be imported directly for testing.

**Complexity: M** (15–30 min). Three separate test modules with different patching patterns (tmp_path redirect for the nonce file, monkeypatch for matchups, direct import for `_is_rate_stat`). Each is simple in isolation; the overhead is context-switching across three files.

**Hidden dependency / ordering risk:** The `test_oauth_helpers.py` tests for `_is_valid`, `_stamp_expiry`, and `validate_and_consume_state` become the regression baseline for ticket 004's refactor of `auth/oauth.py`. This ticket **must be merged before 004 begins** — engineers should not refactor untested code. The ticket itself has no blocking start dependency, so it can run in parallel with 003 immediately after 001 is done.
