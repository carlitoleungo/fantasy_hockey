## Orchestration log — 025-parameterize-overview-nav-links

**Run started:** 2026-07-02 09:33
**Run ended:** 2026-07-02 10:30
**Outcome:** completed

### Pre-flight
- Status check: pass (`ready`)
- Type check: pass (`bug`, not `audit`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- Touches non-empty: pass (3 paths)
- Audit check: pass — `python3 scripts/audit_due.py` → `AUDIT NOT DUE` (weighted 0/5)
- Architectural-surface coverage: pass — the three Touches paths (`web/routes/overview.py`, `web/templates/overview/index.html`, `web/templates/overview/head_to_head.html`) change hardcoded `href`s into context-passed URL variables, the verbatim `table_url` pattern from tickets 020/021. This does not alter the HTMX shell+fragment structure or route/middleware registration (the actual arch surfaces — `web/main.py`, `web/middleware/session.py`, cache/client/oauth — are untouched). PM classified `Process: light` (no arch surface); concurred. No new convention established, so no DECISIONS citation required.

Note on `python`: system `python3` is the audit-script interpreter; the test suite requires the repo's `.venv` interpreter (`.venv/bin/python -m pytest`).

### Subagents spawned (in order)
1. Engineer (round 1) — `fh-engineer`
   - Inputs: `.team/engineer.md` (persona), ticket 025, `table_url` pattern reference (020/021), `docs/DECISIONS.md` 2026-04-19 + `docs/LEARNINGS.md` entries, `tests/test_demo_head_to_head_routes.py` shape
   - Output: `tickets/025-done.md`
   - Summary: Parameterized both nav links — `index.html` compare link → `{{ head_to_head_url }}`, `head_to_head.html` back link → `{{ overview_url }}`. Added URL context to all 8 dicts across `overview()`/`demo_overview()`/`head_to_head()`/`demo_head_to_head()` (both empty-state and normal branches each). Added 2 tests to `test_overview_routes.py` (TC7/TC8) and 2 to `test_demo_head_to_head_routes.py` (TC-D14/TC-D15). Closed the `docs/improvements.md` item. Suite: 349 passed. Set Status → `qa`. No new dependency/env/config.

2. Test Engineer (round 1, combined QA+review — `Process: light`) — `fh-test-engineer`
   - Output: `tickets/025-qa-review.md`
   - Verdict: **APPROVED**
   - Summary: All four ACs pass, verified by rendering each route end-to-end through the real FastAPI app and extracting actual nav anchors (AC1–AC4 confirmed). Suite: 349 passed, 0 failed. Confirmed the `base.html` unconditional `href="/overview"` masking concern is real and correctly handled (back-link tests assert full anchor markup, not bare substring — sound, not masking a regression). Light-ticket blocker checklist all clean: no shared-layer imports, no `_coerce`/`_as_list` concerns, no per-entity API loops, symmetric live/demo updates (no demo-parity gap), consistent with `table_url` pattern (no DECISIONS conflict), diff within `Touches`. Set Status → `done`.

Reviewer: omitted — `Process: light` ticket; combined QA+review covered the blocker checklist.

### Files changed
- web/routes/overview.py (+8)
- web/templates/overview/index.html (~1)
- web/templates/overview/head_to_head.html (~1)
- tests/test_overview_routes.py (+56)
- tests/test_demo_head_to_head_routes.py (+40)
- docs/improvements.md (item moved to Closed)
- tickets/025-parameterize-overview-nav-links.md (Status → done)
- tickets/025-done.md (new, Engineer handoff)
- tickets/025-qa-review.md (new, combined QA+review report)

Total diff: 114 insertions, 12 deletions — well under the ~200-line heuristic. Product-code diff is ~10 lines.

### Halt conditions tripped (if any)
- None.

### Notes for the owner
- Both subagents noted (as fact, not hedge) that no interactive browser click-through was performed — no browser exists in this environment. Neither treated it as a gap: the route tests render the real templates and yield the authoritative `href` targets a browser would follow, and no AC depends on visual/cosmetic behavior. If you want visual confirmation, the ticket's Verification section has the manual walkthrough steps.
- Uncommitted changes are staged in the working tree (git status above). Per orchestrator hygiene, I did not run git — version control is yours.
- Audit cadence: this light ticket counts ½ toward the 5-weighted-ticket audit interval. Audit was not due at pre-flight; re-check with `python3 scripts/audit_due.py` before the next arch-surface ticket.
