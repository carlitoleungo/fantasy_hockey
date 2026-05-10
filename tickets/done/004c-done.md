## Implementation complete — 004c

**What I did:**
- Removed unused `date` import from `tests/test_matchups.py`
- Imported `TOKEN_EXPIRY_BUFFER_SECONDS` from `auth.oauth` into `tests/test_oauth_helpers.py` and replaced the hardcoded `30` offset with `TOKEN_EXPIRY_BUFFER_SECONDS - 1`
- Moved `from analysis.projection import _is_rate_stat` from inside the `test_is_rate_stat` function body to the module-level import block in `tests/test_projection.py`

**Files changed:**
- `tests/test_matchups.py` — removed `date` from `from datetime import ...`; `datetime`, `timedelta`, `timezone` unchanged
- `tests/test_oauth_helpers.py` — added `TOKEN_EXPIRY_BUFFER_SECONDS` to import; replaced magic number `30` with `TOKEN_EXPIRY_BUFFER_SECONDS - 1` in `test_is_valid_returns_false_within_buffer`
- `tests/test_projection.py` — added `from analysis.projection import _is_rate_stat` to top-level imports; removed the same import from inside `test_is_rate_stat`

**How to verify:**
- Run `pytest tests/test_matchups.py tests/test_oauth_helpers.py tests/test_projection.py -v` — all 34 tests should pass
- Confirm no `date` in the `from datetime import` line in `test_matchups.py`
- Confirm no `import` statement inside any test function body in `test_projection.py`

**Scope notes:**
- None — all three changes were exactly as specified in the ticket

**Known limitations:**
- None
