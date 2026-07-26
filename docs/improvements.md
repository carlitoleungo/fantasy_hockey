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

### League settings and stat categories re-fetched from Yahoo on every request

**Type:** bug
**Symptom:** Every authenticated page load makes at least 2 Yahoo API calls that return
season-invariant data. `get_league_settings()` and `get_stat_categories()` both GET the
same `/league/{league_key}/settings` endpoint and neither is cached, so a fully warm
parquet cache still costs 2 calls per render. On the waiver page these are the *only*
remaining calls once pools are warm, so they dominate the steady-state API budget.
**Root cause:** `data/client.py:65` (`get_league_settings`) and `data/client.py:94`
(`get_stat_categories`) call `_get()` directly with no cache check. Call sites include
`data/matchups.py:36` (every `get_matchups()`) and `web/routes/waiver.py:171` (every
waiver POST). The response changes at most once per season for stat categories, and
`current_week` changes weekly.
**Fix (not yet implemented):** Cache the parsed settings response per league via
`data/cache.py`. `current_week` is the only field with meaningful churn, so a short TTL
(1–6 h) on the whole settings payload captures nearly all the saving without risking a
stale week boundary. Note `get_matchups()` re-derives `current_week` from this call, so
the TTL must stay well under a week. Both functions should share one cached fetch rather
than each caching separately, since they hit the same endpoint.
**Affected files:** `data/client.py`, `data/cache.py`, `data/matchups.py`,
`web/routes/waiver.py`
**Discovered:** 2026-07-23 (Tech Lead M1 readiness consult)

---

### Cross-league duplication: `ww_lastmonth` and NHL schedule are cached per league or not at all

**Type:** quality
**Source:** Tech Lead M1 readiness consult 2026-07-23
**File:** `data/players.py:155` (`fetch_lastmonth_batch`), `data/schedule.py:37`
(`get_remaining_games`), `data/cache.py` path helpers
**Detail:** Last-30-day player stats come from `/players;player_keys=…/stats;type=lastmonth`,
which carries no `league_key` — the data is pure NHL fact, identical across leagues, but is
cached once per league. `get_remaining_games()` calls the public NHL API and is not cached at
all, putting 1–2 live third-party calls in the hot path of every "Last 30 days" render.
Deferred to M2 by DECISIONS.md 2026-07-23 "Cache: league-independent data gets a shared tier
at M2"; the M1 cache-hardening work only adds the `CACHE_DIR/_shared/` path affordance. When
building the tier, see that entry's "Known hazard" note — `_parse_stats` filters lastmonth
columns to the league's enabled stats, so raw `stat_id`-keyed values must be stored and
projected at read time.

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
**Update (audit 041) — take this before or with ticket 039.** Open since audit 001, but the M1 deploy changes its risk profile: on the production container a missing credential env var is the single most likely misconfiguration, and this fallback converts it into the least legible possible failure. Audit 041 also found that the same file carries four functions used only by the Streamlit prototype (`validate_and_consume_state`, `try_restore_session`, `get_session`, `clear_session` — imported by `app.py`, `pages/`, and `utils/common.py`, never by `web/`), roughly 45 of its 201 lines. Worth archiving them in the same pass, since their presence is what makes `auth/oauth.py`'s 0.3:1 test ratio look alarming when the FastAPI-live half of the file is in fact well covered.

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
**Update (code review 036a):** the same `_make_db()` / `_insert_session()` / `ctx` scaffolding also sits in `tests/test_home_routes.py` and `tests/test_overview_routes.py`, and ticket 036a added a fifth copy in `tests/test_nav_shell.py` (named `test_nav_shell_qa.py` at the time; renamed by ticket 040). The `tests/conftest.py` fix should cover all five, not just the projection trio.
**Update (audit 041) — the count is thirteen, not five, and this is the largest safe reduction available in the suite.** Files carrying their own `_make_db()` / `user_sessions` schema copy: `test_auth_routes.py`, `test_head_to_head_routes.py`, `test_home_routes.py`, `test_nav_shell.py`, `test_overview_routes.py`, `test_overview_routes_qa.py`, `test_projection_breakdown_qa.py`, `test_projection_matchup_qa.py`, `test_projection_matchup_route.py`, `test_projection_routes.py`, `test_session_middleware.py`, `test_waiver.py`, `test_waiver_routes.py`. Measured across the 14 web route test files: **1,489 of 4,592 lines (32%) sit before the first `def test_`**, and the extreme case is `tests/test_projection_matchup_qa.py` at 124 lines of preamble supporting 2 tests. Expected saving from a shared `conftest.py` is 800–1,100 lines with no coverage change. Audit 041 recommends this as its own ticket, paired with the `*_qa.py` file renames, and explicitly **not** paired with dropping rendered-HTML assertions (those are the only guard against a template edit silently breaking a page, which is the failure mode ticket 040 exists to catch).

