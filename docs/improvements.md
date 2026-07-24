# Improvements & Bug Tracker

> **Scope:** Two kinds of items, distinguished by a **Type** field:
>
> - **`quality`** — code-quality improvements, minor cleanups, and nits that aren't worth
>   fixing immediately but should be addressed when the affected file is next touched.
>   The Reviewer adds these and curates the file.
> - **`bug`** — defects in the current FastAPI stack or the preserved data/analysis/auth
>   layers. Anyone (owner, QA, Reviewer) may file a bug entry; bug entries use the fuller
>   template below (Symptom / Root cause / Fix) so an Engineer can pick them up cold.
>
> For bugs specific to the Streamlit prototype, see
> [`docs/archive/prototype-bugs.md`](archive/prototype-bugs.md).

**Quality item template:**

```
### [Short description]
**Type:** quality
**Source:** [Code review NNN / Audit NNN / owner note]
**File:** `path/to/file` line N
**Detail:** [What to fix and why]
```

**Bug template:**

```
### [Short description]
**Type:** bug
**Symptom:** [What goes wrong, observably]
**Root cause:** [If known]
**Fix (not yet implemented):** [Direction, if known]
**Affected files:** [paths]
**Discovered:** YYYY-MM-DD
```

---

## Open

### `matchups.py` re-fetch loop causes parquet bloat and unnecessary API calls

**Type:** bug
**Symptom:** On every page load for the rest of a given day, `prev_week` stats are re-fetched from Yahoo and appended to the parquet file. Additionally, since the `bug-week23-all-zeroes` fix, `current_week` is appended on **every** `get_matchups()` call (always, not just once per day — see DECISIONS.md 2026-05-31). The data stays correct in memory (duplicate rows are dropped on read) but the parquet grows by up to two rows-per-team per session and adds latency on every load.
**Root cause:** The intent of `matchups.py` lines 50–54 is to re-fetch `prev_week` once per day in case its stats were updated after an earlier fetch:
```python
lu = cache.last_updated(league_key, "matchups")
if lu is not None and lu.astimezone().date() == _date.today():
    weeks_to_fetch = [prev_week] + weeks_to_fetch
```
The condition fires on **every** page load for the rest of the day, because each successful fetch updates `last_updated` to now (today). This appends `prev_week` rows to the parquet on every load. The unconditional `current_week` append (intended behaviour per DECISIONS.md 2026-05-31) compounds the growth. `drop_duplicates(keep="last")` in `get_matchups()` keeps the data correct in memory, but the parquet bloats over time.
**Fix (not yet implemented):**
- Replace the `last_updated == today` condition with a per-week staleness check, or track a separate `prev_week_refreshed_date` value in `last_updated.json`.
- Alternatively, use `cache.write()` (overwrite) instead of `cache.append()` after deduplication, so the parquet stays clean regardless of how many times re-fetch runs. This also absorbs the `current_week` growth without touching the (correct) always-re-fetch behaviour.
**Affected files:** `data/matchups.py`, `data/cache.py`
**Discovered:** 2026-03-30

---

### Nav header shows auth links to unauthenticated visitors

**Type:** quality
**Source:** Audit 024 (noted in ticket 023 done note)
**File:** `web/templates/base.html` line 22–24
**Detail:** `base.html` renders "Overview", "Waiver", and "Logout" in the nav unconditionally. After ticket 023 landed optional auth on `GET /`, unauthenticated visitors on the home page see a "Log in with Yahoo" CTA in the content area but also see three nav links that all route to auth-gated pages or a no-op logout. Fix: pass an `is_authenticated` boolean (or equivalent) from each route context so the base template can render "Login" instead of "Overview / Waiver / Logout" for unauthenticated visitors. The home route already has `current_user is None` to derive this from.

---

### Add demo mode entry point on home page

**Type:** quality
**Source:** Owner note post-020
**File:** `web/templates/home.html`, `web/routes/home.py` (or wherever the home route lives)
**Detail:** Unauthenticated visitors have no visible way to reach demo mode — `/demo/overview` and `/demo/waiver` exist but are not linked from the home page. Add a "Try the demo" button or link on the home page (logged-out view) so visitors can explore the app without signing in. The home route already distinguishes authenticated vs. unauthenticated state (via `optional_user`), so the demo CTA only needs to appear in the unauthenticated branch.

