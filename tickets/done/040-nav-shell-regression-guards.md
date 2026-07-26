# 040 — Nav shell test set: close the 5 uncovered branches, drop the redundant test

## Status
done

## Type
refactor

## Process
full

(Not `light`: ~50 lines expected, above the ~20-line threshold. No architectural surface
in `Touches` and the patterns are all existing, but the size rules light out.)

## Milestone
none

(Test-only regression hardening — no user-visible behaviour changes. It guards the m1
authenticated nav and the m2 demo nav equally, so tagging it to either milestone would
overstate it.)

## Touches
- tests/test_nav_shell_qa.py (renamed to `tests/test_nav_shell.py` — see AC1)
- tests/test_nav_shell.py
- docs/improvements.md
- docs/archive/improvements-closed.md

## Why
Ticket 036b migrated 12 full-page render branches to `shell_context()`, and the Reviewer
confirmed all 12 are correct today. But the test set that is supposed to keep them correct
covers only 7, and it spends three parametrised cases on a test that asserts nothing the
test above it doesn't already assert. The gap matters because the failure mode is silent:
if a future edit drops the `**shell_context(...)` spread from a branch, the page still
returns 200 and still renders, it just shows the wrong nav — a demo visitor gets
authenticated links that bounce them to `/auth/login`, which is the exact defect 036a and
036b existed to fix. Five uncovered branches, all in `web/routes/overview.py`, would let
that regression back in unnoticed. This ticket resolves two `docs/improvements.md` items:
"`test_authenticated_nav_links_return_200` is parametrised over an unused argument and adds
no coverage" and "Nav/header assertions cover 7 of the 12 `shell_context()` branches in the
feature routes".

## Acceptance criteria
- [ ] `tests/test_nav_shell_qa.py` no longer exists; its content lives at `tests/test_nav_shell.py`, moved with `git mv` so history is preserved, and no file in `tests/` carries a `_qa` suffix that this ticket introduced. Do this **first**, before writing any new test.
- [ ] `test_authenticated_nav_links_return_200` no longer exists in `tests/test_nav_shell.py`, and no test in that file is parametrised over an argument its body never reads.
- [ ] Each of the five branches in the table below has a test asserting both the exact nav link set (via `_nav_links`, equal to `AUTHENTICATED_NAV` or `DEMO_NAV`) and the header label (via `_header_left`), so all 12 migrated branches are covered.
- [ ] For each of the five new branch tests, deleting the `**shell_context(...)` spread from that branch in `web/routes/overview.py` makes that test fail — verified by mutation probe and reverted, with the observed failing test IDs reported in the handoff.
- [ ] `.venv/bin/python -m pytest tests/` is green, with a net test-count change reported in the handoff.
- [ ] Both `docs/improvements.md` entries named in Why are moved to `docs/archive/improvements-closed.md` with a resolution note citing ticket 040.

## Out of scope
- Any change to `web/routes/overview.py`, `waiver.py`, `projection.py`, `web/templates/base.html`, or `web/routes/common.py`. All 12 branches are correct; this ticket adds guards, it does not fix behaviour. If a branch turns out to be wrong, stop and escalate rather than fixing it here.
- The third improvements item from the same review, "Post-036b stale comments about pages 'not yet' passing `shell_context()`". Its two halves belong elsewhere: the `tests/test_overview_routes.py` comment goes to whichever ticket next touches that file (not this one), and the `base.html` comment is owned by the DECISIONS 2026-07-25 default-flip follow-up. Leave both alone.
- Consolidating or de-duplicating the `_make_db` / `ctx` fixture scaffolding that is copied across the route test files. It is a real open improvements item, but it touches every route test file and is its own ticket.
- Fragment-handler tests. Fragments do not extend `base.html` and must not gain shell context.
- Adding nav assertions to `tests/test_head_to_head_routes.py` or the other route test files. Keep every nav/header assertion consolidated in `tests/test_nav_shell.py` so the nav contract lives in one file.
- **The other three `*_qa.py` files.** `docs/DECISIONS.md` 2026-07-26 "Tests: one module per feature surface" retires the suffix repo-wide, but assigns only `test_nav_shell_qa.py` to this ticket. `test_projection_matchup_qa.py` and `test_overview_routes_qa.py` merge into their siblings, and `test_projection_breakdown_qa.py` renames, all in the consolidation ticket **after** `tests/conftest.py` exists. Do not touch them here.
- **Creating `tests/conftest.py` or moving any fixture into one.** Ratified by `docs/DECISIONS.md` 2026-07-26 "Tests: `tests/conftest.py` is the canonical home…", but it is the consolidation ticket's job across all thirteen files. Your renamed module keeps its own harness for now. See the Notes below.

