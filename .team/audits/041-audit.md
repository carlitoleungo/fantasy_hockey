## Audit Checkpoint 041 — covering tickets 032, 034, 035, 036a, 036b, 037

**Date:** 2026-07-26

Weighted count 5.5 / 5 (035 light ½, the other five full 1 each). Two themes: (A) cache and
nav-shell conventions, the two surfaces that saw significant work; (B) test-suite health, an
owner-requested direction the standard checklist does not cover.

> **The shipped code is sound. Every finding in this report is about the material around the
> code: test scaffolding, stale prototype code in `auth/oauth.py`, and one naming convention
> that has quietly inverted its own meaning.** No blocker, no decision contradicted, no
> architectural violation in six tickets.

**TL;DR**

- **Verdict: HEALTHY.** Ticket 039 (`fly.toml`) is unblocked and may be scoped.
- **Theme A: both surfaces conform.** All 12 nav-shell branches are correct and complete, and the cache hardening implements both 2026-07-23 decisions literally. One decision (2026-07-25 error-page nav) is ratified but has no ticket.
- **Theme B: the suite is not too big, it is badly factored.** Roughly 1,489 lines of duplicated harness sit in 14 route-test files. The real gaps are `optional_user`'s untested token-refresh branch and ~45 lines of Streamlit-only code still living in `auth/oauth.py`.

---

### Tickets reviewed

- **032** (feature) — Waiver wire multi-position filter (`web/routes/waiver.py`, `waiver/index.html`, `tests/test_waiver.py`). Correct; one API-volume consequence nobody quantified.
- **034** (feature) — Week Projection roster-breakdown readability (`web/routes/projection.py`, `projection/_matchup.html`). Correct; the strongest acceptance evidence of the batch.
- **035** (refactor, light) — Converge the projection matchup route on `team_key` (`web/routes/projection.py`). Correct; clean light-ticket execution.
- **036a** (feature) — Nav shell foundation: `shell_context()` + conditional `base.html` (`web/routes/common.py`, `base.html`, `web/routes/home.py`). Correct.
- **036b** (feature) — Demo nav adoption (`web/routes/overview.py`, `waiver.py`, `projection.py`). Correct; all 12 migrated branches verified against source, not against the handoff.
- **037** (refactor) — Cache write-hardening: atomic rename + per-league lock + `_shared/` affordance (`data/cache.py`, `tests/test_cache.py`). Correct; the locking discipline holds under independent re-tracing.

Full suite re-run during this audit: `.venv/bin/python -m pytest tests/` → **453 passed**, 0 failed.

---

### Prior audit (032) close-out — verified, not assumed

All six suggested actions from `.team/audits/032-audit.md` are resolved, and two of them were
institutionalised rather than handled once:

| Action | Status |
|---|---|
| 1. Close the resolved `/demo/overview` tests item | DONE. `docs/archive/improvements-closed.md:35-40`, with a ticket-027 resolution note. |
| 2. Graduate the demo-nav gap to a ticket | DONE. Became 036a + 036b, both shipped. |
| 3. File the query-param convergence ticket | DONE. Became 035, shipped. |
| 4. Add "close the improvements item this ticket was scoped from" to the DoD | DONE, and **institutionalised**: `.team/engineer.md:159-168` and `.team/pm.md:65-69` both now carry it as a standing rule, not a per-ticket note. |
| 5. Write redirect ACs against the real guard target; cite live DECISIONS entries | DONE. 035, 036a, 036b and 037 all cite live entries; no stale citation found this cycle. |
| 6. Ratify the shared live/demo compute helper | DONE. `docs/DECISIONS.md` 2026-07-03 "Web routes: demo and live handlers share a single compute/render helper". |

Action 4 is the one worth calling out. The recurring failure across audits 024 and 032 was
resolved improvements items lingering under `## Open`. That did not recur once in this batch:
032, 034, 035 and 036a each closed an item and named it in the handoff, and 036b and 037 each
explained in writing why they closed none. The process fix worked.

---

### Theme A — cache and nav-shell conventions

**Both surfaces conform. Neither needs corrective work.**

#### Nav shell (036a, 036b) — complete and consistent

I verified the branch count against the source rather than the handoffs. Every template that
extends `base.html` and every handler that renders one:

