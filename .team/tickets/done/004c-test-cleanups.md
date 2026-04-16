# 004c — Test file cleanups

## Summary

Three small accuracy and style issues discovered during code review of the
test suite. Fix them now so the test bed is clean before ticket 005 adds
session-middleware tests that depend on the same constants and import
conventions.

## Acceptance criteria

- [ ] `tests/test_matchups.py` line 11: `date` is removed from the
  `from datetime import ...` statement; the remaining imports
  (`datetime`, `timedelta`, `timezone`) are unchanged and all tests pass.
- [ ] `tests/test_oauth_helpers.py` `test_is_valid_returns_false_within_buffer`:
  the hardcoded `30` offset is replaced with
  `TOKEN_EXPIRY_BUFFER_SECONDS - 1` (imported from `auth.oauth`); the
  test still passes and would fail automatically if `TOKEN_EXPIRY_BUFFER_SECONDS`
  were ever raised above the new offset value.
- [ ] `tests/test_projection.py`: `from analysis.projection import _is_rate_stat`
  is moved to the top-level import block (alongside `from analysis import
  projection`); the `test_is_rate_stat` function body no longer contains any
  import statement; all projection tests pass.

## Files likely affected

- `tests/test_matchups.py`
- `tests/test_oauth_helpers.py`
- `tests/test_projection.py`

## Dependencies

Requires 004a and 004b to be completed first (establishes the `auth/oauth.py`
constants this ticket's test now imports directly).

## Notes for the engineer

**Change 1 — dead import.**
Line 11 of `test_matchups.py` reads:
```python
from datetime import date, datetime, timedelta, timezone
```
Remove `date`; nothing in the file uses it.

**Change 2 — constant-tied boundary.**
`test_is_valid_returns_false_within_buffer` in `test_oauth_helpers.py` currently
uses the magic number `30`. Replace with `TOKEN_EXPIRY_BUFFER_SECONDS - 1` so the
test tracks the real constant:
```python
from auth.oauth import TOKEN_EXPIRY_BUFFER_SECONDS, _is_valid, _stamp_expiry

def test_is_valid_returns_false_within_buffer():
    tokens = {"expires_at": time.time() + TOKEN_EXPIRY_BUFFER_SECONDS - 1}
    assert _is_valid(tokens) is False
```
`TOKEN_EXPIRY_BUFFER_SECONDS` is currently `60`, so `59` is the new offset —
functionally identical to the old `30`, but the test now fails if the constant
changes.

**Change 3 — module-level import.**
In `test_projection.py`, this import currently lives inside the test function body:
```python
def test_is_rate_stat():
    from analysis.projection import _is_rate_stat
    ...
```
Move it to the top of the file alongside `from analysis import projection`.
No logic changes — purely a style consistency fix.

## Notes for QA

Run `pytest tests/test_matchups.py tests/test_oauth_helpers.py tests/test_projection.py -v`
and confirm all tests pass. Verify there are no remaining `from datetime import`
references to `date` in `test_matchups.py` and no inline imports inside test
function bodies in `test_projection.py`.
