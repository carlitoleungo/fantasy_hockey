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

### Streamlit-only functions remaining in `auth/oauth.py`

**Type:** quality
**Source:** Audit 001 (surfaced during credential rotation); credential-helper half closed by ticket 051
**File:** `auth/oauth.py:58-117`
**Detail:** The file still carries four functions used only by the Streamlit prototype (`validate_and_consume_state`, `try_restore_session`, `get_session`, `clear_session` — imported by `app.py`, `pages/`, and `utils/common.py`, never by `web/`), roughly 45 of its (now shorter) line count. Worth archiving once the Streamlit prototype teardown is scoped, since their presence is what makes `auth/oauth.py`'s test ratio look alarming when the FastAPI-live half of the file is in fact well covered. Ticket 051 deliberately left these in place — removing them breaks the Streamlit prototype's import graph and is a cross-workstream teardown, not a small credential-helper fix.

**Update (Review 051) — the same teardown should also take `_pending_states`.** `auth/oauth.py:28-32` keeps an in-memory `_pending_states` dict for the Streamlit single-process flow, and `get_auth_url()` (line ~54) writes to it on *every* call, including the FastAPI path, which persists nonces to the `oauth_states` DB table instead. The only code that removes entries is `validate_and_consume_state()`, which `web/` never calls, so in the Fly process the dict grows by one 43-byte key per login attempt for the life of the machine and is never pruned. Not a correctness or security problem (the nonces are single-use, the DB is the authority, and a pinned machine restarts often enough that the growth is immaterial at M1 traffic), and deliberately not fixed in 051 — out of that ticket's scope. Fold it into the Streamlit teardown: when the four functions above go, `_pending_states`, `_NONCE_TTL_SECONDS`, and the `_pending_states[state] = ...` line in `get_auth_url()` go with them.

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
**Update (Audit 046) — stop waiting for a passing ticket.** The trap has now been hit independently by the Engineer, QA, and the Reviewer on 040, and Review 042 recorded a third vote for writing it down. Two audit cycles of "take it whenever someone next opens LEARNINGS.md" have produced nothing, because no ticket's `Touches` has included that file. Scope the one-line docs ticket.

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

### `docs/ARCHITECTURE.md` § Directory structure describes a planned tree, not the repo

**Type:** quality
**Source:** Review 039; scope widened by Audit 046
**File:** `docs/ARCHITECTURE.md:66-103` (the whole fenced tree; line 102 is one instance)
**Detail:** Line 102 still reads ``fly.toml  # planned, not yet in repo (deployment is a roadmap
item); port 8000; /data volume mount``. Ticket 039 landed the file, so "planned, not yet in repo"
is now wrong; the rest of the line (port 8000, `/data` mount) is accurate. While there, the tree
listing has no `.dockerignore` entry at all, which 039 also added at the repo root. Suggested
replacement: `fly.toml  # single pinned machine in iad; port 8000; /data volume mount` plus a
`.dockerignore  # keeps .env, app.db*, .cache/ out of the build context` line beside the
`Dockerfile` entry. Deliberately not fixed in 039 — `docs/` was outside that ticket's `Touches`
and outside what the Engineer may edit. **Tech Lead owns this file**; take it in the next
ARCHITECTURE upkeep pass rather than as its own ticket, since it is a factual correction with
no code impact.

**Update (Audit 046) — this is not a two-line fix; the whole tree is the April plan, never
reconciled.** Verified against the working tree:

| Listed | Reality |
|---|---|
| `routes/leagues.py` | Does not exist — the route file is `web/routes/home.py` |
| `routes/demo.py` | Does not exist — demo handlers live inside `overview.py` / `waiver.py` / `projection.py` on public routers |
| (absent) | `web/routes/common.py`, `web/routes/overview.py`, `web/templates.py`, `utils/` |
| `templates/waiver.html`, `leagues.html`, `projection.html` (flat) | Per-feature subdirectories with `_underscore` fragment partials: `waiver/index.html`, `waiver/_table.html`, `overview/`, `projection/` |
| (absent) | `templates/home.html`, `templates/error.html` |
| `fly.toml  # planned, not yet in repo` | Shipped by 039 |
| (absent) | `.dockerignore` |

