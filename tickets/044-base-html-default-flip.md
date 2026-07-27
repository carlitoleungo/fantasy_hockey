# 044 — Flip `base.html`'s absent-flag default from authenticated nav to nav-free

## Status
ready

## Type
refactor

## Milestone
none

## Touches
- web/templates/base.html
- tests/test_nav_shell.py
- tests/test_overview_routes.py
- docs/LEARNINGS.md

## Why
`base.html` currently treats "no shell flags in context" as "this visitor is authenticated"
— a staged-migration affordance from 036a that has outlived its purpose now that every route
module passes `shell_context()`. The cost is that a page which forgets the spread lies to the
visitor instead of degrading visibly, and QA 040 measured how invisible that is: it ablated
the header-label assertion from the three new authenticated branch tests, deleted each
branch's `**shell_context(...)` spread in turn, and the module returned `32 passed` every
time. A dropped spread on an authenticated branch is caught by nothing, because the fallback
nav is exactly the nav the test expects. Flipping the default makes the same mistake fail
loudly, the way it already does on demo branches.

## Acceptance criteria
- [ ] Rendering `base.html` with an empty context produces a header containing the `<a href="/">Fantasy Hockey</a>` brand link and a `<nav>` with zero `<a>` elements.
- [ ] Rendering with `{"demo_mode": False}` and no `is_authenticated` key also produces the nav-free header (it produced the authenticated nav before this ticket).
- [ ] Every explicit branch is unchanged: `is_authenticated=True` → Overview / Waiver / Projection / Logout in that order; `{is_authenticated: False, demo_mode: False}` → "Log in with Yahoo" only; `{is_authenticated: False, demo_mode: True}` → the demo nav; `auth_state_unknown=True` → nav-free (ticket 042's branch still wins, and still comes first).
- [ ] Mutation probe recorded in the done note: deleting the `**shell_context(...)` spread from each authenticated full-page branch in `web/routes/overview.py`, one at a time, now fails at least one test in `tests/test_nav_shell.py` in every case. Restore the file afterwards and confirm the suite is green.
- [ ] Both stale comments are retired: `base.html` lines 21-22 ("pages that do not yet pass `shell_context()` render exactly as before") and the `tests/test_overview_routes.py` comment claiming `/overview` has not adopted `shell_context` yet.

## Out of scope
- **Changing `shell_context()` or any route.** No route module is in `Touches`. Every page
  already passes the flags; this ticket only changes what happens when one doesn't.
- **The `auth_state_unknown` branch from ticket 042.** Keep it first and keep it explicit.
  Do not collapse it into the new default on the grounds that both render nav-free — the key
  is named for its cause, and DECISIONS 2026-07-25 is deliberate about that.
- Any nav styling, link ordering, or copy change.
- `tests/conftest.py` consolidation, even though both test files in `Touches` are named in
  that `docs/improvements.md` item — audit 041 reserves it for its own ticket.
- Renaming `tests/test_overview_routes.py` or reorganising its cases beyond the one stale
  comment and the misleading test name it sits on.

## Notes for the Engineer
- **Architectural surface (template structure) — the Tech Lead consult is already done.**
  Implement the **"Forward commitment (sequenced after 036b, not part of this fix)"**
  paragraph of `docs/DECISIONS.md` **"Nav shell: render sites that cannot resolve a user
  declare the state unknown and render nav-free; exception handlers never derive auth"
  (2026-07-25)**, and cite that entry by date in your done note. The paragraph states the
  flip is blocked on 036b; **036b is done** (shipped 2026-07-25), so it is unblocked. Its
  words: "absent flags render the nav-free header, so a future page that forgets
  `shell_context()` degrades visibly instead of lying."
- The condition to change is `web/templates/base.html:29`,
  `{% elif is_authenticated is undefined or is_authenticated %}`. The target behaviour table:

  | Context | Header nav |
  |---|---|
  | `auth_state_unknown` truthy | brand only, no links (042) |
  | no `is_authenticated` key at all | brand only, no links (**new**) |
  | `demo_mode` truthy | demo nav + "Log in with Yahoo" |
  | `is_authenticated` true | Overview / Waiver / Projection / Logout |
  | `is_authenticated` false | "Log in with Yahoo" only |

  Note the "undefined" and "false" rows must stay distinguishable — an explicit
  `is_authenticated=False` still gets the login link, only the absent case goes nav-free. A
  bare `{% elif is_authenticated %}` collapses them, so you need a defined-check somewhere.
- `tests/test_nav_shell.py:154-170` is the parametrised branch matrix. Two of its five cases
  assert the old default (`({}, AUTHENTICATED_NAV)` and
  `({"demo_mode": False}, AUTHENTICATED_NAV)`) — update those expectations and the "AC3
  safety constraint" comment above them, which describes the constraint this ticket removes.
  The module docstring's fourth bullet (lines 17-20) says the same thing; fix it too.
- **Mutation-probe trap — read this before running AC4.** Lines 174, 241 and 311 of
  `web/routes/overview.py` are each exactly 77 bytes. Deleting one and then another produces
  two source files of identical size, and when the mtimes land in the same second CPython
  reuses the *previous* probe's `.pyc` and reports the previous probe's result.
  `pytest -p no:cacheprovider` does not prevent it (that flag governs pytest's cache, not
  CPython's). **Purge `__pycache__` between every mutation.** QA 040 hit this and initially
  certified the wrong test as a branch's guard; the evidence is in `tickets/done/040-qa.md`.
- **Append that trap to `docs/LEARNINGS.md`** as a short entry next to the existing
  "Tests must patch the importing module's namespace" gotcha — size+mtime collision, the
  purge step, and why the `pytest` flag doesn't help. This is `Touches`-authorised and closes
  a tracked item; keep it to a few lines.
- **Open `docs/improvements.md` items on files in `Touches`:**
  - "`base.html`'s authenticated-nav default is now unblocked, and 040 measured what it
    costs" (`Type: quality`, `web/templates/base.html` lines 21-33) — **this is the item this
    ticket resolves.** Move it to `docs/archive/improvements-closed.md` with a
    `**Resolved:**` note on handoff.
  - "Post-036b stale comments about pages 'not yet' passing `shell_context()`"
    (`Type: quality`, `web/templates/base.html` lines 21-22 and
    `tests/test_overview_routes.py`) — **also resolved here** (AC5), both halves. The entry
    explicitly routes the `base.html` comment to this ticket. Move it to the closed archive
    as well. Note the overview test's assertions stay correct and valuable; only the comment
    and the `_by_default` name are wrong — since 036b, `/overview` does pass
    `shell_context()`, so the test proves the explicit `is_authenticated=True` branch.
  - "Mutation-probe `.pyc` staleness trap is recorded only in a QA report" (`Type: quality`,
    `docs/LEARNINGS.md`) — **also resolved here**, per the LEARNINGS bullet above. Move it to
    the closed archive.
  - "Projection route test scaffolding duplicated across three test files" (`Type: quality`,
    names both `tests/test_nav_shell.py` and `tests/test_overview_routes.py`) — **out of
    scope**; audit 041 recommends it as its own ticket.

## Verification
- Render checks against the template directly (no route needed) for all five rows of the
  table above, asserting on `<nav>` anchors rather than the whole body.
- In the running app, walk every real page and confirm nothing changed: logged-out `/`,
  authenticated `/`, `/overview`, `/waiver`, `/projection`, `/demo/overview`,
  `/demo/waiver`, `/demo/projection`, and an error page (042's nav-free header). Every one of
  these passes flags explicitly, so a visible change anywhere means a branch was missed.
- Run the AC4 mutation probe: for each authenticated full-page branch in
  `web/routes/overview.py`, delete its `**shell_context(...)` spread, purge `__pycache__`,
  run `.venv/bin/python -m pytest tests/test_nav_shell.py`, record which test failed, restore.
  Paste the per-branch results into the done note.
- `.venv/bin/python -m pytest tests/` green with the file restored.

## Dependencies
- **Ticket 042 must complete first.** Both edit the same `base.html` branch block, so they
  cannot run in parallel; AC3 here asserts 042's `auth_state_unknown` branch, which does not
  exist until 042 lands. Scoped as two tickets rather than one because they answer to two
  different paragraphs of the 2026-07-25 decision, carry unrelated acceptance criteria (a
  user-visible M1 defect vs. a fail-safe default with a mutation-probe proof), and together
  would span six files — well past one focused session. DECISIONS 2026-07-25 explicitly
  notes the two do not collide in either landing order.
- 036b — DONE (shipped 2026-07-25). This was the flip's only blocker.
- **Let ticket 039 (`fly.toml`, the M1 gate) finish before this one.** As of 2026-07-26 it is
  already implemented and sits at `Status: qa`, so this means completing its QA and review. No
  file overlap; the only interaction is the audit counter. `scripts/audit_due.py` reads
  2.0 / 5.0 today; 042 (1.0), 043 (0.5, light) and this ticket (1.0) bring it to 4.5 / 5.0, so
  039 stays runnable — but it is architectural, so orchestrator pre-flight blocks it the moment
  the counter reaches 5.0 (relevant if it needs a fix round or a re-run). Clear 039 first.