---

### Simplify redundant assertion in TC14 of `test_home_routes.py`

**Type:** quality
**Source:** Code review 023
**File:** `tests/test_home_routes.py` line 367
**Detail:** `test_home_unauthenticated_shows_login_cta` (TC14) contains `assert "<h1" in body and "Your Leagues" not in body.split("</head>", 1)[1]`. The `"<h1" in body` guard is always true (the unauthenticated `home.html` branch contains an `<h1>`), so it adds no signal. The `body.split("</head>", 1)[1]` idiom is unusual and harder to read than a plain `not in body`. Simplify to `assert "Your Leagues" not in body` — the adjacent `assert "Fantasy Hockey Waiver Wire" in body` already confirms the correct heading is present.

---

### Stale Streamlit fallback in `auth/oauth.py` credential helpers

**Type:** quality
**Source:** Audit 001 (surfaced during credential rotation)
**File:** `auth/oauth.py` lines 151, 158, and the `_redirect_uri` equivalent
**Detail:** `_client_id()`, `_client_secret()`, and `_redirect_uri()` check the env var first, then fall back to `st.secrets["yahoo"][...]`. The Streamlit fallback is dead code — the app runs on FastAPI and `streamlit` is not in `requirements-web.txt`. If the env var is missing, the fallback silently attempts to `import streamlit` and fails at runtime with a confusing `ModuleNotFoundError` rather than a clear "YAHOO_CLIENT_ID not set" error. Remove the `st.secrets` fallback and replace with `raise RuntimeError("YAHOO_CLIENT_ID environment variable not set")` so misconfigured environments fail fast with a useful message.

---

### Leaderboard: all-zero rows when a week has no player activity

