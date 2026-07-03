## Orchestration log — 028-route-common-helpers

**Run started:** 2026-07-02 16:53
**Run ended:** 2026-07-02 17:08
**Outcome:** completed

### Pre-flight
- Status check: pass (Status was `ready`)
- Type check: pass (`refactor`, not `audit`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- Touches non-empty: pass (web/routes/common.py, web/routes/overview.py, web/routes/waiver.py)
- Audit check: pass — `python3 scripts/audit_due.py` reported AUDIT NOT DUE (weighted 1.5 / 5, highest audited ticket 23)
- Architectural-surface coverage: pass — Touches paths are route handler modules, not the routing/middleware surface (`web/main.py`, `web/middleware/session.py`, route registration) in WORKFLOW.md's escalation list. Regardless, the ticket cites the covering active decision `docs/DECISIONS.md` 2026-05-30 ("Shared route helpers: web/routes/common.py is the canonical home"), which this ticket implements directly.

### Process
`Process: light` — Test Engineer ran combined QA + review; the Reviewer step (step 4) was skipped per orchestrator persona.

### Subagents spawned (in order)
1. Engineer (round 1) — subagent type `fh-engineer`
   - Inputs: `.team/engineer.md` (read from disk by the shim), `tickets/028-route-common-helpers.md`, `docs/DECISIONS.md` 2026-05-30 entry, relevant `docs/LEARNINGS.md`
   - Output: `tickets/028-done.md`
   - Summary: Created `web/routes/common.py` holding `_get_league_key(db, session_id) -> str | None` moved verbatim (underscore prefix kept) from `overview.py`. Updated `overview.py` to import from `web.routes.common` and removed the local def; changed `waiver.py`'s import source from `web.routes.overview` to `web.routes.common`. Verified via grep (single definition in common.py, both callers import from common, no import-from-overview remains), an import smoke check (`_get_league_key.__module__ == web.routes.common`), and `pytest` → 355 passed. No new tests (pure move; function has none). Live-browser walk not run (no Yahoo creds); mocked authenticated route tests stand in.

2. Test Engineer (round 1) — subagent type `fh-test-engineer`, combined QA + review mode
   - Output: `tickets/028-qa-review.md`
   - Verdict: APPROVED
   - Summary: All four ACs verified as observed fact. AC1: `common.py:8` defines the function, body byte-for-byte identical to `git show HEAD:web/routes/overview.py` lines 18-23. AC2: only definition in common.py; `overview.py:12` and `waiver.py:20` import from `web.routes.common`; no `from web.routes.overview import _get_league_key` anywhere. AC3/AC4: mocked authenticated route tests return 200 with leaderboard / filter form. `pytest tests/` → 355 passed, 0 failed (run via `.venv/bin/python`, since system `python3` lacks pytest). Diff strictly within Touches; all seven Reviewer always-blockers pass; behaviour-neutral. Set ticket Status to `done`.

### Files changed
- web/routes/common.py (new file, +~10)
- web/routes/overview.py (+1 -8)
- web/routes/waiver.py (+1 -1)
- tickets/028-route-common-helpers.md (Status ready → done)
- tickets/028-done.md (Engineer handoff, new)
- tickets/028-qa-review.md (combined QA+review report, new)

Cumulative source diff: ~3 lines changed + 1 small new file — well under the 200-line heuristic.

### Halt conditions tripped (if any)
- None. The Engineer's and Test Engineer's "live-browser walk not run" notes are honest environment disclosures (no Yahoo OAuth credentials available), not hedges on an acceptance criterion — the ACs themselves were stated as observed fact and covered by the mocked authenticated route tests.

### Notes for the owner
- Optional post-merge sanity check when you next run the app with real Yahoo credentials: log in and visit `/overview` and `/waiver` to confirm the live render, since this environment could only exercise the mocked route tests. The change is a pure definitional move, so no behaviour change is expected.
- This ticket was the prerequisite that DECISIONS.md 2026-05-30 required before the next feature route (029 — Week Projection) ships. That decision's interim state is now resolved; 029 is unblocked on this front.
- The Engineer noted two open `Type: bug` improvements items on `overview.py` — out of scope for this ticket and left untouched.
- Ticket Status is now `done`; changes are staged in the working tree but not committed (orchestrator never runs git). The owner manages version control.

### Round-1 QA report
Not overwritten — no round-2 ran (round-1 verdict was APPROVED). See `tickets/028-qa-review.md` for the full combined QA + review report.
