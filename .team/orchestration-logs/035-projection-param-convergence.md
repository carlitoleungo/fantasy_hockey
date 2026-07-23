## Orchestration log — 035-projection-param-convergence

**Run started:** 2026-07-22
**Run ended:** 2026-07-23
**Outcome:** completed — combined QA+review APPROVED, ticket promoted to `done`, artifacts moved to `tickets/done/`.

### Pre-flight
- Status check: pass (`ready`)
- Type check: pass (`refactor`, not `audit`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- Touches non-empty: pass (`web/routes/projection.py`, `tests/test_projection_matchup_route.py`, `tests/test_demo_projection_routes.py`)
- Audit check: `python3 scripts/audit_due.py` → AUDIT NOT DUE (weighted 1/5; ticket 032 counted since last audit). Not overdue.
- Architectural-surface coverage: pass — `web/routes/projection.py` change is query-param handling inside existing handlers (not `web/main.py`/middleware/route registration or the shell/fragment split); the other two paths are tests. No architectural surface. No new dep/env/config. No covering-decision citation required. The active DECISIONS entry "Web routes: demo and live handlers share a single compute/render helper (2026-07-03)" governs the untouched `_render_matchup` compute path and was cited to both subagents as a do-not-touch constraint.

### Model selection (hybrid rule)
- No `## Model` field on the ticket ⇒ heuristic. `Process: light` ⇒ **sonnet** for both Engineer and Test Engineer. Reviewer N/A (light ticket — combined QA+review). First live run of the per-ticket model-selection + archive-as-you-go process changes committed in 58a1297.

### Process note (surfaced, not a halt)
The ticket's DoD (written before the 2026-07-21 process change) instructed moving the scoped-from improvements item to `## Closed` in `docs/improvements.md`. The current process (now in the Engineer persona) archives closed items to `docs/archive/improvements-closed.md` instead. The Engineer spawn prompt directed following the current process; the Engineer did so correctly.

### Subagents spawned (in order)
1. Engineer — `fh-engineer` (model: sonnet)
   - Inputs: `.team/engineer.md` (re-read from disk), ticket, `docs/ARCHITECTURE.md`, the cited DECISIONS 2026-07-03 entry, `docs/LEARNINGS.md`
   - Output: `tickets/035-done.md`; Status → `qa`
   - Summary: Removed the `my_team` parameter and `or my_team` fallback from both `projection_matchup` and `demo_projection_matchup` in `web/routes/projection.py`; `team_key` is now the sole param, guard unchanged. Deleted `test_matchup_my_team_alias`, added `test_matchup_my_team_alone_is_not_a_selection`; converted all `?my_team=` call sites in `test_demo_projection_routes.py` to `?team_key=` and added `test_demo_projection_matchup_my_team_alone_redirects` (AC4). Moved the scoped-from improvements item to `docs/archive/improvements-closed.md` per the updated process. Full suite `392 passed`; drove the real app via uvicorn+curl (demo shell 200, demo matchup fragment 200 with `team_key`, `?my_team=` alone → 302, authenticated route without cookie → 302 to `/auth/login`). Confirmed `index.html` and the `_render_matchup`/`_matchup_impl` compute path untouched. Flagged one out-of-scope future-cleanup note (near-duplicate demo test).

2. Test Engineer (combined QA+review) — `fh-test-engineer` (model: sonnet)
   - Inputs: `.team/test-engineer.md` (re-read from disk), ticket, `tickets/035-done.md`, cited DECISIONS 2026-07-03 entry, `docs/LEARNINGS.md`
   - Output: `tickets/done/035-qa-review.md`
   - **Verdict: APPROVED.** Set Status to `done`, moved all three artifacts into `tickets/done/`.
   - Suite `392 passed, 0 failed`. ACs all PASS: AC1 auth-guard fires before param resolution (302 to `/auth/login`), mocked suite covers the 200 path (off-season, no live Yahoo per LEARNINGS); AC2 demo `?team_key=` → 200 with distinct fragments per team, verified live; AC3 no `my_team` param on either handler (remaining `my_team` hits are internal variable names in the untouched compute path); AC4 demo `?my_team=` alone → 302, verified live with curl; AC5 suite green. Combined-review checklist clean: no framework imports in `data/`/`analysis/`/`auth/`, no per-entity loops, demo/live parity intact (shared `_render_matchup` untouched, DECISIONS 2026-07-03), diff within Touches + the sanctioned improvements close-out. No blockers.
   - Logged one new `Type: quality` nit to `docs/improvements.md` (near-duplicate test pair in `tests/test_demo_projection_routes.py` made redundant by the alias removal) — flagged for future cleanup, not fixed (persona rules).

### Files changed
- web/routes/projection.py (+2 -4) — in Touches
- tests/test_projection_matchup_route.py (+9 -12) — in Touches
- tests/test_demo_projection_routes.py (+18 -7) — in Touches
- docs/improvements.md — scoped-from item removed from `## Open`; one new quality nit added by QA (sanctioned Test Engineer output)
- docs/archive/improvements-closed.md — scoped-from item archived with ticket-035 resolution note (sanctioned close-out)
- tickets/done/035-*.md — ticket promoted to done with done + qa-review artifacts

### Halt conditions tripped
- None. Clean single pass, no fix round.

### Notes for the owner
1. First run on the new model-selection heuristic (both roles on `sonnet` for this light ticket) and the archive-as-you-go doc process — both worked as intended; the Engineer archived the closed improvements item to `docs/archive/improvements-closed.md` rather than the stale `## Closed` location the ticket text named.
2. Two out-of-scope cleanup observations were logged to `docs/improvements.md` as `Type: quality` nits (near-duplicate demo tests after the alias removal) — no action required now; a future ticket can pick them up.
3. Ticket-text staleness worth a light PM touch-up next time: ticket DoDs that reference `## Closed` should say "move to `docs/archive/improvements-closed.md`" to match the current process.