**Type:** bug
**Symptom:** The leaderboard defaults to the latest available week. During the championship period (or any week where most players haven't played yet), the API returns `'-'` for unplayed stats, which `data/matchups` coerces to `0`. The table renders correctly but shows all zeros, giving no useful ranking signal.
**Root cause:** Default-week selection doesn't account for weeks with no recorded activity.
**Fix (not yet implemented):** Detect an all-zero week and either default to the most recent week with non-zero data, show a "data not yet available" notice inline, or exclude the current in-progress week from the default selection (consistent with the `exclude_weeks` parameter already present on `avg_ranks()`).
**Affected files:** `web/routes/overview.py`, `data/matchups.py`
**Discovered:** QA 015 manual verification

---

### Leaderboard: tied "worst" cells may not get bg-red-100

**Type:** bug
**Symptom:** When two teams are tied for second-worst in an N-team league, neither cell is coloured `bg-red-100`.
**Root cause:** `_compute_cell_ranks` uses `method='min'` for ties — both tied teams receive rank N-1 and no team receives rank N, so the worst-rank check never matches. Acceptable for v1.
**Fix (not yet implemented):** Use `method='max'` for the worst-rank check, or compute a separate "is_worst" flag that detects the actual minimum value per column.
**Affected files:** `web/templates/overview/_table.html`, `web/routes/overview.py`
**Discovered:** Ticket 015 engineer note

---

### Move `_is_rate_stat` import to module level in `tests/test_projection.py`

**Type:** quality
**Source:** Code review 002
**File:** `tests/test_projection.py`
**Detail:** `_is_rate_stat` is imported inside the `test_is_rate_stat` function rather than at the top of the file with the other imports. Minor style inconsistency — either placement works, but moving it to module level matches every other import in the file.

---

### Tighten row-count assertion in `test_logout_unknown_session_id_redirects`

**Type:** quality
**Source:** Code review 007
**File:** `tests/test_auth_routes.py`
**Detail:** Test 7 asserts `len(rows) == 0` against the full `user_sessions` table after calling logout with an unknown session ID. The assertion is trivially true — no row was inserted before the call. The test's real intent (no error on unknown ID) is already covered by the status code and location checks. Either remove the row-count assertion or insert a dummy row first so the assertion has something to prove.

---

### Scope `client` fixture in `test_error_handling.py` to module level

**Type:** quality
**Source:** Code review 009
**File:** `tests/test_error_handling.py` line 8
**Detail:** The `client` fixture is function-scoped (default), so the two test routes (`/test/http-error`, `/test/unhandled`) are registered on the production `app` object once per test — 7 times total. FastAPI silently accumulates duplicate route entries. Add `scope="module"` to the fixture decorator so routes are registered once per test session.

---

### TC4 (`test_demo_waiver_shell_returns_200`) only asserts form action — misses stat chips

**Type:** quality
**Source:** Code review 018
**File:** `tests/test_waiver_routes.py` TC4 (~line 158)
**Detail:** TC4 checks status 200 and that `/demo/api/waiver/players` appears in the response body. It does not verify position radio inputs or stat checkbox values. The original bug (metadata columns as stat chips) was caught by manual QA, not by this test. Extend TC4 to assert all 6 position values and the expected stat names from the fixture DataFrame — matching the pattern TC1 already uses for `GET /waiver`.

---

### Goalie breakdown table omits the shared offense categories (Assists)

**Type:** quality
**Source:** Code review 034
**File:** `web/routes/projection.py` lines 228-241 (`skater_columns` / `goalie_columns`)
**Detail:** Ticket 034 splits the roster breakdown on Yahoo's `stat_group`, so the Goalies table shows only `goaltending` categories. Yahoo tags Assists as `offense` even though it applies to goalies too (`data/client.py:107-108` comments on exactly this), so a goalie's assists no longer appear anywhere in the breakdown. Measured impact in the demo snapshot is zero — all 260 cells that disappeared per fragment held `0.0`/`0.00`, and all 8 demo goalies have no offense stats at all — but a live league where a goalie records an assist would lose that number from the view. This is a product call, not a defect: the ticket explicitly prescribed the `stat_group` partition and sanctioned the two-table option. Fix direction if wanted: give the goalie columns the `goaltending` categories plus any `offense` category whose Yahoo `stat_position_types` include goalies (the raw field is already parsed in `data/client.py`, just not retained). PM may promote this to a ticket if the owner wants goalie assists back.

---

### `test_breakdown_values_unchanged_from_ticket_030` name overstates what it asserts

**Type:** quality
**Source:** Code review 034
**File:** `tests/test_projection_matchup_route.py` line 395
**Detail:** The test asserts `"11.0" in body`, `"6.0" in body`, `"2.50" in body` and `body.count("Projected Wins") == 2` against one mocked render. It is not a comparison against a pre-change render, so it cannot detect that a value changed relative to ticket 030, and the unanchored substring matching does not pin which cell holds each value (`"6.0"` also matches `16.0` or `6.05`). QA and review flagged this independently. Fix: rename to what it does (e.g. `test_comparison_table_and_tally_cards_render_expected_values`) and anchor each assertion to its cell rather than the whole body. Note a true pre/post comparison cannot live in a unit test — AC5 was verified separately by a two-server 535-cell diff during QA 034.

---

### Projection route test scaffolding duplicated across three test files

**Type:** quality
**Source:** Code review 034
**File:** `tests/test_projection_matchup_route.py`, `tests/test_projection_matchup_qa.py`, `tests/test_projection_breakdown_qa.py`
**Detail:** All three files carry their own verbatim copy of `_make_db()`, the `user_sessions` / `oauth_states` schema, the `TestClient` + `dependency_overrides` fixture, and the `TEAMS` / `SETTINGS` / `SCOREBOARD` / `LIVE_STATS` constants. There is no `tests/conftest.py`. Pre-existing duplication (two copies) that ticket 034 grew to three. Fix: add `tests/conftest.py` with a shared in-memory-session-DB fixture and a `client` fixture, and let the projection test modules keep only their own scenario data. Worth doing next time any of the three is substantially reworked.

---

## Closed

Resolved items are archived in [`docs/archive/improvements-closed.md`](archive/improvements-closed.md)
to keep this active tracker lean (it is read on every persona spawn). When you resolve an
item, move its entry there with a brief `**Resolved:**` note (ticket number + what changed),
rather than leaving it here.
