# Improvements Backlog

> **Scope:** Code quality improvements, minor cleanups, and nits that aren't worth fixing immediately but should be addressed when the affected file is next touched.

---

## Open

### Remove unused `date` import in `tests/test_matchups.py`

**Source:** Code review 002
**File:** `tests/test_matchups.py` line 11
**Detail:** `date` was added to the `from datetime import ...` line during ticket 002, but neither of the two new re-fetch tests uses it. The tests use `datetime.now(timezone.utc)` instead of the `date.today()` pattern originally suggested in the ticket spec. Dead import — remove `date` from the import line.

---

### Tie `test_is_valid_returns_false_within_buffer` to `TOKEN_EXPIRY_BUFFER_SECONDS` constant

**Source:** Code review 002
**File:** `tests/test_oauth_helpers.py`
**Detail:** The test uses a hardcoded offset of `time.time() + 30` to land inside the 60-second buffer window. Using `time.time() + TOKEN_EXPIRY_BUFFER_SECONDS - 1` instead would tie the test to the actual constant, so it stays correct if the buffer value ever changes.

---

### Move `_is_rate_stat` import to module level in `tests/test_projection.py`

**Source:** Code review 002
**File:** `tests/test_projection.py`
**Detail:** `_is_rate_stat` is imported inside the `test_is_rate_stat` function rather than at the top of the file with the other imports. Minor style inconsistency — either placement works, but moving it to module level matches every other import in the file.

---

### Tighten row-count assertion in `test_logout_unknown_session_id_redirects`

**Source:** Code review 007
**File:** `tests/test_auth_routes.py`
**Detail:** Test 7 asserts `len(rows) == 0` against the full `user_sessions` table after calling logout with an unknown session ID. The assertion is trivially true — no row was inserted before the call. The test's real intent (no error on unknown ID) is already covered by the status code and location checks. Either remove the row-count assertion or insert a dummy row first so the assertion has something to prove.

---

## Closed

<!-- Move resolved items here with a brief resolution note -->

### Move `_db_dep` to `db/connection.py` and clean up dead import

**Source:** Code review 004b
**Resolved:** Ticket 004d — `db_dep` now lives in `db/connection.py`; `web/routes/auth.py`
and `tests/test_auth_routes.py` import it from there. Dead `import sqlite3` removed.