| Render site | Template | Shell context |
|---|---|---|
| `home.py` ×2 | `home.html` | Present (036a) |
| `overview.py` ×8 | `overview/index.html`, `overview/head_to_head.html` | Present (036b) |
| `waiver.py` ×2 | `waiver/index.html` | Present (036b) |
| `projection.py` ×2 | `projection/index.html` | Present (036b) |
| `main.py` ×2 (exception handlers) | `error.html` | **Absent by design** |

That is 14 of 14 route-owned branches migrated. All eight fragment handlers correctly pass no
shell context, and no explicit `selected_league_name` key survives anywhere under `web/` outside
the helper, so the silent-blanking trap the 036a review predicted cannot fire. Feature-link
ordering (Overview → Waiver → Projection) is preserved in both nav variants.

`error.html` is the sole remaining consumer of the "flags absent ⇒ authenticated nav" default,
which is exactly the state `docs/DECISIONS.md` 2026-07-25 anticipates. Nothing was missed beyond
what ticket 040 already covers.

**One gap, and it is a sequencing gap rather than a code one.** The Tech Lead ruled on the
error-page nav on 2026-07-25 and the decision is fully specified (an `auth_state_unknown` key
from a sibling helper in `common.py`, a leading `base.html` branch, a "Back to home" link in
`error.html`). The entry explicitly states it has **no dependency on 036b** and can land
standalone at M1. 036b has now shipped, so both that fix and the `base.html` default flip its
"Forward commitment" paragraph describes are unblocked, and neither has a ticket. A ratified
decision with no ticket is how the demo-nav gap survived two audit cycles; see suggested action 2.

#### Cache (037) — conformant, with the four named items dispositioned

| Item the ticket asked me to rule on | Finding |
|---|---|
| **~350-line diff vs. the ~200-line halt heuristic** | The heuristic should count **source lines only**. See finding below. |
| **`None` league key no longer fails fast** | **Acceptable until M2.** Traced independently: `_shared/` is unreachable in production. |
| **Live-Yahoo browser walk never run** | **Recorded as an open owner verification, not a pass.** |
| **`fsync` improvements entry** | **Still tracked and correctly scoped out of 037.** |

On the diff-size heuristic: the orchestrator halt list at `.team/orchestrator.md:168` reads
"cumulative diff exceeds ~200 lines". Ticket 037's cumulative diff was ~350 lines, but the source
churn was +139/−31 in one `Touches` file and the remaining +243 was the concurrency test suite the
ticket's own acceptance criteria demanded. The heuristic exists to bound the risk of a large
*behaviour* change going in without human review. Test lines carry the opposite risk profile: a
ticket that adds 240 lines of tests is safer than one that adds 40. Counting them together
penalises exactly the behaviour the process wants. **Recommend narrowing the heuristic to
non-test source lines**, with a separate (higher, or purely advisory) note when the test diff is
large. The orchestrator handled 037 correctly by surfacing rather than halting, but that required
judgment the rule should not have demanded.

On the lost fail-fast net: before 037, a `None` league key reaching a cache call raised
`TypeError`. It now resolves silently to `_shared/`. I traced all ten production `cache.*` call
sites (`data/matchups.py:52,67,69,94`; `web/routes/waiver.py:187,188,197,215,216,226`) and
confirmed the reviewer's conclusion. Every one passes `league_key` positionally; the only `None`
league in the codebase is `_waiver_post_impl`'s demo path, and every cache call in that function
sits inside the `else:` of `if demo:`. The authenticated handlers return early when
`_get_league_key()` is falsy. `_shared/` cannot be reached. **This is acceptable until M2**, and
the M2 shared-tier ticket should be told the net is gone. It is already recorded in `037-review.md`.

On the live-Yahoo walk: **recording it as an open owner verification.** The Engineer stated plainly
that they could not drive authenticated `/waiver` and `/overview`, and QA then closed most of that
gap properly, building a harness with `data/cache.py` fully unmocked against a real temp
`CACHE_DIR` and driving cold, warm, and eight concurrent authenticated requests. What remains
unobserved is only the Yahoo OAuth handshake itself, which touches no cache code. This is honest
reporting, not a verification gap, but it stays open until the owner logs in.

On `fsync`: the entry "Atomic cache write is crash-safe against concurrent readers but not against
machine restart" is present under `## Open` in `docs/improvements.md` and correctly scoped out of
037. It matters more once ticket 039 puts the app on a Fly volume that can be migrated or
restarted under it. See suggested action 3.