---

### Error pages show the authenticated nav to logged-out visitors

**Type:** quality
**Source:** Code review 036a (raised by QA 036a)
**File:** `web/templates/error.html` line 1; render sites `web/main.py` lines 48-65
**Detail:** `error.html` extends `base.html` and passes no shell context, so the authenticated-nav default applies: an unauthenticated or demo visitor who hits a 500/502 error page sees Overview / Waiver / Projection / Logout, every one of which bounces them to `/auth/login` — the same defect ticket 036a just fixed for the home page. Pre-existing, and preserved deliberately by 036a's `base.html` default (that default is 036a AC3), so this is not a regression.
**Not a drive-by fix — needs a Tech Lead ruling first.** Both render sites are FastAPI exception handlers, which have no resolved `CurrentUser` in scope, so `shell_context()` cannot be called there; passing `None` would show authenticated users the logged-out nav instead. This is the case named in the `Revisit if` clause of DECISIONS 2026-07-03 ("a page family that needs nav state but has no user dependency in scope, making a request-only derivation unavoidable"). Cheapest option is probably a neutral error-page nav (app-name link only, no feature links), which needs no auth state at all. Suggested sequencing: once 036b lands, the PM scopes one sweep ticket covering every remaining `base.html` consumer, with the Tech Lead ruling on the mechanism as its dependency.
**Tech Lead ruling DONE (2026-07-25)** — `docs/DECISIONS.md` "Nav shell: render sites that cannot resolve a user declare the state unknown and render nav-free". Mechanism: an explicit `auth_state_unknown` key from a sibling helper in `web/routes/common.py`, spread into both handlers' contexts; `base.html` branches on it first and renders the brand link only; plus a "Back to home" link in `error.html`'s body. No auth derivation in the handlers, and **no dependency on 036b** — this can be scoped and landed standalone at M1. The related `base.html` default flip (absent flags ⇒ nav-free instead of authenticated nav) is a separate follow-up that *is* blocked on 036b; see the ruling's "Forward commitment" paragraph.

---

### TC18's league-label assertion in `test_home_routes.py` does not discriminate

**Type:** quality
**Source:** Code review 036a (proved by QA 036a mutation probe)
**File:** `tests/test_home_routes.py` lines 450-451
**Detail:** `test_home_authenticated_nav_has_feature_links_in_roadmap_order` (TC18) ends with `assert "Alpha League" in body`, above a comment claiming `selected_league_name` "is now threaded via shell_context on this branch". The assertion cannot prove that: the league list in the content area contains the same string, so a render that drops the header label still passes. QA confirmed this with a mutation probe. AC2 is properly guarded elsewhere — pre-existing TC9 (`test_home_header_shows_selected_league_name`) scopes the match to `<header>…</header>` and does fail under that mutation, as does `tests/test_nav_shell.py::test_authenticated_home_nav_and_league_label` — so this is redundancy, not a coverage gap. Fix: delete the assertion and its comment; TC18's job is nav ordering. The comment is the riskier half, since it could lead someone to delete TC9 as a duplicate.

---

### Post-036b stale comments about pages "not yet" passing `shell_context()`

**Type:** quality
**Source:** Code review 036b (flagged by both the Engineer and QA)
**File:** `tests/test_overview_routes.py` (`test_overview_renders_authenticated_nav_by_default`), `web/templates/base.html` lines 21-22
**Detail:** Two comments describe a migration state that no longer exists. The overview test's comment says "/overview has not adopted shell_context yet, so base.html must fall back to the authenticated nav" — since 036b, `/overview` does adopt it, so the test now proves the explicit `is_authenticated=True` branch, not the default branch. Its assertions remain correct and valuable; only the comment (and arguably the test name) is wrong. `base.html`'s comment ("pages that do not yet pass `shell_context()` render exactly as before") has one remaining beneficiary, `error.html`, which is the defect tracked in "Error pages show the authenticated nav to logged-out visitors" above. Fix the test comment in whichever ticket next touches that file; the `base.html` comment should be resolved by the DECISIONS 2026-07-25 default-flip follow-up rather than edited on its own.

---

### `base.html`'s authenticated-nav default is now unblocked, and 040 measured what it costs

