## Orchestration log — 044-base-html-default-flip

**Run started:** 2026-09-17
**Run ended:** 2026-09-17
**Outcome:** completed

### Pre-flight
- Status check: pass (`ready`)
- Type check: pass (`refactor`)
- Required-sections check: pass (all eight present)
- `Touches` non-empty: pass (4 paths)
- Audit check: pass — 1.5 / 5, AUDIT NOT DUE
- Architectural-surface coverage: pass — `web/templates/base.html` is on WORKFLOW.md's
  template-structure surface. The ticket cites `docs/DECISIONS.md` 2026-07-25 "Nav shell:
  render sites that cannot resolve a user declare the state unknown and render nav-free;
  exception handlers never derive auth" by date, and implements its "Forward commitment
  (sequenced after 036b, not part of this fix)" paragraph. The Tech Lead consult was already
  taken as part of that entry; no new one was owed.
- Dependencies: 042 (done), 036b (done 2026-07-25, the flip's only blocker), 039 (done).

### Model selection
- Engineer: `opus` — heuristic branch `Process: full` (no Process field ⇒ full) with 4
  `Touches` paths (≥ 3) and an architectural surface. No `## Model` section in the ticket.
- Test Engineer: `opus` — same branch.
- Reviewer: `opus` — always.

### Subagents spawned (in order)
1. Engineer (round 1)
   - Output: `tickets/044-done.md`
   - Summary: Split `{% elif is_authenticated is undefined or is_authenticated %}` into
     `{% elif is_authenticated is undefined %}` (nav-free) and `{% elif is_authenticated %}`,
     keeping the absent and explicit-False cases structurally distinguishable. Left the
     `auth_state_unknown` branch first and explicit. Updated the test matrix, renamed the
     misleading overview test, retired both stale comments, added the `__pycache__` purge
     entry to LEARNINGS, and closed three improvements items. Suite: 479 passed (478 + 1).
   - **Corrected the ticket:** its Notes named lines 174, 241 and 311 as the authenticated
     `shell_context` spreads, but 241 and 311 are demo branches. The real authenticated
     spreads are 56, 77, 146 and 174 — four, not three. Probed all four, purging
     `__pycache__` before every mutation; each failed at least one test. Restored
     `web/routes/overview.py` byte-identical (md5 verified).

2. Test Engineer (round 1, normal QA — `Process: full`)
   - Output: `tickets/044-qa.md`
   - Verdict: **APPROVED**
   - Summary: Verified all five behaviour-table rows plus six extra combinations, scraping
     anchors from inside `<nav>` only. Confirmed `auth_state_unknown` still wins when
     combined with `is_authenticated=True` and with `demo_mode=True` — demonstrably winning,
     not merely co-existing. Grepped for the spreads itself rather than trusting either
     line-number list, confirmed the Engineer's correction, and established nothing was
     missed: the two other authenticated routes are HTMX fragment routes that render no
     shell and correctly carry no spread.
   - **Ran a counterfactual the ticket did not require.** The naive version is confounded, so
     QA repeated 040's assertion ablation against both templates: under the new template each
     of the four mutations fails its own branch test; under the pre-044 template no branch
     test fires for any of them (all four produce an identical failure set caused by the old
     template, not by the mutation). That converts AC4 from "these tests fail now" into
     "these tests fail because of this change" — the actual claim in the ticket's Why.
   - The `.pyc` size collision was live during the run (four mutations, identical 11536-byte
     files) yet each probe named a distinct test, which is direct evidence the purge worked
     rather than an assertion that it was followed.

3. Reviewer (round 1)
   - Output: `tickets/done/044-review.md`
   - Verdict: **APPROVED** — no blockers, no should-fixes
   - Summary: Scope and architecture clean; `git status` shows exactly seven paths (the four
     in `Touches`, the two tracker files the Notes authorise, the ticket's Status line).
     Read the full 2026-07-25 entry and confirmed the implementation matches all three things
     its Forward commitment paragraph specifies, rather than merely citing it. Re-ran the
     suite: 479 passed. Independently confirmed `web/routes/overview.py` md5.

### Reviewer rulings requested
1. **DECISIONS.md needs a discharge marker, not a new entry.** The flip is the literal
   execution of an existing ruling with the same rationale and branch structure, so it earns
   no entry of its own — but the 2026-07-25 entry's final paragraph still reads as pending
   work "blocked on 036b". Logged as a `Type: quality` item flagged **Tech Lead action**,
   naming the resulting branch shape so the amendment can be written without re-deriving it.
   The Reviewer did not edit DECISIONS.md.
2. **No tracker item for the wrong line numbers.** The correction already survives in three
   durable places, and the durable fix is that the new LEARNINGS entry — the one a future
   ticket will actually read — cites no line numbers at all.
3. **Leaving `tests/test_nav_shell.py:168` was right.** The stale "dormant until 036b adopts
   it" comment is not named in AC5, Out of scope is emphatic, and a comment edit in an
   already-open file is exactly the "while I'm here" cleanup the Reviewer checklist says to
   flag rather than reward. Logged as `Type: quality` pointing at the `tests/conftest.py`
   consolidation ticket audit 041 reserved.
4. One non-blocking nit, recommended left alone: the new branch has an empty `{% elif %}`
   body, which reads as an oversight at a glance. The DECISIONS-citing comment above it is
   the right mitigation; restructuring would cost more clarity than it buys.

### Files changed
- `web/templates/base.html` (+6 -2)
- `tests/test_nav_shell.py` (+16 -5), `tests/test_overview_routes.py` (+3 -3)
- `docs/LEARNINGS.md` (+11)
- `docs/improvements.md` (net -9, three items closed, two new filed by the Reviewer),
  `docs/archive/improvements-closed.md` (+27)
- Moved to `tickets/done/`: the ticket, `044-done.md`, `044-qa.md`, `044-review.md`

Code diff is small; the line counts above are dominated by tracker bookkeeping. Well under
the ~200-line halt heuristic. Orchestrator verified scope independently via `git status
--short` and `git diff --stat`, and re-checked `web/routes/overview.py`'s md5
(`53e0ec6ee9ad6a77e03e66a122b939bf`) since that file is NOT in `Touches` and was mutated
four times during the probe.

### Halt conditions tripped
- None. No fix round needed.

### Notes for the owner
- **Two pages remain owner-must-verify**, unchanged from QA to Reviewer: the authenticated
  walk (`/`, `/overview`, `/waiver`, `/projection`) and the error page. Both the Engineer and
  QA hit the same wall — those routes 302 to `/auth/login`, which 302s to Yahoo, which
  returned **429**. Residual risk is low and asymmetric: every affected page passes flags
  explicitly and lands on branches the diff does not touch, and QA showed `error.html`
  rendered with no shell flags now yields zero nav anchors where it previously yielded the
  full authenticated nav. The flip makes the unverifiable surface strictly safer, not riskier.
- **Yahoo returned 429 (rate limited)** during this run. Unrelated to 044, but worth knowing
  before the first deploy — it blocked two agents from reaching authenticated pages.
- **One Tech Lead action queued:** amend DECISIONS 2026-07-25 to mark the Forward commitment
  discharged. It currently reads as pending work.
- The ticket's own Notes contained incorrect line numbers. Both the Engineer and QA caught it
  independently. Same class of defect as ticket 043's unrunnable suggested test code — the PM
  persona is shipping unverified specifics in ticket Notes, twice now in one session.
- Nothing was committed by any subagent.

### Round-1 QA report
Not archived here — no round-2 ran. Full report at `tickets/done/044-qa.md`.