**One item neither 037's review nor QA caught.** `data/cache.py`'s module docstring still opens
with "Two-layer caching model: ... `@st.cache_data` handles the in-session memory layer (applied
in `pages/` as needed)". Ticket 037 edited that docstring (it added the Concurrency paragraph) and
left a Streamlit-prototype claim at the top of the file describing a layer the FastAPI app does not
have. `nit` on its own; it becomes part of a pattern under Theme B.

---

### Theme B — test-suite health (owner-requested)

**Measurements verified.** My counts differ slightly from the ticket's in absolutes but agree on
every ratio, so the ticket's conclusions stand.

| Layer | Source | Test | Ratio |
|---|---|---|---|
| `data/` + `analysis/` | 1,901 | 3,328 | 1.8:1 |
| `web/routes/` | 1,302 | 4,592 | 3.5:1 |
| `auth/oauth.py` (direct tests only) | 201 | 59 | 0.3:1 |
| **Whole repo** | **3,700** | **8,520** | **2.3:1** |

453 tests collected from 414 `def test_` functions (parametrisation accounts for the difference).
Suite runs in 1.6 seconds. Zero skipped, zero xfail. Nothing in the suite references `streamlit`,
`app.py`, or `pages/`.

#### Question 1 — Route-test bulk: can it be cut without losing a guard?

**Yes, and the target is not the HTML assertions. It is the harness.**

The premise in the ticket (route tests assert against rendered HTML, so template edits break tests
that were never about the template) is real but is not what drives the 3.5:1 ratio. I measured the
preamble of every web route test file, meaning everything before the first `def test_`:

| Metric | Value |
|---|---|
| Route test files measured | 14 |
| Total lines | 4,592 |
| Lines before the first test | **1,489 (32%)** |
| Files carrying their own `_make_db()` / `user_sessions` schema copy | **13** |

Thirteen files, not five. The open improvements item "Projection route test scaffolding duplicated
across three test files" was amended at review 036a to say five files; the true count is thirteen,
including `test_auth_routes.py`, `test_session_middleware.py`, `test_waiver.py`,
`test_waiver_routes.py`, `test_head_to_head_routes.py` and both `*_routes_qa.py` files. Each carries
a verbatim copy of the in-memory SQLite schema, the `TestClient` + `dependency_overrides` fixture,
and a `_insert_session` helper.

The extreme case the ticket names is instructive but points the other way.
`tests/test_waiver.py` is 807 lines over 25 tests, and its bulk is genuine scenario data
(pagination sets, lastmonth fallback fixtures, multi-position pools), not redundancy. The genuine
extreme is **`tests/test_projection_matchup_qa.py`: 159 lines carrying 2 tests, of which 124 lines
are preamble.** That is 78% scaffolding to support 35 lines of assertion.

**Recommendation: yes, a consolidation ticket is warranted, and it should be `tests/conftest.py`,
not an assertion audit.** Rough shape: a shared session-DB fixture, a shared `client` fixture, and
shared `TEAMS` / `SETTINGS` / `SCOREBOARD` constants, with each module keeping only its own
scenario data. Realistic saving is 800 to 1,100 lines with zero coverage change. **Do not pair it
with dropping HTML assertions.** Those assertions are the only thing standing between a template
edit and a silently wrong page, which is precisely the failure mode ticket 040 exists to guard
against. The brittleness complaint is better answered by scoping assertions to an element (the
`_nav_links` / `_header_left` helpers in `test_nav_shell_qa.py` are the pattern) than by removing
them.

One stale artefact found while reading: **14 call sites in `tests/test_waiver.py` still POST
`"position": "All"`**, a form field neither handler has declared since ticket 032 renamed it to
`positions`. FastAPI silently ignores unknown form fields, so the tests pass, but they read as
though they exercise a position filter and do not. Ticket 032 fixed the one test the rename broke
and did not sweep the rest; neither QA nor review caught it. Harmless, but it is dead payload that
will mislead the next reader.

#### Question 2 — Auth coverage: is it real?

**Settled without a coverage run. The two names split in opposite directions, and neither answer is
the one the name-scan implied.**

