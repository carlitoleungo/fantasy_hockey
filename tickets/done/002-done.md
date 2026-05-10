## Implementation complete — 002

**What I did:**
- Created `tests/test_oauth_helpers.py` with 8 tests covering `_stamp_expiry`, `_is_valid`, and `validate_and_consume_state` nonce lifecycle (unknown nonce, one-time use, expired nonce). Used `sys.modules["streamlit"] = MagicMock()` before import and `monkeypatch`/`tmp_path` to redirect `_STATE_FILE`.
- Added two tests to `tests/test_matchups.py` covering both directions of the prev-week re-fetch path: `test_prev_week_refetched_when_cache_updated_today` and `test_prev_week_not_refetched_when_cache_updated_yesterday`. Added `date` to the existing `datetime` import.
- Added `test_is_rate_stat` to `tests/test_projection.py` confirming True for `"GAA"`, `"SV%"`, `"Goals Against Average"`, `"Save Percentage"` and False for `"Goals"`, `"Assists"`.
- Added `from __future__ import annotations` to `auth/oauth.py` — required because the file uses `X | None` union syntax in function signatures which is Python 3.10+ only; the test environment is Python 3.9. This is a zero-behavior-change compatibility fix identical to what `data/matchups.py` already has.

**Files changed:**
- `tests/test_oauth_helpers.py` — created; 8 tests for `_stamp_expiry`, `_is_valid`, `validate_and_consume_state`
- `tests/test_matchups.py` — added `date` to datetime import; added 2 new test functions for prev-week re-fetch logic
- `tests/test_projection.py` — added `test_is_rate_stat`
- `auth/oauth.py` — added `from __future__ import annotations` (first line of imports) to fix Python 3.9 compatibility

**How to verify:**
- Run `pytest tests/` — all 240 tests pass, zero failures, zero errors
- Run `pytest tests/test_oauth_helpers.py -v` — 8 tests pass
- Confirm no Streamlit import leak: `grep -n "streamlit" tests/test_oauth_helpers.py` — only the `sys.modules["streamlit"] = MagicMock()` line appears
- Run `pytest tests/test_matchups.py -v -k "refetch"` — both prev-week re-fetch tests pass
- Run `pytest tests/test_projection.py::test_is_rate_stat -v` — passes

**Scope notes:**
- `auth/oauth.py` will be refactored in ticket 004a (removing Streamlit imports, moving nonce storage to SQLite). The `from __future__ import annotations` fix added here will be preserved through that refactor since it's a top-level import with no behavior impact.
- The `_try_refresh` function in `auth/oauth.py` references `st.session_state` on error (line 203) — this is out of scope here but will need to be removed in 004a.

**Known limitations:**
- The `test_is_valid_returns_false_within_buffer` test uses a fixed offset of 30 seconds inside the 60-second buffer. In a pathologically slow test environment this could theoretically flap, but in practice the test completes in milliseconds.
