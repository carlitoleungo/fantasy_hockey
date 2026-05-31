## Orchestration log — 020-demo-overview-leaderboard

**Run started:** 2026-05-31 (session start)
**Run ended:** 2026-05-31
**Outcome:** completed

### Pre-flight
- Status check: pass (ready)
- Required-sections check: pass (all 8 sections present)
- Architectural-surface coverage: pass with note — ticket cites "Decision 2026-04-19 (HTMX shell + fragment split)" which is the superseded version; active entry is 2026-05-30. Content is substantively identical (supersession only corrected ticket-number labels and added a Revisit if clause). Proceeded on judgment that the spirit of citation was met. The demo-mode parity surface was not directly triggered by the Touches paths (the ticket touches `web/routes/overview.py`, not `data/demo.py`).

### Mid-run halt (resolved)
- **Halt reason:** Engineer subagent reported "Edit tool permission is currently denied" — session was in "don't ask" mode, silently blocking all file edits in subagents. Additionally, `web/main.py` was missing from `Touches` but needed to be touched.
- **Resolution:** Owner switched permission mode to default (prompts) and added `web/main.py` to `Touches`. Orchestration restarted from Engineer round 1.

### Subagents spawned (in order)

1. **Engineer (round 1 — aborted)**
   - Blocked by permission mode before implementation; reported `web/main.py` missing from Touches.
   - No output files written.

2. **Engineer (round 1 — re-run after fixes)**
   - Inputs: `.team/engineer.md`, `tickets/020-demo-overview-leaderboard.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/LEARNINGS.md`, `web/routes/overview.py`, `web/templates/overview/index.html`, `web/main.py`, `web/routes/waiver.py` (reference), `analysis/team_scores.py`, `data/demo.py`
   - Output: `tickets/020-done.md`
   - Summary: Added `public_router` to `web/routes/overview.py` with `GET /demo/overview` shell and `GET /demo/overview/table?week=N` fragment routes. Updated `overview/index.html` to use `{{ table_url }}` instead of hard-coded `/overview/table`. Added `table_url` context var to both authenticated handlers. Registered `overview_public_router` in `web/main.py`. Closed improvements.md item. Walked golden path steps 1–3 via curl; confirmed 200s and correct HTML. Steps 4–5 flagged as untestable without Yahoo credentials.

3. **Test Engineer (round 1)**
   - Inputs: `.team/test-engineer.md`, `tickets/020-demo-overview-leaderboard.md`, `tickets/020-done.md`, `docs/LEARNINGS.md`, `docs/DECISIONS.md`
   - Output: `tickets/020-qa.md`
   - Verdict: APPROVED
   - Summary: 332 tests run, 332 passed. AC1–AC3 PASS with specific observations (200 status, HTML content including "Demo League", 12 team rows, colored rank cells, no Yahoo API log activity). AC4 PASS on HTML wiring / OWNER-MUST-VERIFY for in-browser swap. AC5 PASS on redirect / OWNER-MUST-VERIFY for live session. Flagged missing automated tests for demo routes as non-blocking.
   - Process note: Test Engineer set ticket Status to `done` prematurely (before Reviewer). Status was already correct at end of run so no correction needed.

4. **Reviewer**
   - Inputs: `.team/reviewer.md`, ticket, done, qa, `web/routes/overview.py`, `web/templates/overview/index.html`, `web/main.py`, `docs/improvements.md`, `web/routes/waiver.py` (reference), `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`
   - Output: `tickets/020-review.md`
   - Verdict: APPROVED
   - Summary: Scope clean (all changes within Touches). Architecture clean (public_router shape matches waiver.py reference exactly; table_url backward-compatible; no new implicit convention). Two should-fixes logged to improvements.md: (1) missing automated tests for `/demo/overview` routes; (2) hard-coded `/overview/head-to-head` link in `index.html` sends demo visitors to auth-protected route — should be fixed in ticket 021.

### Files changed
- `web/routes/overview.py` (added public_router + 2 demo routes + table_url in auth handler context dicts)
- `web/templates/overview/index.html` (hx-get hard-coded URL → `{{ table_url }}`)
- `web/main.py` (import + register overview_public_router)
- `docs/improvements.md` (closed 1 item, added 2 new should-fixes)
- `tickets/020-done.md` (new)
- `tickets/020-qa.md` (new)
- `tickets/020-review.md` (new)

### Halt conditions tripped
- Permission mode block (mid-run, resolved by owner before re-spawn)

### Notes for the owner
- **OWNER-VERIFIED (AC4):** Owner confirmed in-browser HTMX week-change swap works on `/demo/overview`.
- **OWNER-VERIFIED (AC5):** Owner confirmed authenticated `/overview` still loads live data correctly.
- **Ticket 021 note:** The `/overview/head-to-head` link in `index.html` is still hard-coded. When an unauthenticated visitor is on `/demo/overview`, clicking "Compare two teams →" will redirect them to login. Reviewer logged this to improvements.md; fix is scoped to ticket 021 when `/demo/overview/head-to-head` is built.
- **pyarrow environment note:** Engineer found pyarrow absent from the Python 3.11 env and installed it. This is a pre-existing gap that also affects `/demo/waiver`. Consider adding `pyarrow` to `requirements-web.txt` if it isn't already there.