**`_try_refresh` is genuinely covered, but only on one of its two callers.** The name-scan was a
false negative: `tests/test_session_middleware.py` patches `auth.oauth.requests.post`, the transport
*inside* `_try_refresh`, rather than the function itself. Through that seam it drives six real
scenarios: valid token with no refresh, expiring token triggering exactly one refresh, Yahoo
rejecting the refresh (asserting the session row is deleted and the user is redirected), a
network-level failure, a parametrised 59s/61s expiry boundary, and two sequential healthy requests
producing zero refreshes. That is thorough coverage.

**But all six drive `require_user` only. `optional_user` has zero test references anywhere in
`tests/`.** And `optional_user` is not a thin wrapper: `web/middleware/session.py:129-152` is a
near-verbatim 24-line copy of `require_user`'s refresh-update-or-delete block, differing only in
returning `None` where the other raises. It is exercised indirectly by the home-route tests, but
only on the happy paths (valid session, no session). **The branch that deletes a user's session row
when a token refresh fails is duplicated, security-relevant, and untested on the `optional_user`
side.** This is the sharpest finding in Theme B. It is a `should-fix`, not a blocker, because I
read both copies and they are correct today.

**`validate_and_consume_state` is not undertested. It is dead code in the FastAPI stack.** Its only
importer is `app.py`, the Streamlit prototype. The FastAPI `/auth/callback` does not use it at all;
it implements state validation inline against the `oauth_states` SQLite table
(`web/routes/auth.py:49-58`), and that implementation **is** tested, by
`test_callback_invalid_state_returns_400_no_yahoo_call` and `test_callback_nonce_one_time_use`. The
OAuth CSRF check is covered. The function with zero references is simply not part of the running app.

That reframes the 0.3:1 auth ratio entirely. Tracing every function in `auth/oauth.py`:

| Function | Used by FastAPI app? |
|---|---|
| `get_auth_url`, `exchange_code`, `make_session`, `_stamp_expiry`, `_is_valid`, `_try_refresh` | Yes |
| `validate_and_consume_state`, `try_restore_session`, `get_session`, `clear_session` | **No — `app.py` / `pages/` / `utils/` only** |
| `_client_id`, `_client_secret`, `_redirect_uri` | Yes, but each falls back to `import streamlit` |

Roughly 45 of 201 lines are prototype-only, plus three credential helpers that `import streamlit` on
any path where an env var is missing. `streamlit` is not in `requirements-web.txt`, so on the
production container a missing `YAHOO_CLIENT_ID` raises `ModuleNotFoundError` instead of a usable
error. That is already tracked ("Stale Streamlit fallback in `auth/oauth.py` credential helpers",
Source: Audit 001) and has been open since audit 001. **It should be fixed before ticket 039 puts
the app on a public host**, because it converts the single most likely deploy misconfiguration into
the least legible failure.

**No `pytest-cov` run is needed to settle question 2.** Both names were resolved by reading the call
graph and the patch targets. Coverage tooling would still be worth having eventually, but it would
not have answered this question better and should not be installed on this ticket's account.

**This also qualifies one of the two findings the ticket said not to re-derive.** "No test references
`streamlit`, `app.py`, or `pages/`, so there is nothing stale to archive from the migration" is true
of the tests and false of the source they cover. The migration staleness sits in `auth/oauth.py` (a
layer `CLAUDE.md` describes as "shared and stable") and in `data/cache.py`'s docstring. Both are in
files 037 and the M1 work are actively touching.

#### Question 3 — The `*_qa.py` convention: ratify or merge?

**The tests are genuine. The convention has inverted its own meaning and should not be ratified as-is.**

On content, the answer is clear. I read all four files. `test_projection_breakdown_qa.py` covers a
mononym player name, a goalie-only roster, a multi-token `display_position` like `C,G`, and a league
with no enabled goaltending categories. `test_projection_matchup_qa.py` covers an opponent-column
highlight and a tie with no highlight. `test_overview_routes_qa.py` covers row ordering, colour-class
positioning, and two negative assertions that specific cells must *not* be coloured. These are real
edge cases around the new partitions, not restatements of the Engineer's happy paths. Every one is
permitted by `docs/DECISIONS.md` 2026-05-31, and both the 034 and 036a reviews adjudicated that
correctly.

