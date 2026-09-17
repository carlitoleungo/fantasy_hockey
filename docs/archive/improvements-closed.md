# Improvements & Bug Tracker — Closed items (archive)

> **Archived — current FastAPI stack.** These are resolved `quality` and `bug` items
> moved out of [`docs/improvements.md`](../improvements.md) to keep the active tracker
> lean (it is read on every persona spawn). Nothing here is actionable; this file is a
> historical record of what was fixed and in which ticket. New closed items are appended
> here when they are resolved. For the Streamlit-era backlog, see
> [`improvements.md`](improvements.md) in this directory.

---

## Closed

### Scope `client` fixture in `test_error_handling.py` to module level

**Type:** quality
**Source:** Code review 009
**File:** `tests/test_error_handling.py` line 8
**Resolved:** Ticket 050 — added `scope="module"` to the `client` fixture decorator, so the
two test routes (`/test/http-error`, `/test/unhandled`) are registered on the production `app`
object once per test module instead of once per test (7 times).

### Error pages show the authenticated nav to logged-out visitors

**Type:** quality
**Source:** Code review 036a (raised by QA 036a)
**File:** `web/templates/error.html` line 1; render sites `web/main.py` lines 48-65
**Resolved:** Ticket 042 — implemented DECISIONS.md 2026-07-25 "Nav shell: render sites that cannot resolve a user declare the state unknown and render nav-free; exception handlers never derive auth" (Option C) verbatim. `web/routes/common.py` gained `unknown_auth_shell_context()`, a no-argument sibling to `shell_context()` returning `{"auth_state_unknown": True}`; both exception handlers in `web/main.py` (`requests.HTTPError` -> 502 and the 500 handler) spread it into their `error.html` context; `base.html` branches on that key **first**, before `demo_mode`, and renders the header with the "Fantasy Hockey" brand link only, no feature links, no Logout, no login prompt; `error.html`'s body gained an explicit "Back to home" link to `/`, which is public and renders the correct nav for whoever follows it. No auth is derived in the handlers (no cookie read, no DB lookup, no `request.state`), so both pages render byte-identically with and without a valid `session_id` cookie — asserted in `tests/test_nav_shell.py` and confirmed live against a seeded valid session. The `base.html` "flags absent => authenticated nav" default and the stale `base.html` comment at lines 21-22 were deliberately left alone; both belong to the 044 default-flip follow-up tracked under `## Open`.

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

---

### Add demo mode entry point on home page

**Type:** quality
**Source:** Owner note post-020
**File:** `web/templates/home.html`, `web/routes/home.py` (or wherever the home route lives)
**Resolved:** Ticket 043 — added a secondary "Try the demo" link (`href="/demo/overview"`) next to the "Log in with Yahoo" button in `home.html`'s unauthenticated branch only. No route change was needed; `web/routes/home.py` was out of scope for this ticket. Covered by new tests `test_home_unauthenticated_shows_demo_cta` and `test_home_authenticated_no_demo_cta` in `tests/test_home_routes.py`.

---

### Simplify redundant assertion in TC14 of `test_home_routes.py`

**Type:** quality
**Source:** Code review 023
**File:** `tests/test_home_routes.py` line 367
**Resolved:** Ticket 043 — dropped the always-true `"<h1" in body` clause. Could not adopt the exact suggested replacement (`assert "Your Leagues" not in body`) verbatim: `home.html`'s `{% block title %}` is the fixed string "Your Leagues" regardless of branch, so that plain check always fails against the `<title>` tag. Scoped the check to content after `<body>` instead (`body.split("<body>", 1)[1]`), which keeps the simplification's intent (no more `</head>`-split idiom hidden behind a redundant guard) while staying correct. Verified green under `.venv/bin/python -m pytest tests/`.

---

### TC18's league-label assertion in `test_home_routes.py` does not discriminate

**Type:** quality
**Source:** Code review 036a (proved by QA 036a mutation probe)
**File:** `tests/test_home_routes.py` lines 450-451
**Resolved:** Ticket 043 — deleted the trailing `assert "Alpha League" in body` and its comment from `test_home_authenticated_nav_has_feature_links_in_roadmap_order` (TC18). TC9 (`test_home_header_shows_selected_league_name`) and `tests/test_nav_shell.py::test_authenticated_home_nav_and_league_label` remain as the tests that actually scope the assertion to `<header>…</header>`.

---

### Post-036b stale comments about pages "not yet" passing `shell_context()`

**Type:** quality
**Source:** Code review 036b (flagged by both the Engineer and QA)
**File:** `tests/test_overview_routes.py` (`test_overview_renders_authenticated_nav_by_default`), `web/templates/base.html` lines 21-22
**Resolved:** Ticket 044 — both halves retired. `base.html`'s "pages that do not yet pass `shell_context()`" comment was deleted along with the default it described (the default now renders nav-free). In `tests/test_overview_routes.py`, TC9's comment was rewritten to say `/overview` passes `shell_context()` since 036b so the test proves the explicit `is_authenticated=True` branch, and the test was renamed `test_overview_renders_authenticated_nav` (dropping the misleading `_by_default`). Its assertions were left unchanged.

---

### `base.html`'s authenticated-nav default is now unblocked, and 040 measured what it costs

**Type:** quality
**Source:** Code review 040 (evidence from QA 040's ablation probes)
**File:** `web/templates/base.html` lines 21-33 (`{% elif is_authenticated is undefined or is_authenticated %}`)
**Resolved:** Ticket 044 — the flip landed, implementing the "Forward commitment" paragraph of DECISIONS.md 2026-07-25. `{% elif is_authenticated is undefined or is_authenticated %}` split into an empty `{% elif is_authenticated is undefined %}` branch (nav-free) followed by `{% elif is_authenticated %}`, so absent flags degrade visibly while an explicit `is_authenticated=False` still renders the login link. The mutation probe in the ticket's AC4 now fails a `tests/test_nav_shell.py` test for all four authenticated full-page branches of `web/routes/overview.py` (lines 56, 77, 146, 174); previously all four were silent.

---

### Mutation-probe `.pyc` staleness trap is recorded only in a QA report

**Type:** quality
**Source:** Code review 040 (discovered by QA 040)
**File:** `docs/LEARNINGS.md` (append); evidence in `tickets/done/040-qa.md`
**Resolved:** Ticket 044 — appended "Purge `__pycache__` between mutation probes, or CPython replays the previous result" to `docs/LEARNINGS.md`, next to the patch-target gotcha. It records the size+mtime invalidation collision, the purge command, why `pytest -p no:cacheprovider` does not help, and points at `tickets/done/040-qa.md`.
