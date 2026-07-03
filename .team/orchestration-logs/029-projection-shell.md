## Orchestration log — 029-projection-shell

**Run started:** 2026-07-03
**Run ended:** 2026-07-03
**Outcome:** completed

### Pre-flight
- Status check: pass (`ready`)
- Type check: pass (`feature`, not audit)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- Touches non-empty: pass (4 paths)
- Audit check: pass — `python3 scripts/audit_due.py` reported AUDIT NOT DUE (weighted 2/5). Note: `python` is not on PATH in this environment; `python3` is required.
- Architectural-surface coverage: pass. Touches hits routing (`web/main.py`, new `web/routes/projection.py`), template shell/fragment (`web/templates/projection/index.html`), and nav (`web/templates/base.html`). Covering active DECISIONS entries all exist and are cited by the ticket:
  - "Feature pages: HTMX fragment pattern with shell + fragment template split" — ACTIVE entry dated **2026-05-30** (supersedes the same-title 2026-04-19 entry; substance unchanged). Ticket cites this decision by title but with the stale **2026-04-19** date. Coverage is satisfied (active entry exists, cited by title); the stale date is a documentation nit, not a coverage gap — flagged to owner below.
  - "League context: session-state propagation retained" (2026-04-19) — active, cited.
  - "Nav shell: feature links added per ticket" (2026-04-19) — active, cited.
- Dependency check: ticket 028 (`_get_league_key` in `web.routes.common`) confirmed complete and present before spawning.

### Subagents spawned (in order)
1. Engineer (round 1) — `fh-engineer`
   - Inputs: `.team/engineer.md` (via shim), `tickets/029-projection-shell.md`, relevant DECISIONS entries (with the 2026-05-30 active-date correction), ticket-028 import note.
   - Output: `tickets/029-done.md`; Status advanced `ready` → `qa`.
   - Summary: Built `GET /projection` shell mirroring `waiver_shell`; new `projection.py` route (39L) + `projection/index.html` template (37L); registered `projection_router` in `main.py` (+2); added "Projection" nav link after "Waiver" in `base.html` (+1). Fragment URL parameterized as `matchup_url` (default `/projection/matchup`), not hardcoded. Added `tests/test_projection_routes.py` (198L, 7 tests). Full suite 362 passed. `/demo/projection` still 404. Flagged: empty-state keyed off `get_teams == []` (shell fetches no matchups per minimal-footprint instruction); selected team carried as `team_key` query param for the 030 fragment contract.

2. Test Engineer (round 1) — `fh-test-engineer`
   - Output: `tickets/029-qa.md`; Status advanced `qa` → `review`.
   - Verdict: **APPROVED**
   - Summary: Wrote own test plan from ACs first, then re-rendered `/projection` out-of-band against a fresh in-memory DB with mocked data, inspecting raw HTML. All 5 ACs + both session guards verified as observed fact. Full suite 362 passed (run via `.venv/bin/python` — system `python3` lacks pytest/httpx). Confirmed `matchup_url` genuinely parameterized (no hardcoded 3rd occurrence), `hx-trigger` includes `load`, `<h1>` exactly "Week Projection", nav order Overview → Waiver → Projection, `/demo/projection` 404. Confirmed `team.team_key` access matches real `get_teams` dict shape (data/client.py). Pre-season-with-teams-but-no-matchups case explicitly flagged as a 030 concern, not a blocker.

3. Reviewer (round 1) — `fh-reviewer`
   - Output: `tickets/029-review.md`
   - Verdict: **APPROVED**
   - Summary: Diff clean across scope, architecture (layer purity intact; route does orchestration; reuses `client.get_teams` which already uses `_as_list()`; single collection call, no per-entity loop; `_get_league_key` from `common` with parameterized SQL), decision conformance (active 2026-05-30 fragment decision + active League context + Nav shell), and security (no secrets logged, both guards correct, no new deps, no client-side auth). Sole finding: stale 2026-04-19 citation in ticket text (no code impact). No `docs/improvements.md` entries logged.

### Files changed (ticket 029 diff only)
- `web/routes/projection.py` (new, +39)
- `web/templates/projection/index.html` (new, +37)
- `web/main.py` (+2)
- `web/templates/base.html` (+1)
- `tests/test_projection_routes.py` (new, +198 — authorized by ticket Verification section)

Feature product code ~79 lines, well under the 200-line halt heuristic.

### Halt conditions tripped (if any)
- None. No fix round needed. Engineer flagged an interpretation (empty-state trigger) but resolved it with documented reasoning rather than posing an open question; QA independently validated it against AC5.

### Notes for the owner
- **Stale DECISIONS citation (documentation nit, no code impact):** ticket 029's "Notes for the Engineer" cites the HTMX shell+fragment decision as `2026-04-19`, but the active entry is the `2026-05-30` supersession of the same title (the 04-19 entry only corrected a factual error and added a `Revisit if` clause; substance identical). Consider a PM pass to update future ticket citations to `2026-05-30`. Coverage was satisfied, so this did not block orchestration.
- **Pre-season edge case for 030:** a league that has teams but no matchups yet will still render the team selector (the shell has no matchup data by design). The empty-state fires only when `get_teams` returns `[]`. QA flagged this as belonging to the 030 fragment — carry it forward when scoping/implementing 030.
- **Environment note:** `python` is not on PATH; use `python3` for scripts, and `.venv/bin/python -m pytest` for the test suite (system `python3` lacks pytest/httpx).
- **Out-of-band housekeeping performed this run (owner-requested, not part of ticket 029):**
  - Moved already-completed tickets into `tickets/done/`: `024-audit-checkpoint.md`, and the 028 set (`028-route-common-helpers.md`, `028-done.md`, `028-qa-review.md`).
  - Added a "move done tickets to `tickets/done/`" rule at every place a ticket transitions to `done`: `.team/reviewer.md`, `.team/test-engineer.md` (light-process branch), `.team/orchestrator.md` (step 5 + light-process branch), and `WORKFLOW.md` (standard loop step 5 + light-process section). Rule: on `done`, move the ticket and all its artifacts (`tickets/NNN-*.md`) into `tickets/done/`.
  - This run exercised the new rule: ticket 029's four artifacts (`029-projection-shell.md`, `029-done.md`, `029-qa.md`, `029-review.md`) were moved into `tickets/done/` on promotion.
- These file moves and doc edits are staged in the working tree but **not committed** — the orchestrator does not run git. Commit them at your discretion (note they are logically two changesets: the 029 feature, and the workflow-housekeeping).

### Round-1 QA report
No round-2 ran (round-1 verdict was APPROVED). See `tickets/done/029-qa.md` for the full report.