The problem is what has happened to the name. **`tests/test_nav_shell_qa.py` is no longer
supplementary QA coverage.** Ticket 036b's *Engineer* put the primary AC coverage for the demo nav
there (19 parametrised cases), deliberately, to avoid a sixth copy of the harness. Ticket 040 then
formalises it: its Out of scope says "Keep every nav/header assertion consolidated in
`tests/test_nav_shell_qa.py` so the nav contract lives in one file." A file whose suffix means
"supplementary, written by QA on top of AC coverage" is now the canonical, Engineer-authored home of
a feature's acceptance tests, and the process is actively directing more work into it.

That is drift with a cost the ticket named correctly: discoverability. An engineer looking for the
nav contract has no reason to open a file called `_qa`.

**Recommendation: do not ratify the suffix, and do not merge the files by hand either.** Take the
naming question inside the `tests/conftest.py` consolidation ticket from question 1, since that
ticket touches all of these files anyway. The rule worth ratifying is about *what a test file
contains*, not who wrote it:

- One test module per feature surface, named for the surface (`test_nav_shell.py`,
  `test_projection_breakdown.py`), holding both AC and edge-case tests.
- Authorship stays a `git` question, which is where it belongs. `docs/DECISIONS.md` 2026-05-31
  governs *when QA may write a test*, and nothing in it requires a separate file to enforce that.

Of the four, `test_nav_shell_qa.py` (rename, it is now primary) and `test_projection_matchup_qa.py`
(159 lines for 2 tests, merge into `test_projection_matchup_route.py`) are the clear cases.
`test_projection_breakdown_qa.py` and `test_overview_routes_qa.py` are large enough to stand alone
and only need renaming. This is a Tech Lead ratification, not a Reviewer call. See suggested action 4.

---

### Findings

- **should-fix (spans 036a/036b, Theme B):** `optional_user` (`web/middleware/session.py:102-158`)
  has zero direct test coverage. Its token-refresh branch, including the `DELETE FROM user_sessions`
  on refresh failure, is a near-verbatim 24-line copy of `require_user`'s and is exercised by no test.
  `require_user`'s equivalent is covered six ways in `tests/test_session_middleware.py`. Both copies
  are correct today, so this is a guard gap in security-relevant code rather than a live defect, but
  it is the one gap in this batch that gets worse rather than better once the app is public.

- **should-fix (pre-existing, escalated by the M1 deploy sequence):** the `st.secrets` fallback in
  `auth/oauth.py:147-166` should be removed before ticket 039 ships. `streamlit` is absent from
  `requirements-web.txt`, so a missing `YAHOO_CLIENT_ID` on the production container produces
  `ModuleNotFoundError` rather than a legible configuration error. Open since audit 001; the deploy
  ticket changes its risk profile. Already tracked in `docs/improvements.md`.

- **should-fix (process, spans all six tickets):** the `~200-line` orchestrator halt heuristic
  (`.team/orchestrator.md:168`) counts test lines against a threshold that exists to bound
  *behaviour*-change risk. Ticket 037 tripped it at ~350 lines on ~108 net source lines. Narrow it to
  non-test source.

- **should-fix (test-suite structure, spans 034/036a/036b):** thirteen test files carry a verbatim
  copy of the in-memory session-DB scaffolding, totalling 1,489 lines of preamble across the 14 route
  test files (32% of those files). The existing `docs/improvements.md` entry says five files; the
  count is thirteen and should be corrected. This is the single largest and safest reduction available
  in the suite.

- **should-fix (unratified convention, spans 034/036a/036b, Theme B Q3):** the `*_qa.py` file suffix
  now labels a file that holds Engineer-authored primary AC coverage (`test_nav_shell_qa.py`), and
  ticket 040 institutionalises that. Needs a Tech Lead ruling before 040 adds more to it. Detail in
  Theme B above.

- **nit (032):** the per-position fetch loop in `web/routes/waiver.py:180-198` is
  `positions × stats`, so a cold-cache request selecting five positions and five stats issues 25 Yahoo
  calls where the pre-032 single-select issued 5. The loop is correct and the ticket prescribed it for
  a sound reason (top-25 crowding would bury D and G), the calls are still bulk rather than per-player,
  and the 24h per-position cache TTL makes steady state cheap. But the 5× cold-path multiplier landed
  in the same window the Tech Lead flagged Yahoo rate limits as an M1/M2 concern, and no ticket
  quantified it. Worth knowing, not worth changing.

- **nit (032):** fourteen call sites in `tests/test_waiver.py` still POST `"position": "All"`, a form
  field removed by that same ticket. Silently ignored by FastAPI; misleading to read.

