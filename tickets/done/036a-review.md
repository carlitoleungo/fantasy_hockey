## Code Review — 036a

**Reviewer date:** 2026-07-25
**QA verdict on entry:** APPROVED (`tickets/036a-qa.md`)

**Files reviewed:**
- `web/routes/common.py` — new `shell_context()`; 18 lines, no logic beyond deriving
  `is_authenticated` from `current_user is not None`. Docstring cites DECISIONS 2026-07-03.
- `web/templates/base.html` — nav split into demo / authenticated / logged-out branches with
  the authenticated nav as the fallback when both flags are absent.
- `web/routes/home.py` — `shell_context()` spread into both `TemplateResponse` contexts on
  `GET /`; no other change to the handler.
- `tests/test_home_routes.py` — TC17, TC18, TC19 added.
- `tests/test_overview_routes.py` — TC9 added (default-path regression guard).
- `tests/test_nav_shell_qa.py` — QA's supplementary file (14 tests).
- `docs/improvements.md` → `docs/archive/improvements-closed.md` — DoD item move, verified.

Verified independently: `.venv/bin/python -m pytest tests/ -q` → **421 passed** in 1.36s.

### Scope: CLEAN

The diff stays inside `Touches` (`web/routes/common.py`, `web/templates/base.html`,
`web/routes/home.py`) plus the test files AC4 requires and the improvements close-out the DoD
mandates. Nothing in `web/templates.py`, no `context_processors`, no change to
`require_user`/`optional_user` or route registration, no restyling, no "Try the demo" CTA —
all four `Out of scope` boundaries hold. The Engineer's decision to leave the "Add demo mode
entry point on home page" improvements item open, and to flag rather than silently apply the
TC14 item whose prescribed fix is wrong, are both correct calls.

**Ruling 1 — the dormant `demo_mode` branch in `base.html` is in scope.** The ticket's own
Notes instruct that "`base.html` must branch on `is_authenticated` / `demo_mode`", and 036b
scopes `base.html` out with an explicit escalate-don't-edit clause. Implementing the branch
that the instruction names, in the only ticket permitted to touch the file, is the ticket
being completed rather than 036b being pre-empted. The persona's "no shims for code paths
without callers" rule targets speculative abstraction; this is a specified branch with a
named consumer landing next ticket. Two things make it safe rather than dead code: its link
targets (`/demo/overview`, `/demo/waiver`, `/demo/projection`) are routes that already exist
and QA confirmed return 200, and the branch is regression-covered by
`tests/test_nav_shell_qa.py`. Its rendered output also matches 036b's AC1 and AC2 (three demo
links, no Logout, a login affordance), so 036b should need no `base.html` edit. Not scope
creep; no action.

### Architecture: CLEAN

- No framework import added to `data/`, `analysis/`, or `auth/`. The only new import is
  `web/routes/common.py` importing `CurrentUser` from `web/middleware/session.py`, which is
  route-layer to middleware-layer and introduces no cycle (`session.py` imports nothing from
  `web/routes/`).
- No Yahoo API calls added, so no per-entity-loop question. No `data/` function added, so no
  `data/demo.py` counterpart owed. No `stat['value']`, no `_as_list()` surface touched.
- DECISIONS conformance verified against each cited entry:
  - **2026-07-03 (Option C)** — the helper consumes the user the route's dependency already
    resolved; there is no second cookie or DB read anywhere in the diff. `web/templates.py`
    is untouched, so the rejected Option B stayed rejected. The mandated default is
    implemented as `{% elif is_authenticated is undefined or is_authenticated %}`, which
    correctly yields the authenticated nav for an empty context and for
    `{"demo_mode": False}` alone.
  - **2026-04-19 (nav shell)** — Overview → Waiver → Projection ordering preserved in both
    link sets; the league-label + logout shape is unchanged.
  - **2026-05-30 (shared route helpers)** — `shell_context()` is in `common.py`, the
    canonical home, and is public-named rather than underscore-prefixed, which is the right
    read of that entry's own complaint about `_get_league_key`.
  - **2026-05-30 (`optional_user`)** — unchanged; the helper consumes its output.
- No implicit-decision drift: no new directory, no new template-naming pattern, no new
  session handling. The mechanism was pre-ratified by the Tech Lead, so no new entry is owed.

**Security:** no tokens, session IDs, or PII enter the template context — `shell_context()`
returns a bool, a bool, and a league name already rendered in the header. No new SQL, no new
dependency, no cookie-attribute surface touched.

**Beginner-friendliness:** the helper is three dict keys and one `is not None`; the template
branch is readable top to bottom. No inversion of control, no implicit global. Good.

### Verification adequacy

QA's evidence exceeds what the ACs require. The two checks that matter most were done
properly: the AC3 regression was proved by diffing the `<nav>` markup of an empty-context
render at `HEAD` against the working tree (byte-identical anchors, text, and classes), and
the "no second auth-derivation path" constraint was checked by grep across `web/`, not
assumed. Both AC2 residuals QA declined to close (live-browser visual, end-to-end OAuth round
trip) are genuinely outside this ticket's surface, and their reason for not exercising the
stale `app.db` rows — that `optional_user` deletes a row whose refresh fails — is correct as
read from `web/middleware/session.py`. Accepting AC2 on mocked-Yahoo evidence is the right
call and matches CLAUDE.md's testing strategy.

