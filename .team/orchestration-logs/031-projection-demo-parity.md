## Orchestration log — 031-projection-demo-parity

**Run started:** 2026-07-03
**Run ended:** 2026-07-03
**Outcome:** completed

### Pre-flight
- Status check: pass (Status was `ready`)
- Type check: pass (Type `feature`, not `audit`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- Touches non-empty: pass (`web/routes/projection.py`, `web/main.py`)
- Audit check: `python3 scripts/audit_due.py` → AUDIT NOT DUE (weighted 4/5, highest audited ticket 23). Not blocking.
- Architectural-surface coverage: pass. Ticket touches Routing/registration (`web/main.py`, public vs authenticated route registration) and Demo-mode parity surfaces. Active covering decision `2026-05-30 "Web routes: demo route pairing policy"` (docs/DECISIONS.md:80, non-superseded) exists and is cited by the ticket in Notes for the Engineer by date and title. This ticket *satisfies* that policy for the projection route (ships the demo counterpart in-ticket).
- Dependency: ticket 030 complete (commit fb1d09d) — required since demo routes reuse index.html/_matchup.html and the same compute path.

### Subagents spawned (in order)
1. Engineer (round 1) — subagent type `fh-engineer`
   - Inputs: .team/engineer.md, tickets/031-projection-demo-parity.md, relevant DECISIONS/LEARNINGS context, focused instruction.
   - Output: tickets/031-done.md
   - Summary: Added a `public_router` in web/routes/projection.py with `GET /demo/projection` (shell) and `GET /demo/projection/matchup` (fragment), following the `demo_overview*`/`demo_waiver*` pattern. Extracted the compute+render tail of `_matchup_impl` into a shared `_render_matchup(...)` helper used by both live and demo paths. Demo fragment resolves the pair directly from `demo.get_projection_pair_data()` (no scoreboard loop), swaps rosters on opponent selection. Registered `projection_public_router` in web/main.py. Added tests/test_demo_projection_routes.py (11 tests). `python3 -m pytest tests/` → 385 passed. Flagged two things honestly (see Notes for owner).

2. Test Engineer (round 1) — subagent type `fh-test-engineer`
   - Output: tickets/031-qa.md
   - Verdict: APPROVED
   - Summary: Independently verified all four ACs against code and via TestClient, including against the real committed Week 14 demo JSON (unpatched). AC1–AC4 all PASS. Ruled the AC4 "redirects to `/`" wording flag a definitive PASS (substantive requirement — auth still enforced, behaviour unchanged — holds; logged-out routes 302 → /auth/login via untouched require_user path). Full suite 385 passed. Diff within Touches. Demo routes never touch the live Yahoo path (make_session asserted uncalled). One owner-must-verify item stated as fact: did not open a real browser, so the client-side HTMX swap painting/CSS layout was not observed headlessly (attributes identical to already-working 029/030 shell; low risk).

3. (fix round) — not applicable (QA APPROVED on round 1)

4. Reviewer (round 1) — subagent type `fh-reviewer`
   - Output: tickets/031-review.md
   - Verdict: APPROVED
   - Summary: Clean on scope, architecture, and security. Diff within Touches plus the new test file; no drift into templates/data/analysis/auth. `_render_matchup` extraction is behaviour-preserving for the live path; live handlers retain `Depends(require_user)`; demo path makes zero Yahoo calls (asserted). Satisfies 2026-05-30 demo route pairing policy in-ticket. No blockers, no should-fixes, no new improvements.md entries. Set ticket Status to `done` and moved all artifacts into tickets/done/.

### Files changed
- web/main.py (+2 -0)
- web/routes/projection.py (+132 -4)
- tests/test_demo_projection_routes.py (new, 11 tests)
- tickets/031-projection-demo-parity.md (Status → done; moved to tickets/done/)

### Halt conditions tripped (if any)
- None.

### Notes for the owner
- **Audit comes due after this ticket.** Pre-flight showed weighted 4/5 (NOT DUE) *before* 031. 031 is a feature touching an architectural surface (routing), so once it counts it brings the weighted total to ~5 → AUDIT DUE. The next architectural-surface ticket will halt at pre-flight until a Reviewer audit checkpoint runs. Schedule the audit before the next routing/cache/client/template/auth ticket.
- **Uncommitted work.** The moved artifacts in tickets/done/, the source changes (web/main.py, web/routes/projection.py), and the new test file are untracked/uncommitted. Committing is left to your normal git flow (the workflow only commits when asked).
- **Browser-visual gap (low risk).** QA verified the shell emits correct HTMX attributes and the fragment URLs return 200 with correct content, but did not open a real browser to observe the client-side HTMX swap painting or CSS/layout. Attributes are identical in form to the already-shipped 029/030 shell. If you want full confidence, spot-check `/demo/projection` in an incognito browser.
- **AC4 wording nit.** The AC says logged-out requests "redirect to `/`"; the actual (unchanged) redirect target is `/auth/login`. Both Engineer and QA flagged and reconciled this — the substantive requirement holds. Consider tightening the AC wording convention in future demo-parity tickets.
- **Pre-existing open item (not this ticket's scope).** docs/improvements.md item to converge the projection route's dual `team_key`/`my_team` param names remains open — its fix touches projection/index.html, outside 031's Touches. Left for a follow-up shell ticket.
- Environment note: this machine uses `python3` (bare `python` is not on PATH).