## Notes for the Engineer

**The five uncovered branches — all in `web/routes/overview.py`:**

| # | Route | Branch | Line | Expected nav | Expected header label |
|---|---|---|---|---|---|
| 1 | `/overview/head-to-head` | populated (≥2 teams) | 174 | `AUTHENTICATED_NAV` | `Alpha League` |
| 2 | `/overview` | `df is None or df.empty` | 56 | `AUTHENTICATED_NAV` | `Alpha League` |
| 3 | `/overview/head-to-head` | `len(teams) < 2` | 146 | `AUTHENTICATED_NAV` | `Alpha League` |
| 4 | `/demo/overview` | `df is None or df.empty` | 241 | `DEMO_NAV` | `Demo League` |
| 5 | `/demo/overview/head-to-head` | `len(teams) < 2` | 311 | `DEMO_NAV` | `Demo League` |

The other seven (populated `/overview`, `/waiver`, `/projection`, and all four demo pages)
are already covered by `test_authenticated_feature_pages_render_authenticated_nav`,
`test_demo_pages_render_demo_nav`, and `test_demo_pages_header_keeps_demo_league_label`.

**Patch targets — the demo handlers are the trap.** `docs/LEARNINGS.md` "Tests must patch
the importing module's namespace" gives the general rule, and it holds for the
authenticated branches: patch `web.routes.overview.get_matchups`. It does **not** hold for
the demo handlers. `demo_overview` and `demo_head_to_head` lazily `from data import demo as
demo_module` *inside the function body*, then call `demo_module.get_matchups()`, so the
binding happens at call time on the `data.demo` module object. The patch target is
`data.demo.get_matchups`. Patching `web.routes.overview.get_matchups` for a demo branch
silently does nothing and the test passes against the populated branch instead — a green
test that guards nothing. This is documented in `tests/test_demo_overview_routes.py` lines
11-12 and now in `docs/LEARNINGS.md`.

**Existing patterns to copy for forcing each branch:**
- Branches 2 and 3: `tests/test_overview_routes.py::test_overview_empty_matchups_renders_shell` and `tests/test_head_to_head_routes.py::test_head_to_head_empty_matchups_renders_shell` (line 324) both force the authenticated empty state with `patch("web.routes.overview.get_matchups", return_value=None)`.
- Branches 4 and 5: `tests/test_demo_overview_routes.py` (line 58 onward) for the `patch("data.demo.get_matchups", ...)` shape.
- Branch 1: no patching subtlety — the existing `_authenticated_feature_get` df already has two teams (`Alpha`, `Beta`), so `len(teams) < 2` is false and it lands on the populated branch.

**`_authenticated_feature_get` needs extending for branch 1.** Its `module` lookup
(line 263, in the renamed `tests/test_nav_shell.py`) is a dict keyed on `/overview`, `/waiver`,
`/projection` and will `KeyError` on `/overview/head-to-head`. Map that path to the
`overview` module rather than adding a second helper.

**Removing `test_authenticated_nav_links_return_200`** (lines 341-347): plain deletion is
the expected outcome. `test_authenticated_feature_pages_render_authenticated_nav` directly
above it already parametrises the same three paths through the same helper and already
asserts `status_code == 200` alongside the nav set and label, so nothing is lost. Do not
replace it with a de-parametrised variant unless you can state what it asserts that the
neighbouring test does not.