**QA's `tests/test_nav_shell_qa.py` is permitted, not a policy breach.** DECISIONS 2026-05-31
Option B allows supplementary tests "on top of existing AC coverage" and forbids only QA
supplying the primary AC suite. The Engineer shipped discriminating automated coverage for
all four ACs before QA started (TC17/TC18/TC19 + overview TC9), QA verified that explicitly
as its Step 3 check, and the file adds branch-matrix and scoping depth rather than filling a
hole. The `*_qa.py` filename follows the existing `test_projection_matchup_qa.py` /
`test_projection_breakdown_qa.py` precedent, so it is not new-convention drift.

### Issues

No blockers.

- **nit — `tests/test_home_routes.py:451`, TC18's `assert "Alpha League" in body` is
  redundant, and its comment claims more than the line delivers.** (Ruling 2.) Acceptable
  as-is; not a returnable defect. QA's reasoning is sound on both halves: the assertion does
  not discriminate (the content-area league list carries the same string, proved by mutation
  probe), and the AC2 label claim is nonetheless guarded twice elsewhere — pre-existing TC9
  scopes the match to `<header>…</header>` and fails under the same mutation, and QA's
  `test_authenticated_home_nav_and_league_label` now asserts the header-scoped label
  alongside the nav order. So AC2 has discriminating coverage and DECISIONS 2026-05-31 is
  satisfied; returning the ticket for it would be blocking a correct implementation over a
  test line that is weak rather than wrong. The sharper problem is the comment above it
  ("selected_league_name is now threaded via shell_context on this branch"), which advertises
  coverage the assertion does not provide and could mislead someone into deleting TC9 as a
  duplicate. Logged to `docs/improvements.md` for cleanup when the file is next touched;
  fix is to drop the line and the comment, since TC18's job is nav ordering.
- **nit — `tests/test_nav_shell_qa.py:232` is a deliberate tripwire that 036b must delete.**
  `test_demo_pages_still_render_default_authenticated_nav` asserts the pre-036b demo nav, so
  it will fail the moment 036b lands, by design. That is defensible (it forces the flip to be
  explicit) but only if 036b's engineer expects it. Flagging here so it reads as an intended
  update rather than a regression; no tracker entry, since the failing suite is
  self-announcing.
- **nit — heads-up for 036b: `shell_context()` can silently clobber `selected_league_name`.**
  Fourteen existing context dicts in `overview.py`, `waiver.py`, and `projection.py` pass
  `selected_league_name` explicitly (the demo handlers use the literal `"Demo League"`). Since
  the helper always returns that key, spreading it *after* an explicit key without passing
  `league_name=` silently replaces the label with `None`. `home.py` gets this right. 036b
  should replace each explicit key rather than spread alongside it — e.g.
  `shell_context(None, demo=True, league_name="Demo League")`. Worth stating in 036b's notes;
  not a defect in 036a.

**Ruling 3 — `web/templates/error.html` warrants a tracker entry now, and a PM-scoped sweep
later, not a ticket I file.** QA was right to raise it and right not to file it blind. The
behaviour is real: `error.html` extends `base.html` and passes no shell context, so a
logged-out or demo visitor who hits a 500/502 sees Overview / Waiver / Projection / Logout,
every one of which bounces them to `/auth/login`. It is pre-existing, and 036a preserves it
exactly by the `base.html` default, which is AC3 working as intended — so it is not a
regression and not a blocker. But it is not a drive-by fix either, and that is the part worth
recording: both render sites are FastAPI exception handlers (`web/main.py:48-65`) with no
resolved `CurrentUser` in scope, so `shell_context()` cannot be called there at all, and
passing `None` would hand authenticated users the logged-out nav — the mirror-image bug. That
is precisely the situation named in the `Revisit if` clause of DECISIONS 2026-07-03 ("a page
family that needs nav state but has no user dependency in scope"), so the fix needs a Tech
Lead ruling on the mechanism before an Engineer picks it up. Filed to `docs/improvements.md`
with that framing; the PM may promote it to a sweep of the remaining `base.html` consumers
once 036b lands. Not a condition on this ticket.

### Verdict: APPROVED

Ticket `## Status` set to `done`. No changes requested; all three findings are nits and two
of them are forward-looking notes for 036b.

**New `docs/improvements.md` entries written:**
- "Error pages show the authenticated nav to logged-out visitors" (Type: quality, Source:
  Code review 036a, raised by QA 036a) — includes the Tech Lead trigger above.
- "TC18's league-label assertion in `test_home_routes.py` does not discriminate" (Type:
  quality, Source: Code review 036a).
- Amended the existing "Projection route test scaffolding duplicated across three test files"
  entry: `tests/test_nav_shell_qa.py` adds another verbatim copy of the in-memory
  session-DB scaffolding, so the `tests/conftest.py` fix now covers five files, not three.

**Also noted for the owner (no entry filed):** QA is right that AC4 and the ticket template's
Verification section name `python3 -m pytest tests/` literally, which cannot succeed on this
machine — the venv interpreter is required. That is ticket boilerplate affecting 036b and
earlier tickets equally; the PM should amend the template wording to `python -m pytest
tests/`, not this ticket.
