# Improvements Backlog

> **Scope:** Code quality improvements, minor cleanups, and nits that aren't worth fixing immediately but should be addressed when the affected file is next touched.

---

## Open

### Add demo mode entry point on home page

**Source:** Owner note post-020
**File:** `web/templates/home.html`, `web/routes/home.py` (or wherever the home route lives)
**Detail:** Unauthenticated visitors have no visible way to reach demo mode — `/demo/overview` and `/demo/waiver` exist but are not linked from the home page. Add a "Try the demo" button or link on the home page (logged-out view) so visitors can explore the app without signing in. The home route already distinguishes authenticated vs. unauthenticated state (via `optional_user`), so the demo CTA only needs to appear in the unauthenticated branch.

---

### No automated tests for `/demo/overview` and `/demo/overview/table` routes

**Source:** Code review 020
**File:** `tests/test_overview_routes.py` (or a new `tests/test_demo_overview_routes.py`)
**Detail:** The demo overview routes have no automated test coverage. QA and the Engineer both noted this gap. The waiver demo routes have `test_demo_waiver_shell_returns_200` as a parallel in `test_waiver_routes.py`. Add at minimum: `test_demo_overview_shell_returns_200` (GET /demo/overview → 200, no auth cookie required), `test_demo_overview_table_returns_fragment` (GET /demo/overview/table?week=N → 200, response begins with `<div`, no `<html>` tag), and `test_demo_overview_no_auth_required` (no session cookie → still 200, not 302). These match the coverage pattern already established for the waiver demo routes.

---

### "Compare two teams" link hard-codes `/overview/head-to-head` in shared template

**Source:** Code review 020; updated code review 021
**File:** `web/templates/overview/index.html` line 11
**Detail:** The "Compare two teams →" anchor points to `/overview/head-to-head` unconditionally. When the template is rendered in the demo context (`/demo/overview`), that link sends the unauthenticated visitor to the authenticated route, which redirects to login. The fix is to pass a `head_to_head_url` context variable (analogous to `table_url`) from both the authenticated and demo shells, defaulting to `/overview/head-to-head` and `/demo/overview/head-to-head` respectively, and update the template to use `{{ head_to_head_url }}`. Ticket 021 added the `/demo/overview/head-to-head` route (the prerequisite) but `index.html` was outside its `Touches` list. This fix is now unblocked — it should land in the next ticket that touches `web/templates/overview/index.html` or `web/routes/overview.py`.

---

### Simplify redundant assertion in TC14 of `test_home_routes.py`

**Source:** Code review 023
**File:** `tests/test_home_routes.py` line 367
**Detail:** `test_home_unauthenticated_shows_login_cta` (TC14) contains `assert "<h1" in body and "Your Leagues" not in body.split("</head>", 1)[1]`. The `"<h1" in body` guard is always true (the unauthenticated `home.html` branch contains an `<h1>`), so it adds no signal. The `body.split("</head>", 1)[1]` idiom is unusual and harder to read than a plain `not in body`. Simplify to `assert "Your Leagues" not in body` — the adjacent `assert "Fantasy Hockey Waiver Wire" in body` already confirms the correct heading is present.

---

### Stale Streamlit fallback in `auth/oauth.py` credential helpers

**Source:** Audit 001 (surfaced during credential rotation)
**File:** `auth/oauth.py` lines 151, 158, and the `_redirect_uri` equivalent
**Detail:** `_client_id()`, `_client_secret()`, and `_redirect_uri()` check the env var first, then fall back to `st.secrets["yahoo"][...]`. The Streamlit fallback is dead code — the app runs on FastAPI and `streamlit` is not in `requirements-web.txt`. If the env var is missing, the fallback silently attempts to `import streamlit` and fails at runtime with a confusing `ModuleNotFoundError` rather than a clear "YAHOO_CLIENT_ID not set" error. Remove the `st.secrets` fallback and replace with `raise RuntimeError("YAHOO_CLIENT_ID environment variable not set")` so misconfigured environments fail fast with a useful message.

---


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

---

### TC4 (`test_demo_waiver_shell_returns_200`) only asserts form action — misses stat chips

**Source:** Code review 018
**File:** `tests/test_waiver_routes.py` TC4 (~line 158)
**Detail:** TC4 checks status 200 and that `/demo/api/waiver/players` appears in the response body. It does not verify position radio inputs or stat checkbox values. The original bug (metadata columns as stat chips) was caught by manual QA, not by this test. Extend TC4 to assert all 6 position values and the expected stat names from the fixture DataFrame — matching the pattern TC1 already uses for `GET /waiver`.

---

### TC10 missing `>GR<` assertion for games-remaining column

**Source:** Code review 019b
**File:** `tests/test_waiver.py` — `test_waiver_post_lastmonth_returns_gp_column_and_footer`
**Detail:** TC10 asserts `>GP<` is present in the response body but does not assert `>GR<`. AC1 for ticket 019b requires both the GP and GR column headers to appear when `period="Last 30 days"`. QA manually confirmed `>GR<` renders correctly, but the test gap means a regression that removes the GR header would not be caught by the automated suite. Add `assert ">GR<" in body` to TC10.

---

## Closed

<!-- Move resolved items here with a brief resolution note -->

### Demo mode not reachable for `/overview` and `/overview/head-to-head`

**Source:** Audit 001
**File:** `web/routes/overview.py`, `web/templates/overview/`
**Resolved (partial):** Ticket 020 — `/demo/overview` and `/demo/overview/table` routes added to `web/routes/overview.py`; `overview/index.html` updated to use `{{ table_url }}` context variable so both authenticated and demo shells point at the correct fragment endpoint. The `/demo/overview/head-to-head` gap remains open and is tracked in ticket 021.

### Tighten TC9 assertion to isolate league name to the header element

**Source:** Code review 014
**Resolved:** Ticket 023 — `test_home_header_shows_selected_league_name` now extracts the `<header>…</header>` substring and asserts the league name is present within it.

### Logout provides no confirmation and re-auth is invisible

**Source:** QA 015 manual verification
**Resolved:** Ticket 022 — `/auth/logout` now redirects to `/?logged_out=1` instead of `/auth/login`; cookie is deleted on logout; `home.html` shows a "You have been logged out." banner when `?logged_out=1` is present.

### Dead `cats` variable in demo branch of `_waiver_post_impl`

**Source:** Code review 019a
**File:** `web/routes/waiver.py`
**Resolved:** Ticket 019b — removed dead `cats = demo_module.get_stat_categories()` call from the `demo=True` branch of `_waiver_post_impl`.

### Remove unused `date` import in `tests/test_matchups.py`

**Source:** Code review 002
**Resolved:** Bug fix week23-all-zeroes — confirmed `date` was already absent from the import line when this ticket was worked; improvement was already applied.

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
