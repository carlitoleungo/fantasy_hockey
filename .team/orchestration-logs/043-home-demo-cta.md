## Orchestration log — 043-home-demo-cta

**Run started:** 2026-09-15 (session start)
**Run ended:** 2026-09-15
**Outcome:** completed

### Pre-flight
- Status check: pass (`ready`)
- Type check: pass (`feature`, not `audit`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- `Touches` non-empty: pass (`web/templates/home.html`, `tests/test_home_routes.py`)
- Audit check: **AUDIT DUE** — `.venv/bin/python scripts/audit_due.py` reports 5 / 5
  (038, 039, 040, 042, 045 completed since the last audit at ticket 37). Surfaced to the
  owner as a judgment call: `web/templates/home.html` sits inside the "Template structure
  (HTMX shell + fragment split)" surface on WORKFLOW.md's escalation list, but this change
  adds one anchor inside an existing content block and does not touch the shell or the
  fragment split. **Owner ruled it non-architectural and authorised proceeding.**
  The overdue audit remains outstanding and must be scheduled before the next
  architectural ticket.
- Architectural-surface coverage: N/A per the owner's ruling above.

### Model selection
- Engineer: `sonnet` — heuristic branch `Process: light`. No `## Model` section in the ticket.
- Test Engineer: `sonnet` — same branch.
- Reviewer: not spawned (`Process: light`; combined QA+review covers the blocker checklist).

### Subagents spawned (in order)
1. Engineer (round 1)
   - Inputs: `.team/engineer.md`, `tickets/043-home-demo-cta.md`, DECISIONS 2026-04-19
     template-structure entry, LEARNINGS entries on test patch targets and template/nav gotchas
   - Output: `tickets/043-done.md`
   - Summary: Added one secondary "Try the demo" link (`href="/demo/overview"`) after the
     existing login button, inside the `{% if leagues is none %}` branch only. Added two tests
     (`test_home_unauthenticated_shows_demo_cta`, `test_home_authenticated_no_demo_cta`) plus
     the TC14 and TC18 sweeps. Moved three resolved quality items to
     `docs/archive/improvements-closed.md`. `web/routes/home.py` untouched.
     Suite: 471 passed. Flagged one deviation (see below).

2. Test Engineer (round 1, combined QA + review — `Process: light`)
   - Output: `tickets/043-qa-review.md` (now `tickets/done/043-qa-review.md`)
   - Verdict: **APPROVED**
   - Summary: Ran `.venv/bin/python -m pytest tests/` independently → 471 passed. Verified
     AC1/AC3/AC4 by independent live curl against `uvicorn web.main:app`, not by trusting the
     handoff. AC5 by own pytest run. AC2 (visual secondary) confirmed at the Tailwind-class
     level and flagged as owner-must-verify for pixel-level judgment. Zero review blockers:
     no framework imports in `data/`/`analysis/`/`auth/`, `web/routes/home.py` confirmed
     untouched via `git diff --stat`, diff scoped to `Touches` plus the explicitly instructed
     docs moves. Set Status to `done` and moved all artifacts into `tickets/done/`.

### Engineer deviation and its ruling
The ticket's Notes for the Engineer literally instruct replacing TC14's assertion with
`assert "Your Leagues" not in body`. That instruction is wrong: `web/templates/home.html:3`
has an unconditional `{% block title %}Your Leagues{% endblock %}` outside the
`{% if leagues is none %}` guard, so the substring matches on every branch and the assertion
always fails. The Engineer kept the sweep's intent (dropping the always-true `"<h1" in body`
guard) but scoped the check to `body.split("<body>", 1)[1]`, relying on `base.html:12`'s bare
`<body>` tag. The Test Engineer verified both template facts directly and ruled the deviation
correct and sufficiently surgical. No further correction needed.

### Files changed
- `web/templates/home.html` (+1 -0)
- `tests/test_home_routes.py` (+41 -4)
- `docs/improvements.md` (-27)
- `docs/archive/improvements-closed.md` (+27)
- `tickets/done/043-home-demo-cta.md` (+1 -1, Status line; moved from `tickets/`)
- New: `tickets/done/043-done.md`, `tickets/done/043-qa-review.md`

Cumulative diff: 70 insertions, 32 deletions — well under the ~200-line halt heuristic.
Orchestrator independently verified via `git status --short` and `git diff --stat` that
nothing outside `Touches` (plus the ticket-instructed docs moves) was changed.

### Halt conditions tripped
- None during the loop. One pre-flight halt condition (AUDIT DUE) was surfaced to the owner
  before any spawn and resolved by an explicit owner ruling.

### Notes for the owner
- **The audit is overdue at 5 / 5 and is still outstanding.** Schedule `/reviewer` in audit
  mode before the next architectural-surface ticket. 044 (`base.html`, the template-structure
  surface proper) is the obvious next candidate and is a stronger audit-gate case than 043 was.
- **AC2 needs your eye.** The Test Engineer confirmed the Tailwind classes
  (`bg-purple-600 text-white` filled vs. `border border-gray-300 text-gray-700` bordered) but
  has no browser. Load `/` logged out and confirm the demo link reads as clearly secondary.
- The ticket's Notes contained a factually incorrect code suggestion (the TC14 assertion).
  Worth a note to the PM persona that suggested test code in Notes should be run before it
  ships in a ticket.
- `docs/ui-brief.md` is untracked and unrelated to this diff — pre-existing, left alone.
- Nothing was committed. Version control is yours.

### Round-1 QA report
Not archived here — no round-2 ran. The full report is at
`tickets/done/043-qa-review.md`.
