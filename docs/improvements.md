# Improvements Backlog

> **Scope:** Code quality improvements, minor cleanups, and nits that aren't worth fixing immediately but should be addressed when the affected file is next touched.

---

## Open

### Remove unused `date` import in `tests/test_matchups.py`

**Source:** Code review 002
**File:** `tests/test_matchups.py` line 11
**Detail:** `date` was added to the `from datetime import ...` line during ticket 002, but neither of the two new re-fetch tests uses it. The tests use `datetime.now(timezone.utc)` instead of the `date.today()` pattern originally suggested in the ticket spec. Dead import — remove `date` from the import line.

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

### Scope `client` fixture in `test_error_handling.py` to module level

**Source:** Code review 009
**File:** `tests/test_error_handling.py` line 8
**Detail:** The `client` fixture is function-scoped (default), so the two test routes (`/test/http-error`, `/test/unhandled`) are registered on the production `app` object once per test — 7 times total. FastAPI silently accumulates duplicate route entries. Add `scope="module"` to the fixture decorator so routes are registered once per test session.

---

### Stale comment and dead stub in `tests/test_home_routes.py`

**Source:** Code review 011
**File:** `tests/test_home_routes.py` lines 8–10 and 28–29
**Detail:** The module docstring says `xmltodict` is "not in requirements-web.txt" — that was true before the QA fix but is now incorrect. The `if "xmltodict" not in sys.modules: sys.modules["xmltodict"] = MagicMock()` guard below it is now dead code in normal installs (xmltodict is present). Remove the stale comment and the defensive stub.

---

## Closed

<!-- Move resolved items here with a brief resolution note -->

### Move `_db_dep` to `db/connection.py` and clean up dead import

**Source:** Code review 004b
**Resolved:** Ticket 004d — `db_dep` now lives in `db/connection.py`; `web/routes/auth.py`
and `tests/test_auth_routes.py` import it from there. Dead `import sqlite3` removed.

### Tie `test_is_valid_returns_false_within_buffer` to `TOKEN_EXPIRY_BUFFER_SECONDS` constant

**Source:** Code review 002
**Resolved:** Ticket 010 — confirmed the test already used `TOKEN_EXPIRY_BUFFER_SECONDS - 1`; the improvement had already been applied. No code change needed.
