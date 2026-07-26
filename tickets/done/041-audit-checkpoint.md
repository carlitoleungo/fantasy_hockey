# 041 — Audit checkpoint: tickets 032, 034, 035, 036a, 036b, 037

## Status
done

## Type
audit

## Milestone
none

## Touches
- .team/audits/041-audit.md
- docs/improvements.md

## Why
`scripts/audit_due.py` reports **AUDIT DUE at 5.5 / 5** as of 2026-07-26: six non-audit
tickets have completed since the last audit covered work through ticket 031. Per the
mandatory audit cadence the Reviewer reads those tickets end-to-end and produces an audit
report. This audit also gates ticket **039** (`fly.toml`), which is architectural-surface
work the PM cannot finalise while an audit is outstanding. Tickets 038 and 040 are not
blocked and may proceed in parallel.

Beyond the standard checkpoint, the owner has asked this audit to answer a specific
question: the suite has grown to 433 test functions and 8,520 lines against 3,496 lines of
source, and they want to know whether that is the right amount, whether anything is
redundant, and whether anything is stale. See Theme B below.

## Acceptance criteria
- [x] `.team/audits/041-audit.md` exists, follows the audit-report format in `.team/reviewer.md`, and covers all six tickets: 032, 034, 035, 036a, 036b, 037
- [x] Each ticket's acceptance criteria are checked against the actual shipped code and diffs, not just the done note
- [x] Theme A (cache + nav-shell conventions) and Theme B (test-suite health) each get an explicit section with findings, including a stated position on the three Theme B questions
- [x] Any convention the code now embodies without a `DECISIONS.md` entry is surfaced as a proposed entry for the Tech Lead to ratify
- [x] Open items are logged to `docs/improvements.md` or handed to the PM as follow-up ticket candidates, with a clear verdict of HEALTHY or NEEDS ATTENTION

## Out of scope
- **Fixing anything found.** Flag it; the PM scopes follow-ups. This ticket changes no
  source code and no tests.
- **Deleting or consolidating tests.** Theme B produces findings and a recommendation, not
  edits. Any consolidation is a separate ticket the PM writes from this report.
- Tickets at or below 031 (covered by `.team/audits/032-audit.md` and earlier).
- Installing `pytest-cov` or any other dependency to measure coverage. If a real coverage
  run is needed to answer Theme B question 2, say so in the report and let the owner decide.
- Re-opening decisions already ratified in `docs/DECISIONS.md`. Conformance is in scope;
  re-litigation is not.

## Notes for the Engineer
(This ticket is executed by the Reviewer in audit-checkpoint mode, not by an Engineer.)

**Do not re-audit tickets ≤ 031.** `.team/audits/032-audit.md` covers 025, 027, 028, 029,
030, 031 and returned HEALTHY; its suggested actions all appear resolved (its two PM actions
became tickets 035 and 036a/036b, and its Tech Lead action became the `docs/DECISIONS.md`
2026-07-03 "Web routes: demo and live handlers share a single compute/render helper" entry).
Confirm that follow-through rather than assuming it.

**The six tickets to cover** (specs and artifacts all in `tickets/done/`):
- **032** — Waiver multi-position filter (feature)
- **034** — Projection roster readability (feature)
- **035** — Projection param convergence (light; combined `035-qa-review.md` replaces separate qa/review files)
- **036a** — Nav shell foundation: `shell_context()` helper + conditional `base.html` (feature)
- **036b** — Demo nav adoption (feature)
- **037** — Cache write-hardening: atomic rename + per-league lock + `_shared/` affordance (refactor)

### Theme A — cache and nav-shell conventions
Two surfaces saw significant work and are the natural focus:
- **Nav shell.** 036a/036b spread `shell_context()` across 12 branches. Check the pattern is
  applied consistently and conforms to `docs/DECISIONS.md` 2026-07-03 "Nav shell: conditional
  on auth/demo state via shared shell-context" and the 2026-07-25 entry on error pages
  rendering nav-free. Ticket **040** is already scoped to close the known regression-guard
  gap (5 of 12 branches unasserted) — do not duplicate it; verify nothing else was missed.
