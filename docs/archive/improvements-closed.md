# Improvements & Bug Tracker — Closed items (archive)

> **Archived — current FastAPI stack.** These are resolved `quality` and `bug` items
> moved out of [`docs/improvements.md`](../improvements.md) to keep the active tracker
> lean (it is read on every persona spawn). Nothing here is actionable; this file is a
> historical record of what was fixed and in which ticket. New closed items are appended
> here when they are resolved. For the Streamlit-era backlog, see
> [`improvements.md`](improvements.md) in this directory.

---

## Closed

### Nav header shows auth links to unauthenticated visitors

**Type:** quality
**Source:** Audit 024 (noted in ticket 023 done note)
**File:** `web/templates/base.html` line 22–24
**Resolved:** Ticket 036a — added `shell_context()` to `web/routes/common.py` (returns `is_authenticated` / `demo_mode` / `selected_league_name` from the user already resolved by `require_user`/`optional_user`) and made the `base.html` nav conditional on those flags, defaulting to the authenticated nav when both are absent. `web/routes/home.py` adopts the helper on both branches, so the logged-out home nav now renders a single "Log in with Yahoo" link instead of Overview / Waiver / Projection / Logout. Adoption in the overview/waiver/projection demo shells follows in ticket 036b.

### Converge Week Projection matchup route on a single team query-param name

**Type:** quality
**Source:** Code review 030
**File:** `web/routes/projection.py` line 218; `web/templates/projection/index.html`
**Resolved:** Ticket 035 — removed the `my_team` parameter and the `selected = team_key or my_team` fallback from both `projection_matchup` and `demo_projection_matchup` in `web/routes/projection.py`. `team_key` is now the sole param; `?my_team=` is treated as no selection and redirects to the shell. The shell template already emitted `team_key` (unchanged).

### TC10 missing `>GR<` assertion for games-remaining column

**Type:** quality
**Source:** Code review 019b
**File:** `tests/test_waiver.py` — `test_waiver_post_lastmonth_returns_gp_column_and_footer`
**Resolved:** Ticket 032 — added `assert ">GR<" in body` to TC10 (`tests/test_waiver.py` was in this ticket's Touches). Closed while in-scope per Engineer persona input #6.

### No automated tests for `/demo/overview` and `/demo/overview/table` routes

**Type:** quality
**Source:** Code review 020
**File:** `tests/test_demo_overview_routes.py`
**Resolved:** Ticket 027 — added `tests/test_demo_overview_routes.py` (6 tests) covering all three required names (`test_demo_overview_shell_returns_200`, `test_demo_overview_table_returns_fragment`, `test_demo_overview_no_auth_required`) plus HTMX-target and no-Yahoo-call assertions. Closed at audit 032 (the item was left under Open after 027 shipped).

### "Compare two teams" link hard-codes `/overview/head-to-head` in shared template

**Type:** quality
**Source:** Code review 020; updated code review 021
**File:** `web/templates/overview/index.html` line 11
**Resolved:** Ticket 025 — `head_to_head_url` (in `index.html`) and `overview_url` (in `head_to_head.html`) are now passed from both the authenticated and demo shell handlers (both empty-state and normal branches), so the shared templates render the correct route per context. Fixed the sibling "← Back to Leaderboard" hardcoded `/overview` link in the same ticket.

### Update docs/bugs.md parquet-bloat entry to include current_week

**Type:** quality
**Source:** Audit 024
**Resolved:** 2026-07-02 docs consolidation — `docs/bugs.md` was merged into this file and the migrated parquet-bloat bug entry now documents `current_week` as a second participant in the bloat.

### Demo mode not reachable for `/overview` and `/overview/head-to-head`

**Type:** quality
**Source:** Audit 001
**File:** `web/routes/overview.py`, `web/templates/overview/`
**Resolved (partial):** Ticket 020 — `/demo/overview` and `/demo/overview/table` routes added to `web/routes/overview.py`; `overview/index.html` updated to use `{{ table_url }}` context variable so both authenticated and demo shells point at the correct fragment endpoint. The `/demo/overview/head-to-head` gap remains open and is tracked in ticket 021.

### Tighten TC9 assertion to isolate league name to the header element

**Type:** quality
**Source:** Code review 014
**Resolved:** Ticket 023 — `test_home_header_shows_selected_league_name` now extracts the `<header>…</header>` substring and asserts the league name is present within it.

### Logout provides no confirmation and re-auth is invisible

**Type:** quality
**Source:** QA 015 manual verification
**Resolved:** Ticket 022 — `/auth/logout` now redirects to `/?logged_out=1` instead of `/auth/login`; cookie is deleted on logout; `home.html` shows a "You have been logged out." banner when `?logged_out=1` is present.

### Dead `cats` variable in demo branch of `_waiver_post_impl`

**Type:** quality
**Source:** Code review 019a
**File:** `web/routes/waiver.py`
**Resolved:** Ticket 019b — removed dead `cats = demo_module.get_stat_categories()` call from the `demo=True` branch of `_waiver_post_impl`.

### Remove unused `date` import in `tests/test_matchups.py`

**Type:** quality
**Source:** Code review 002
**Resolved:** Bug fix week23-all-zeroes — confirmed `date` was already absent from the import line when this ticket was worked; improvement was already applied.

### `stat_columns(df)` called twice in `overview()`

**Type:** quality
**Source:** Code review 015
**Resolved:** Ticket 016 — extracted to local variable `cols` in both `overview()` and `overview_table()`.

### Move `_db_dep` to `db/connection.py` and clean up dead import

**Type:** quality
**Source:** Code review 004b
**Resolved:** Ticket 004d — `db_dep` now lives in `db/connection.py`; `web/routes/auth.py`
and `tests/test_auth_routes.py` import it from there. Dead `import sqlite3` removed.

### Tie `test_is_valid_returns_false_within_buffer` to `TOKEN_EXPIRY_BUFFER_SECONDS` constant

**Type:** quality
**Source:** Code review 002
**Resolved:** Ticket 010 — confirmed the test already used `TOKEN_EXPIRY_BUFFER_SECONDS - 1`; the improvement had already been applied. No code change needed.

### Stale comment and dead stub in `tests/test_home_routes.py`

**Type:** quality
**Source:** Code review 011
**Resolved:** Ticket 014 — removed stale module docstring referencing xmltodict, removed `if "xmltodict" not in sys.modules` guard, removed unused `sys` import.

---

### Near-duplicate demo projection matchup tests after ticket 035's alias removal

**Type:** quality
**Source:** QA 035
**File:** `tests/test_demo_projection_routes.py`
**Resolved:** Ticket 034 — removed `test_demo_projection_matchup_accepts_team_key_param`, which asserted nothing `test_demo_projection_matchup_returns_fragment` did not already assert once the `my_team` alias was gone. The surviving test keeps the richer fragment assertions.