**Type:** quality
**Source:** Code review 040 (evidence from QA 040's ablation probes)
**File:** `web/templates/base.html` lines 21-33 (`{% elif is_authenticated is undefined or is_authenticated %}`)
**Detail:** DECISIONS 2026-07-25 already commits to flipping this default (absent flags ⇒ nav-free header) and states the flip is blocked on 036b. **036b is done, so the flip is unblocked** — this entry exists so the follow-up is tracked as work rather than living only inside a decision paragraph. Ticket 040 also supplies the first direct measurement of the default's cost, and it is larger than the error-page defect it was previously known for. QA 040 ablated the header-label assertion from the three new authenticated branch tests, deleted each branch's `**shell_context(...)` spread in turn, and the module returned `32 passed` every time: with the default in place, a dropped spread on an *authenticated* branch is invisible to any nav assertion, because the nav falls back to exactly the nav the test expects. The only thing catching it is `assert "Alpha League" in _header_left(...)`, which works solely because `selected_league_name` also disappears with the spread. A future authenticated page rendered without a selected league would have no guard at all, and the same regression on a demo branch is caught immediately (the nav flips visibly). Fix: the flip described in the 2026-07-25 ruling's "Forward commitment" paragraph, which also retires the stale `base.html` comment tracked in the entry above and makes the nav assertions in `tests/test_nav_shell.py` load-bearing on authenticated branches instead of merely correct. Sequencing note for the PM: pair it with, or land it after, the `auth_state_unknown` error-page ticket, since both touch the same `base.html` branch block.

---

### Mutation-probe `.pyc` staleness trap is recorded only in a QA report

**Type:** quality
**Source:** Code review 040 (discovered by QA 040)
**File:** `docs/LEARNINGS.md` (append); evidence in `tickets/done/040-qa.md`
**Detail:** Mutation probes are now a standing verification technique in this workflow (036a, 036b and 040 all used one, and 040's acceptance criteria required one), so the trap QA 040 hit will recur. Lines 174, 241 and 311 of `web/routes/overview.py` are each exactly 77 bytes; deleting one and then another produces two source files of identical size, and when the mtimes land in the same second CPython treats the cached bytecode as current and reuses the **previous** probe's `.pyc`. QA 040's first pass consequently reported line 241 failing `test_authenticated_head_to_head_renders_authenticated_nav` — the line-174 result — and `pytest -p no:cacheprovider` does not prevent it, since that flag governs pytest's own cache, not CPython's. Purging `__pycache__` between iterations fixed it and all five probes then matched. The failure mode is a silently wrong probe result, which is worse than a crash: it can certify the wrong test as the guard for a branch. Fix: append a `docs/LEARNINGS.md` entry stating the size+mtime collision and the `__pycache__` purge as the required step between mutations. This belongs in LEARNINGS.md rather than in a ticket artifact — it affects future unrelated tickets, and the file already carries test-harness gotchas (see "Tests must patch the importing module's namespace"). The Reviewer cannot append to LEARNINGS.md under the persona rules, so this is for the next ticket that opens the file, or a one-line docs ticket.

---

### Atomic cache write is crash-safe against concurrent readers but not against machine restart

**Type:** quality
**Source:** Code review 037
**File:** `data/cache.py` `_atomic_write()` line 85
**Detail:** `_atomic_write()` writes a temp file and `os.replace()`s it onto the target, which is exactly what DECISIONS 2026-07-23 specifies and fully satisfies ticket 037's acceptance criteria — a concurrent *reader* can never observe a partial file. It does not protect against the machine going away mid-write. There is no `fsync()` on the temp file before the rename and no `fsync()` on the containing directory after it, so a Fly machine restart, migration, or power loss can leave the rename durable while the data blocks are not, producing a zero-length or truncated parquet on the volume. That is precisely the "corrupted file persists on the volume and does not self-heal" failure the DECISIONS entry is written to prevent, arriving through a different door. Related and smaller: a hard kill (SIGKILL, OOM) between `mkstemp()` and `os.replace()` leaves a `.{name}.XXXXXX.tmp` file behind, since cleanup lives in an `except` handler. Nothing globs the cache directory so this is dead weight rather than a correctness bug, but it accumulates on a 1 GB volume. Fix: flush and `os.fsync()` the temp file's descriptor before the rename, `os.fsync()` the directory descriptor after it, and sweep stale `.*.tmp` files from each league directory at startup. Deliberately out of scope for 037 — the ticket and the decision both scope the hardening to reader atomicity — so take it whenever `data/cache.py` is next opened, or sooner if the deployment ever reports an unreadable cache file after a restart.

---

### `optional_user` has no direct test coverage, including its session-deleting refresh branch

**Type:** quality
**Source:** Audit 041 (Theme B, auth coverage question)
**File:** `web/middleware/session.py` lines 102-158; tests would belong in `tests/test_session_middleware.py`
**Detail:** `optional_user` is referenced by no test file. It is not a thin wrapper around
`require_user`: lines 129-152 are a near-verbatim 24-line copy of `require_user`'s
refresh-update-or-delete block, differing only in returning `None` where the other raises
`RequiresLogin`. `require_user`'s copy is covered six ways (valid token, expiring token, Yahoo
rejecting the refresh, network error, a parametrised 59s/61s expiry boundary, sequential healthy
requests); `optional_user`'s is exercised only indirectly by the home-route tests, and only on the
happy paths where no refresh occurs. The untested branch includes `DELETE FROM user_sessions` on
refresh failure. Both copies are correct as read, so this is a missing regression guard rather than
a live defect, but it is the only security-relevant coverage gap in the 032-037 batch and it gets
worse once the app is public. Fix: mirror the six `require_user` cases against a route using
`optional_user` (`GET /` is the only one today), patching `auth.oauth.requests.post` as the existing
tests do. Note the name-scan that raised this also produced a false negative on `_try_refresh` —
that function *is* well covered, through the transport patch rather than by name.

---

### Stale `position` form field in 14 `tests/test_waiver.py` call sites

**Type:** quality
**Source:** Audit 041
**File:** `tests/test_waiver.py` lines 168, 198, 214, 236, 271, 313, 345, 400, 464, 497, 529, 565, 601, 635
**Detail:** Each of these POSTs `data={..., "position": "All", ...}`. Ticket 032 renamed the form
field to `positions: list[str]` on both handlers, so `position` is no longer declared anywhere in
`web/routes/waiver.py`. FastAPI silently ignores unknown form fields, so the tests pass and the
behaviour is correct. The cost is legibility: the tests read as though they exercise a position
filter and do not. Ticket 032 fixed the one test its rename broke (`test_waiver_post_position_no_matching_rows`)
and did not sweep the rest; neither QA nor the code review caught it. Fix: delete the key, or change
it to `"positions": ["All"]` where the intent really is "no position filter". Worth folding into the
`tests/conftest.py` consolidation ticket, which will be in this file anyway.

---

### `data/cache.py` module docstring still describes the Streamlit caching layer

**Type:** quality
**Source:** Audit 041
**File:** `data/cache.py` lines 4-6
**Detail:** The docstring opens "Two-layer caching model: ... `@st.cache_data` handles the
in-session memory layer (applied in `pages/` as needed)". The FastAPI app has no such layer, and
`CLAUDE.md` records `@st.cache_data` as a legacy Streamlit-prototype note that does not apply. Ticket
037 edited this docstring (it added the Concurrency paragraph at the bottom) and left the stale claim
at the top, so a reader now meets a false statement before the accurate one. Fix: drop the two-layer
framing and describe the disk layer only. Small, but it sits in the file the M1 cache work keeps
reopening — take it with the `fsync` item below.

---

### `audit_due.py` silently ignores a `Tickets reviewed` section that is not a bullet list

**Type:** bug
**Symptom:** A completed audit does not register. `scripts/audit_due.py` keeps reporting
`AUDIT DUE` with the same ticket list after `.team/audits/NNN-audit.md` has been written and the
audit ticket moved to `tickets/done/`, so the next architectural-surface ticket stays blocked for no
reason.
**Root cause:** `scripts/audit_due.py:77` matches covered ticket IDs with
`re.match(r"\s*-\s+\**([A-Za-z0-9][\w-]*)", line)` over the `## Tickets reviewed` section. Only
bullet lines match. A markdown table renders correctly to a human and yields zero covered IDs, which
also leaves `high_water` at its previous value, so every ticket since the last audit stays uncovered.
There is no warning: an audit file that parses to zero tickets is indistinguishable from no audit at
all. Hit during audit 041, where the section was first written as a table.
**Fix (not yet implemented):** Either make the parser accept table rows (`| **032** | ...`) alongside
bullets, or have it print a warning when an audit file is found whose `Tickets reviewed` section
parses to zero IDs — the second is smaller and catches every future format drift, not just tables.
Separately, `.team/reviewer.md`'s audit-output template shows bullets but does not say they are
load-bearing; one sentence there would prevent the mistake at the source. It fails in the safe
direction (over-reporting audits as due, never under-reporting), so this is a friction bug rather
than a correctness risk.
**Affected files:** `scripts/audit_due.py`, `.team/reviewer.md`
**Discovered:** 2026-07-26 (Audit 041)

---

### `_merge_into_cache` read-modify-write sits outside the per-league cache lock

**Type:** bug
**Symptom:** Two concurrent `get_matchups()` calls for the same league can lose one caller's
freshly fetched week. Reproduced by QA on ticket 038 by stalling one thread between its read
and its write: pre-038 `cache.append` left weeks `[1, 2, 3]` on disk, post-038
`_merge_into_cache` left `[1, 2]`. The loss is transient — the next `get_matchups()` call
re-derives `_last_cached_week`, re-fetches the missing week, and the file returns to `[1, 2, 3]`
with 0 duplicates. No bloat, no duplicate rows, no corrupted file, no permanent data loss; the
cost is one extra Yahoo call on the following request.
**Root cause:** `data/matchups.py:99-105` calls `cache.read()` and then `cache.write()`.
`cache.write()` takes the per-league `threading.Lock` (ticket 037 / DECISIONS 2026-07-23), but
the read that produced the merged frame happened before the lock was acquired, so two callers
can build their merged frames from the same pre-merge snapshot. `cache.append()`, which this
replaced, held the lock across both halves. Ticket 038 forbade touching `data/cache.py`, so the
Engineer correctly flagged this rather than widening scope.
**Fix (not yet implemented):** Add a `cache.merge_on(league_key, data_type, df, subset)`
primitive to `data/cache.py` that acquires the league lock once and performs read, concat,
`drop_duplicates(subset=..., keep="last")`, and `_write_unlocked` inside it, then have
`data/matchups.py` call it instead of the private `_merge_into_cache`. This also settles the
open question of whether cache-state merges belong in the cache layer at all (see the
Tech Lead finding in `tickets/done/038-review.md`) — `append` and `upsert_lastmonth_cache` are
both cache-layer primitives, and `_merge_into_cache` is the first merge to live outside it.
Note `data/cache.py` is an architectural surface: this needs a Tech Lead ruling before it is
scoped, not just an Engineer ticket.
**Affected files:** `data/matchups.py`, `data/cache.py`
**Discovered:** 2026-07-26 (QA + Review 038)

---

### `cache.append()` has no production callers left

**Type:** quality
**Source:** QA 038 finding, confirmed in Review 038
**File:** `data/cache.py:172`
**Detail:** Ticket 038 replaced the last non-test call site (`data/matchups.py`). `grep` over
`data/`, `web/`, `analysis/`, `auth/`, and `scripts/` finds no remaining caller; only
`tests/test_cache.py` exercises it. Decide deliberately: either delete it (and its tests) as
dead code, or keep it as intentional API surface — in which case the `cache.merge_on` bug entry
above is the natural place to reshape it, since `merge_on` is `append` plus a dedup subset.
Do not delete it in isolation before that ruling; 037's headline acceptance criterion is
written against `append`, so removing it silently drops that regression test.

---

### `docs/DECISIONS.md` cites `data/matchups.py` line numbers that have drifted

**Type:** quality
**Source:** QA 038 finding
**File:** `docs/DECISIONS.md:248`
**Detail:** The 2026-05-31 "current_week always re-fetched" entry points at "`data/matchups.py`
lines 44–46". Ticket 038 added a line to the module docstring, so that block is now at lines
45–47. `docs/DECISIONS.md` was not in 038's `Touches`, so the Engineer was right to leave it.
The durable fix is to cite the symbol rather than the line range (e.g. "the unconditional
`current_week` append in `get_matchups()`") — line numbers in a decisions log rot on every
adjacent edit. Tech Lead owns this file.

---

### `tests/test_matchups.py` module docstring still describes the append write path

**Type:** quality
**Source:** Review 038
**File:** `tests/test_matchups.py:1-9`
**Detail:** The docstring says tests cover "that new rows are appended correctly". Since 038 the
write path merges and overwrites rather than appends, and the file gained a parquet-hygiene
section the docstring does not mention. One-line wording fix when the file is next touched.

---

## Closed

Resolved items are archived in [`docs/archive/improvements-closed.md`](archive/improvements-closed.md)
to keep this active tracker lean (it is read on every persona spawn). When you resolve an
item, move its entry there with a brief `**Resolved:**` note (ticket number + what changed),
rather than leaving it here.