- **Cache.** 037 rewrote every write path. Verify conformance to the two 2026-07-23 cache
  decisions, and note these specific items already surfaced during its review:
  - Its diff was ~350 lines against the workflow's ~200-line halt heuristic (~108 net source
    lines, the rest tests). Recommend whether the heuristic should count source lines only.
  - A `None` league key previously raised `TypeError` and now silently resolves to
    `_shared/`. The fail-fast net is gone; confirm that is acceptable until M2.
  - The live-Yahoo-OAuth browser walk in 037's Verification section was never run. QA closed
    everything reachable without live credentials and said so plainly. Record it as an open
    owner verification, not a pass.
  - A `Type: quality` improvements entry exists for the missing `fsync` in `_atomic_write()`.
    Confirm it is still tracked and correctly scoped out of 037.

### Theme B — test-suite health (owner-requested)
The standard audit checklist covers under-testing (verification gaps) but has no check for
redundancy, staleness, or growth rate. The owner wants that direction covered. Measurements
already taken on 2026-07-26, for you to verify and build on:

| Layer | Source | Test | Ratio |
|---|---|---|---|
| `data/` + `analysis/` core modules | 1,193 | 1,984 | 1.7:1 |
| `web/routes/` | 1,302 | 4,933 | 3.8:1 |
| `auth/oauth.py` (direct tests only) | 201 | 59 | 0.3:1 |

Answer these three questions explicitly:
1. **Route-test bulk.** `web/routes/` carries 3.8:1, and route tests assert against rendered
   HTML, so template edits break tests that were never about the template. Can fixtures be
   shared and redundant HTML assertions dropped without losing a real guard? `tests/test_waiver.py`
   is the extreme case at 25 tests over 807 lines (~32 lines per test).
2. **Auth coverage — the opposite risk.** A name-reference scan across the suite found
   `validate_and_consume_state` (OAuth CSRF state check) and `_try_refresh` (token refresh)
   in zero test files. This is a proxy, not a coverage measurement: both may be exercised
   indirectly through `/auth/callback` route tests. Determine whether the coverage is real.
   If only a `pytest-cov` run can settle it, say so rather than guessing (see Out of scope).
3. **The `*_qa.py` convention.** Four files (`test_nav_shell_qa.py`, `test_overview_routes_qa.py`,
   `test_projection_breakdown_qa.py`, `test_projection_matchup_qa.py`) hold 30 tests over
   1,011 lines of QA-authored supplementary coverage. This is permitted by `docs/DECISIONS.md`
   2026-05-31 "Team process: Engineer owns automated test coverage; QA does not fill gaps"
   (QA may add edge cases on top of Engineer AC coverage), and their docstrings read as
   genuine edge cases. But the file-naming split is an unratified convention that costs
   discoverability. Are they real edge cases or restatements? Should the convention be
   ratified in `DECISIONS.md`, or the files merged into their siblings?

Two findings already established, so do not spend time re-deriving them: **no test references
`streamlit`, `app.py`, or `pages/`**, so there is nothing stale to archive from the migration;
and there are **no skipped or xfail tests** hiding rot. `data/` and `analysis/` at 1.2:1–2.0:1
look correctly proportioned — the concern is routes and auth, not the core.

Note the naming collision worth fixing while you are here: `.team/audits/032-audit.md` covers
tickets 025–031, but ticket 032 is the waiver multi-position filter, so "032" means two
different things. Audit 024 has a matching `024-audit-checkpoint.md` ticket; audit 032 does
not. Recommend a convention so this does not recur.

## Verification
- `.team/audits/041-audit.md` exists with per-ticket findings for all six tickets plus the
  two named theme sections and an explicit HEALTHY / NEEDS ATTENTION verdict.
- Theme B's three questions each have a stated answer and a recommendation, including whether
  a follow-up consolidation ticket is warranted and roughly what it would cover.
- `scripts/audit_due.py` reports `AUDIT NOT DUE` after this ticket completes and moves to
  `tickets/done/`.
- The PM reads the report and acts on flagged items before ticket 039 is orchestrated.

## Dependencies
- None. This ticket is the prerequisite for ticket **039** (architectural surface). Tickets
  038 and 040 are not blocked by it.
