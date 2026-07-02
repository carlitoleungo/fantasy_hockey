## Orchestration log — 027-test-demo-overview-routes

**Run started:** 2026-07-02 15:45
**Run ended:** 2026-07-02 16:03
**Outcome:** completed

### Pre-flight
- Status check: pass (Status was `ready`, Type `feature` — not an audit)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- Audit check: `python3 scripts/audit_due.py` → AUDIT NOT DUE (0.5 / 5 weighted). Pass.
- Architectural-surface coverage: pass (N/A) — the only `Touches` path is a test file (`tests/test_demo_overview_routes.py`), which is not on the WORKFLOW.md escalation list. No architectural surface touched, so no DECISIONS citation required.
- Process: no `## Process` section → full process (Engineer → Test Engineer → Reviewer).

### Subagents spawned (in order)
1. Engineer (round 1) — subagent `fh-engineer`
   - Inputs: `.team/engineer.md`, `tickets/027-test-demo-overview-routes.md`, reference tests (`test_demo_head_to_head_routes.py`, `test_waiver_routes.py`), `web/routes/overview.py`, `docs/LEARNINGS.md`
   - Output: `tickets/027-done.md`
   - Summary: Created new `tests/test_demo_overview_routes.py` (isolated-file option, matching the head-to-head precedent). 6 tests covering all 5 ACs incl. the 3 required names. Patched `data.demo.get_matchups` for data; asserted `web.routes.overview.make_session`/`get_matchups` not called for AC5. Ran file (6 passed) and full suite (355 passed). Flagged that AC2's literal `table_url="..."` string does not appear in rendered HTML — template emits `hx-get="{{ table_url }}"` — so asserted the rendered `hx-get="/demo/overview/table"` form instead. Set Status → `qa`.

2. Test Engineer (round 1) — subagent `fh-test-engineer`
   - Output: `tickets/027-qa.md`
   - Verdict: APPROVED
   - Summary: Independently verified all 5 ACs as observed facts, including unpatched drives against real demo data. Confirmed the AC2 adaptation is faithful (and stronger) — `overview/index.html:18` renders `table_url` as `hx-get="{{ table_url }}"`. Ran file (6 passed) and full suite (355 passed, no regressions in overview tests). All 3 required test names present. No QA-authored tests needed. Left Status `qa` for the Reviewer to advance.

3. Reviewer — subagent `fh-reviewer`
   - Output: `tickets/027-review.md`
   - Verdict: APPROVED
   - Summary: Scope clean (diff only the new test file, confirmed via `git status`). Architecture clean — patch targets verified against `web/routes/overview.py`: never-called assertions patch the importing-namespace live symbols while data swap patches the lazily-imported `data.demo.get_matchups`; distinct symbols, so AC5 genuinely proves the live path is untouched. AC2 adaptation correct and stronger than ticket wording. Security clean (public demo routes, no secrets, no client-side auth). Re-ran file: 6 passed. No blockers/should-fixes/nits. Set Status → `done`.

### Files changed
- tests/test_demo_overview_routes.py (new, +144)
- tickets/027-test-demo-overview-routes.md (Status field: ready → qa → done, +1 -1 net)
- tickets/027-done.md, tickets/027-qa.md, tickets/027-review.md (workflow artifacts)

### Halt conditions tripped (if any)
- None. No fix round needed. No diff outside `Touches`. Cumulative source diff is 144 lines (one new test file), under the ~200-line heuristic.

### Notes for the owner
- Ticket complete and set to `done`. No source code changed — this was a pure test-coverage ticket.
- Minor documentation-vs-reality note (already resolved in-flight, no action needed): the ticket's AC2 wording referenced a literal `table_url="/demo/overview/table"` string, but the template renders that context value as `hx-get="{{ table_url }}"`. All three roles independently confirmed the rendered-form assertion faithfully (and more robustly) covers AC2's intent. Consider tightening AC wording in future test tickets to reference rendered HTML rather than context-key names.
- Audit tracker at 0.5 / 5 weighted — not due.

### Round-1 QA report
No round-2 ran (round-1 verdict was APPROVED). See `tickets/027-qa.md` for the full report.