- **nit (037):** `data/cache.py`'s module docstring still describes `@st.cache_data` and `pages/` as
  the second caching layer. Ticket 037 edited this docstring and left the stale opening.

- **nit (036b, already tracked):** `"Demo League"` is written as a literal at six demo call sites. The
  pre-existing pattern, so not a 036b finding, but a module constant would be tidier whenever those
  files are next reworked.

---

### Implicit decisions surfaced

Two, both for the Tech Lead to rule on:

1. **Test-file naming and authorship are conflated.** The `*_qa.py` suffix started as "supplementary
   edge cases added by QA on top of Engineer AC coverage" and now labels a file holding
   Engineer-authored primary AC coverage that ticket 040 will extend. Proposed entry: test modules are
   named for the **feature surface** they cover and hold both AC and edge-case tests regardless of
   author; `docs/DECISIONS.md` 2026-05-31 continues to govern *when* QA may add a test, and needs no
   filename to enforce it. Ratify before ticket 040 lands, since 040 is currently instructed to
   consolidate more of the nav contract into a `_qa` file.

2. **There is no shared test fixture module, and the repo has decided against one thirteen times by
   default.** `tests/conftest.py` does not exist, so every route test file re-declares the session DB
   schema and the `TestClient` fixture. Nobody chose this; it accreted. Proposed entry: `tests/conftest.py`
   is the canonical home for cross-module test fixtures, mirroring the 2026-05-30 "Shared route helpers:
   `web/routes/common.py` is the canonical home" decision one layer down. Worth an entry precisely because
   the same reasoning already carried once for `common.py`.

Also worth recording, though it is a housekeeping convention rather than an architectural one:
**audit files should be named for their own audit ticket.** `.team/audits/032-audit.md` covers tickets
025 to 031, but ticket 032 is the waiver multi-position filter, so "032" denotes two different things.
Audit 024 has a matching `024-audit-checkpoint.md` ticket; audit 032 has none. This audit is
`041-audit.md` and ticket 041 is the audit ticket, so the convention is self-correcting from here.
`scripts/audit_due.py` reads the `## Tickets reviewed` bullets, not the filename, so renaming
`032-audit.md` to something unambiguous (for example `032-audit-025-031.md`) is safe. Owner's call
whether it is worth the churn.

A related trap found while closing this audit, worth one line in `.team/reviewer.md`: the
`Tickets reviewed` section **must be a bullet list**. `scripts/audit_due.py:77` matches
`-\s+\**(id)`, so a table renders fine to a human but registers zero covered tickets, and the script
keeps reporting `AUDIT DUE` after a completed audit. It fails silently in the safe direction, but it
cost a round trip here. The persona's template already shows bullets; it does not say they are load-bearing.

---

### DECISIONS.md hygiene

No new gaps. All four entries added since the last audit (2026-07-23 ×3, 2026-07-25 ×1) carry
`Revisit if` clauses, and the two 2026-07-23 cache entries carry unusually good ones: the
`threading.Lock` revisit trigger is correctly tied to the single-worker decision, and 037 wrote that
coupling into `data/cache.py`'s module docstring so the next person to propose a second worker reads
it in the file the assumption lives in. That is the best decision-to-code traceability in the repo.

The eight pre-2026-04-19 entries lacking `Revisit if` clauses, flagged in audit 024 and again in audit
032, remain open. Still low priority, still not re-litigated here.

One entry is ratified but unticketed: 2026-07-25 "Nav shell: render sites that cannot resolve a user
declare the state unknown and render nav-free". See suggested action 2.

---

### Suggested actions (priority order)

1. **(PM)** Scope ticket 039 (`fly.toml`). This audit is HEALTHY and does not block it. Fold in, or
   sequence immediately before it, the `auth/oauth.py` `st.secrets` removal: on a public container a
   missing credential env var currently fails as `ModuleNotFoundError`.
2. **(PM)** Scope the error-page nav fix. `docs/DECISIONS.md` 2026-07-25 fully specifies the mechanism,
   states it has no dependency on 036b, and 036b has shipped. A ratified decision with no ticket is how
   the demo-nav gap survived two audit cycles. The `base.html` default flip described in that entry's
   "Forward commitment" paragraph is also now unblocked and can ride along or follow.
