# Improvements Backlog

> **Scope:** Code quality improvements, minor cleanups, and nits that aren't worth fixing immediately but should be addressed when the affected file is next touched.

---

## Open

### Logout provides no confirmation and re-auth is invisible

**Source:** QA 015 manual verification
**File:** `web/routes/auth.py` (logout handler), `web/templates/base.html`
**Detail:** Two related UX gaps surfaced when navigating via the new Overview nav link: (1) After logout the user lands on `/` with no league selected, which looks identical to the home screen for a freshly logged-in user — there is no "you have been logged out" message. (2) The session DB record is deleted on logout but the session cookie remains in the browser. Clicking "Overview" after logout triggers a full silent Yahoo OAuth re-authentication round-trip (Overview → /auth/login → Yahoo → /auth/callback → /) that looks to the user like "nothing happened". Fix options: clear the cookie on logout in addition to deleting the DB row; show a flash/banner on the post-logout redirect; or add a dedicated `/logged-out` landing page.

---

### Leaderboard: all-zero rows when a week has no player activity

**Source:** QA 015 manual verification
**File:** `web/routes/overview.py`, `data/matchups.py`
**Detail:** The leaderboard defaults to the latest available week. During the championship period (or any week where most players haven't played yet), the API returns `'-'` for unplayed stats, which `data/matchups` coerces to `0`. The table renders correctly but shows all zeros, giving no useful ranking signal. Consider detecting an all-zero week and either defaulting to the most recent week with non-zero data, showing a "data not yet available" notice inline, or excluding the current in-progress week from the default selection (consistent with the `exclude_weeks` parameter already present on `avg_ranks()`).

---

### Leaderboard: tied "worst" cells may not get bg-red-100

**Source:** Ticket 015 engineer note
**File:** `web/templates/overview/_table.html`, `web/routes/overview.py`
**Detail:** `_compute_cell_ranks` uses `method='min'` for ties. When two teams are tied for second-worst in an N-team league, both receive rank N-1 and no team receives rank N, so neither cell is colored `bg-red-100`. Acceptable for v1. Fix: use `method='max'` for the worst-rank check, or compute a separate "is_worst" flag that detects the actual minimum value per column.

---

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

---

### Tighten TC9 assertion to isolate league name to the header element

**Source:** Code review 014
**File:** `tests/test_home_routes.py` line 265
**Detail:** `test_home_header_shows_selected_league_name` asserts `"Alpha League" in response.text`, but "Alpha League" also appears in the league list body for the same fixture. The assertion would pass even if `selected_league_name` were missing from the context. Extract the `<header>...</header>` substring from the response body and assert the league name is present within that substring.

---

## Closed

<!-- Move resolved items here with a brief resolution note -->

### `stat_columns(df)` called twice in `overview()`

**Source:** Code review 015
**Resolved:** Ticket 016 — extracted to local variable `cols` in both `overview()` and `overview_table()`.


### Move `_db_dep` to `db/connection.py` and clean up dead import

**Source:** Code review 004b
**Resolved:** Ticket 004d — `db_dep` now lives in `db/connection.py`; `web/routes/auth.py`
and `tests/test_auth_routes.py` import it from there. Dead `import sqlite3` removed.

### Tie `test_is_valid_returns_false_within_buffer` to `TOKEN_EXPIRY_BUFFER_SECONDS` constant

**Source:** Code review 002
**Resolved:** Ticket 010 — confirmed the test already used `TOKEN_EXPIRY_BUFFER_SECONDS - 1`; the improvement had already been applied. No code change needed.

### Stale comment and dead stub in `tests/test_home_routes.py`

**Source:** Code review 011
**Resolved:** Ticket 014 — removed stale module docstring referencing xmltodict, removed `if "xmltodict" not in sys.modules` guard, removed unused `sys` import.