**Use the existing helpers, do not add new ones.** `_nav_links` scopes to the `<nav>`
element and `_header_left` scopes to the part of `<header>` before `<nav>`. The header
scoping is what makes the label assertion discriminate — a whole-body `"Alpha League" in
response.text` still passes when the header label is blank, because the content area
repeats the name. This is the same trap ticket 036b was written around.

**Decisions this must conform to:** `docs/DECISIONS.md` 2026-07-03 "Nav shell: conditional
on auth/demo state via shared shell-context; no second auth-derivation path" (the mechanism
under test) and 2026-04-19 for the Overview → Waiver → Projection link ordering baked into
`AUTHENTICATED_NAV` / `DEMO_NAV`.

**DoD:** this ticket resolves the two `docs/improvements.md` items named in Why. Move both
entries to `docs/archive/improvements-closed.md` with a resolution note citing ticket 040.
Leave the third (stale-comments) entry open and untouched.

**Open `docs/improvements.md` items on files in `Touches`** (checked 2026-07-26):
- *Scoped-from, in scope:* the two items named in Why —
  "`test_authenticated_nav_links_return_200` is parametrised over an unused argument and adds
  no coverage" and "Nav/header assertions cover 7 of the 12 `shell_context()` branches in the
  feature routes". Close both per the DoD.
- *Do NOT sweep, despite it naming a file in your `Touches`:* **"Projection route test
  scaffolding duplicated across three test files"** (`Type: quality`). Its audit-041 update
  names `tests/test_nav_shell_qa.py` as one of **thirteen** files carrying a duplicated
  `_make_db()` / `user_sessions` scaffold, and `docs/DECISIONS.md` 2026-07-26 now ratifies a
  shared `tests/conftest.py` as the fix across all thirteen. Your input #6 obliges you to
  sweep `Type: quality` items on files you are modifying, and read literally that would pull
  a 13-file, 800–1,100-line refactor into this ticket. **That is a separate ticket the PM is
  scoping from audit 041 action 4.** Twelve of the thirteen files are not in your `Touches`,
  so attempting it would also escape scope and halt the run. Leave the item open, change no
  scaffolding, and do not extract a `conftest.py`. If you find the duplication genuinely
  obstructs writing the five branch tests, stop and say so rather than refactoring around it.

**The rename (AC1) — do it first, and keep it a pure move.** `docs/DECISIONS.md` 2026-07-26
"Tests: one module per feature surface, named for the surface, never for the author" retires
the `*_qa.py` suffix and assigns this one file to this ticket, because the ticket is opening
it anyway and the ruling notes the misnomer would otherwise become load-bearing. Use
`git mv tests/test_nav_shell_qa.py tests/test_nav_shell.py` so history follows the file, run
the suite to confirm it is still collected and green, and only then start on the deletions
and the five branch tests. Do not combine the move with content edits in one step — a pure
rename plus a separate content diff is what lets the Reviewer see what actually changed.
Update the module docstring if it describes the file as QA-supplementary; the module is the
canonical home of the nav contract, which is what the ruling establishes.

## Verification
- `.venv/bin/python -m pytest tests/` green; report the observed pass count and the net change in test count.
- Mutation probe, the core of this ticket: for each of the five branches, delete that branch's `**shell_context(...)` spread from `web/routes/overview.py`, confirm the corresponding new test fails, then revert. Report the failing test ID observed for each. A branch whose test still passes with the spread removed is not guarded and the ticket is not done.
- Confirm `git diff --stat` shows no change to any file under `web/` once the probes are reverted.
- No manual browser walk needed — this ticket adds no route behaviour and changes no template.

## Dependencies
- None. Ticket 036b is `done` (`tickets/done/036b-demo-nav-adoption.md`); this hardens its test set.