Two consequences beyond tidiness. First, the template layout above is a *convention* — the
per-feature directory plus `_`-prefixed fragment naming — that no `docs/DECISIONS.md` entry
records and that ARCHITECTURE.md actively contradicts, so the only place a new feature page can
learn the pattern is by copying a neighbouring file. Second, this is the file a reviewer is told
to verify changes against, so a stale tree quietly weakens every future review. Suggested fix:
regenerate the tree from the repo in one pass and, in the same pass, decide whether the template
convention wants its own short DECISIONS entry.

---

### `fly.toml`'s `auto_stop_machines` boolean form should be re-checked with `flyctl` in hand

**Type:** quality
**Source:** Review 039 (QA 039 raised the deprecation half)
**File:** `fly.toml:36`
**Detail:** One item on `[http_service]`, deliberately left as-shipped because it cannot be
validated locally (`flyctl` is not installed and ticket 039 forbade `fly` commands, so
`fly config validate` never ran). Resolve it at the first deploy, when flyctl can confirm the
answer immediately.

`auto_stop_machines = false` uses the boolean form, which current flyctl treats as deprecated
in favour of `"off"`/`"stop"`/`"suspend"`. The boolean is still accepted and is the form
understood by *both* older and newer flyctl, so switching to `"off"` blind would trade a
deprecation warning for an unvalidated schema risk. If `fly config validate` warns, change it
to `"off"` then.

**Update — ticket 045 resolved the `auto_start_machines` half of this entry** (numbered item 2
as originally filed): `auto_start_machines` is now `true`, so Fly Proxy will restart the single
pinned machine if it stops for a reason other than a process crash. That flip needed no `flyctl`
and no re-opening of DECISIONS 2026-07-23 — auto-start only starts an existing stopped machine
and never creates one. Only the deprecation question above remains open.

---

### `min_machines_running = 1` is inert as configured, and DECISIONS 2026-07-23 names it as the pin mechanism

**Type:** quality
**Source:** Review 045 (inertness first spotted by QA 039, corollary drawn in Review 039)
**File:** `fly.toml:38`, `docs/DECISIONS.md:170`
**Detail:** `min_machines_running` applies only when `auto_stop_machines` is `stop`/`suspend`. With
`auto_stop_machines = false` it has no effect, so `min_machines_running = 1` neither keeps a machine
running nor contributes to the single-machine pin. The pin comes from the absence of
`max_machines_running` / `concurrency` / `[processes]` / `[[services]]` / `regions` plus the single
`[[vm]]` — verified exhaustively in `tickets/done/039-review.md` § "On the single-machine pin".
Option A of the 2026-07-23 entry describes the chosen shape as "`min_machines_running = 1`, no
autoscaling, single region `iad`", which reads as though the key is load-bearing on the pin. It is
not, and the key is a floor rather than a spawner, so nothing is broken today — the cost is that a
future reader can take `min_machines_running = 1` as a guarantee that one machine is always up,
which is precisely the false comfort ticket 045's `auto_start_machines` flip existed to correct.
Filed here because ticket 045 resolved and deleted the improvements entry whose text was the only
remaining record of it. Fix: reword Option A (and the Decision line) to attribute the pin to the
absent autoscaling keys and the single `[[vm]]`, mentioning `min_machines_running = 1` as inert
statement-of-intent. Worth deciding in the same pass whether to keep the key at all — it is
harmless, and it becomes meaningful the moment `auto_stop_machines` is ever set to `stop`.
**Tech Lead owns `docs/DECISIONS.md`**; take it with the other DECISIONS/ARCHITECTURE upkeep items
in this file, and it can also be answered at `fly config validate` time alongside the
`auto_stop_machines` entry above.

---

### Error page "Back to home" link does not read as clickable