3. **(Tech Lead, then PM)** Rule on the two implicit decisions above. Item 1 (test-file naming) should be
   decided **before ticket 040 lands**, since 040 is currently instructed to consolidate more of the nav
   contract into `test_nav_shell_qa.py`. Item 2 (`tests/conftest.py`) can follow.
4. **(PM)** Scope the test consolidation ticket Theme B recommends: a `tests/conftest.py` holding the
   session-DB and `client` fixtures, adopted across the thirteen files that currently duplicate them, plus
   the file renames from action 3. Expected saving 800 to 1,100 lines with no coverage change. Explicitly
   **not** in its scope: dropping HTML assertions. Fold in the 14 stale `"position": "All"` form fields in
   `tests/test_waiver.py` and merging `test_projection_matchup_qa.py` (2 tests, 124 lines of preamble)
   into its sibling.
5. **(PM)** File a small ticket for `optional_user` test coverage: drive its refresh-success,
   refresh-failure (asserting the session row is deleted and `None` is returned), and network-error
   branches, mirroring the six `require_user` cases already in `tests/test_session_middleware.py`. Small,
   and it closes the one security-relevant gap in this batch.
6. **(Owner, process)** Amend the `~200-line` halt heuristic in `.team/orchestrator.md:168` to count
   non-test source lines only.
7. **(Owner)** Two things to carry to the next authenticated login: the 037 warm-cache walk on `/waiver`
   and `/overview`, and the accumulated visual checks from 032 (checkbox pill styling and the JS
   mutual-exclusivity toggle firing on a real click), 034 (horizontal-scroll reduction at 1280px, spacing
   between the stacked Skaters/Goalies tables, sticky-first-column behaviour, `title` tooltips on hover),
   and 036b (authenticated nav walk). None blocks anything; they have simply been accruing for three
   tickets because no environment in this workflow has a Yahoo session.
8. **(Owner, housekeeping)** Ticket 037's code is complete and approved but **uncommitted** —
   `data/cache.py` and `tests/test_cache.py` are modified in the working tree while the ticket artifacts
   sit in `tickets/done/`. Every other ticket in this batch has a commit. Worth committing so the shipped
   state matches the ticket state.
9. **(Owner, tooling)** Fix the `scripts/audit_due.py` parser trap described above, and add one sentence
   to `.team/reviewer.md` saying the `Tickets reviewed` bullets are load-bearing. Filed as a `Type: bug`
   entry in `docs/improvements.md`. Lowest priority of the nine: it fails in the safe direction (audits
   over-report as due, never under-report), so it costs a round trip rather than correctness.

---

### Verdict: HEALTHY

Six tickets, zero blockers, zero architectural violations, zero contradicted decisions. No framework
import in `data/`, `analysis/` or `auth/`; no per-entity Yahoo loop; no raw `stat['value']`; no missing
demo counterpart; no secrets or PII in logs or template context. Every ticket's diff stayed inside its
`Touches` list, with the only excursions being test files (never listed in `Touches` in this repo) and
`docs/improvements.md` close-outs the personas explicitly sanction. The full suite is green at 453
passed.

Two things raise this above a routine pass. The audit-032 process fix worked: not one resolved
improvements item was left under `## Open` this cycle, breaking a pattern that had recurred across two
audits. And the batch's hardest tickets got the batch's strongest evidence, which is the right
correlation. Ticket 034's AC5 was proved by an independent 535-cell pre/post reconstruction on a second
server, and ticket 037's non-vacuity was proved by de-hardening the module and watching 14 of 16 new
tests fail with real defect signatures. Neither was asked for.

The verdict is HEALTHY rather than NEEDS ATTENTION because every finding is a `should-fix` or `nit`,
none blocks merging, none contradicts an active decision, and the one genuinely security-relevant item
(`optional_user`'s untested refresh branch) is a missing guard on code I read and found correct, not a
defect. Ticket 039 is unblocked.

The thread worth the owner's attention is **migration debt in the layers `CLAUDE.md` calls stable**.
`auth/oauth.py` still carries four Streamlit-only functions and three credential helpers that
`import streamlit`, and `data/cache.py`'s docstring still describes a `@st.cache_data` layer the FastAPI
app does not have. The test suite is clean of prototype references, which is what the pre-audit scan
measured and why this went unnoticed. The source under test is not. That debt has been harmless while
the app ran only on a laptop; ticket 039 changes that.
