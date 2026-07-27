# Improvements & Bug Tracker — Closed items (archive)

> **Archived — current FastAPI stack.** These are resolved `quality` and `bug` items
> moved out of [`docs/improvements.md`](../improvements.md) to keep the active tracker
> lean (it is read on every persona spawn). Nothing here is actionable; this file is a
> historical record of what was fixed and in which ticket. New closed items are appended
> here when they are resolved. For the Streamlit-era backlog, see
> [`improvements.md`](improvements.md) in this directory.

---

## Closed

### `matchups.py` re-fetch loop causes parquet bloat and unnecessary API calls

**Type:** bug
**Symptom:** On every page load for the rest of a given day, `prev_week` stats were re-fetched from Yahoo and appended to the parquet file, and `current_week` was appended on every `get_matchups()` call (DECISIONS.md 2026-05-31). The data stayed correct in memory (duplicate rows dropped on read) but the parquet grew by up to two rows-per-team per session.
**Affected files:** `data/matchups.py`, `data/cache.py`
**Discovered:** 2026-03-30
**Resolved:** Ticket 038 — `data/matchups.py` now merges the fetched rows into the cached frame (existing rows first, fetched rows appended), drops duplicates on `(team_key, week)` with `keep="last"`, and `cache.write()`s the result instead of `cache.append()`ing the raw rows. The parquet is bounded to the distinct `(team_key, week)` pairs no matter how often the re-fetch runs, and a parquet already bloated by the old behaviour self-heals on the next write. Took the improvements entry's Option 2 (dedup-then-overwrite), not the per-week staleness check: it also absorbs the intended `current_week` re-fetch, so neither the always-re-fetch behaviour (DECISIONS 2026-05-31) nor the `max(week)` delta-fetch rule (DECISIONS 2026-03-03) changed. `data/cache.py` was not modified.

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

---

### `test_authenticated_nav_links_return_200` is parametrised over an unused argument and adds no coverage

**Type:** quality
**Source:** Code review 036b (first raised by QA 036b)
**File:** `tests/test_nav_shell_qa.py` lines 341-347 (now `tests/test_nav_shell.py`)
**Resolved:** Ticket 040 — deleted outright, the entry's first option. `test_authenticated_feature_pages_render_authenticated_nav` directly above it parametrises the same three paths through the same `_authenticated_feature_get()` helper and already asserts `status_code == 200` alongside the nav link set and the header label, so the "every nav href resolves" intent is stated there and nothing was lost. Not replaced with a de-parametrised variant. The same ticket renamed the module off its `_qa` suffix per DECISIONS.md 2026-07-26.

---

### Nav/header assertions cover 7 of the 12 `shell_context()` branches in the feature routes

**Type:** quality
**Source:** Code review 036b (coverage gap noted by QA 036b, extended here)
**File:** `tests/test_nav_shell_qa.py` (DEMO_PAGES / authenticated params), `tests/test_head_to_head_routes.py`
**Resolved:** Ticket 040 — all 12 migrated branches are now covered. Three new tests in `tests/test_nav_shell.py` close the five gaps in `web/routes/overview.py`: populated authenticated `/overview/head-to-head`, the `df is None or df.empty` and `len(teams) < 2` empty states on the authenticated pair, and the same two empty states on the demo pair. Each asserts the exact nav link set via `_nav_links` and the header label via `_header_left`, and each was confirmed by mutation probe to fail when its branch's `**shell_context(...)` spread is deleted. The demo cases patch `data.demo.get_matchups` (lazy in-body import), not the route module — the trap now recorded in `docs/LEARNINGS.md`. Per the ticket's Out of scope, the assertions stayed consolidated in `tests/test_nav_shell.py`; `tests/test_head_to_head_routes.py` was not modified.

---

### `.dockerignore` secret patterns are root-anchored while its bytecode patterns are not

**Type:** quality
**Source:** Review 039
**File:** `.dockerignore:6-7,32`
**Resolved:** Ticket 045 — replaced `.env` + `.env.*` with a single `**/.env*` and `*.pem` with `**/*.pem`, so all three secret patterns now match at any depth like the `**/`-prefixed bytecode patterns 039 fixed. A comment in the Secrets block records that the prefix is load-bearing and that a miss here bakes a live credential into the image rather than merely bloating it. Verified empirically over a build context taken from the real repo root (`FROM busybox` + `COPY . /ctx`, Docker 29.6.2) with a negative control: probes at `web/.env`, `web/deep/nest/.env.local` and `web/certs/key.pem` reached the context under the old patterns and were absent under the new ones, while root-level `./.env` and `./.env.example` stayed excluded and the context source tree still equalled the host tree minus bytecode (74 files, the same 19 top-level entries QA 039 recorded). The sibling `.streamlit/` patterns were left root-anchored deliberately — the entry did not ask for them and the Streamlit teardown deletes those files outright.