**Type:** quality
**Source:** Code review 042 (raised by QA 042)
**File:** `web/templates/error.html` line 9
**Detail:** The recovery link ticket 042 added renders as `text-sm text-gray-600` with no underline
and no link colour, so in a browser it reads as a third line of body copy rather than a control.
It satisfies 042's AC3 (visible, anchored to `/`) and the classes are copied verbatim from the
`base.html` nav links, so it is consistent with the current markup rather than a defect in it —
but it is now the *only* way off the error page for a visitor who does not think to click the
brand link, so an affordance nobody recognises has a real cost. Deliberately not fixed in 042:
that ticket puts restyling the error page explicitly out of scope, and a one-off restyle here
would diverge from the shared link styling. **Belongs to the M1 UI re-design**
(`docs/ROADMAP.md` § M1 item 3), which should settle a single link/control style and apply it to
the nav and this link together. Related observation from QA 042, same owner: at 375 px the error
body (`max-w-xl mx-auto`, no horizontal padding) clips at the right edge — confirmed pre-existing
by rendering the pre-042 templates at the same width, and in fact improved by 042, which removed
four nav links that also overflowed that header.
**Update (Ticket 050):** the 375 px clip described above is fixed — `error.html`'s container
now carries `px-4` like every other page shell. The link-affordance half (no underline, no
link colour) is unchanged and deliberately left for the M1 UI re-design; this entry stays open
for that half.

---

### Front-end CDN dependencies are unpinned and Tailwind's is a development build

**Type:** quality
**Source:** Audit 046 (deployment-readiness sweep)
**File:** `web/templates/base.html:7-9`
**Detail:** Every page loads three third-party scripts from three different CDNs at request time:
`cdn.tailwindcss.com`, `unpkg.com/htmx.org@2.0.4`, and `cdn.jsdelivr.net/.../alpinejs@3.x.x`.
This implements DECISIONS 2026-04-10 "Stack: FastAPI + HTMX + Jinja2; no JS build pipeline"
faithfully and was the right call for a local prototype, but that entry was written six months
before the app had a public URL and its `Revisit if` clause is about UI richness, not delivery.
Three things change once `fly deploy` runs. (1) `cdn.tailwindcss.com` is Tailwind's in-browser
JIT compiler, which its own documentation says is for development only — it ships a compiler to
every visitor, recomputes styles on each load, and logs a console warning on a public site.
(2) Alpine is pinned to `3.x.x`, a floating range, so a future upstream release lands in
production unreviewed; htmx, by contrast, is pinned exactly, so the file is already inconsistent
with itself. (3) Three CDNs are three availability and supply-chain dependencies in front of an
app whose entire M1 promise is a stable HTTPS URL, and none of them is covered by the
single-machine reasoning in DECISIONS 2026-07-23. Nothing here is broken today and no exposure is
claimed. Fix, cheapest first: pin Alpine to an exact version, then decide whether Tailwind stays
a CDN compiler or becomes a vendored stylesheet under `web/static/`. **Route to the M1 UI
re-design** (`docs/ROADMAP.md` § M1 item 3) — it is the pass that will touch every template's
classes anyway, and the Tailwind half is a genuine decision the Tech Lead should record rather
than an Engineer nit.

---

### Orchestrator tells QA to read the done note first; the Test Engineer persona says not to

**Type:** bug
**Source:** Audit 046 (disclosed as a persona deviation by QA on 038, 042, and 043)
**File:** `.team/orchestrator.md:114` vs `.team/test-engineer.md:28-32`
**Detail:** The orchestrator's QA task prompt says "Read `tickets/NNN-done.md` first to find what
to verify, then re-read the ticket". The Test Engineer persona says the opposite: input 1 is the
ticket, and input 2 is to "**Skim — but do not anchor on** — the Engineer's
`tickets/NNN-done.md`". The anchoring guard exists so QA derives its plan from the acceptance
criteria rather than reproducing the Engineer's proof. Because the launching prompt overrides the
persona in practice, QA disclosed the deviation in three of the six tickets in this batch (038,
042, 043) and each time had to spend a paragraph arguing the verification was still independent.
No verification was actually compromised — QA compensated each time with its own harness and
parameters, and the reviewers agreed — so this costs report space and reviewer attention rather
than correctness. Fix: one line in `.team/orchestrator.md:114`, reordered to "Read the ticket
first, then skim `tickets/NNN-done.md`", so the prompt stops contradicting the persona it spawns.
Owner action — personas and orchestration files are outside what any agent in this workflow edits.

---

## Closed

Resolved items are archived in [`docs/archive/improvements-closed.md`](archive/improvements-closed.md)
to keep this active tracker lean (it is read on every persona spawn). When you resolve an
item, move its entry there with a brief `**Resolved:**` note (ticket number + what changed),
rather than leaving it here.
