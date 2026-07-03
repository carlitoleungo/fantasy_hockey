## Orchestration log — 030-projection-matchup-fragment

**Run started:** 2026-07-03
**Run ended:** 2026-07-03
**Outcome:** completed

> Note: an initial pre-flight run on 2026-07-03 halted on the coverage-based
> architectural-surface check — the `_matchup.html` Touches path (Template-structure
> surface) did not cite the active covering decision. The owner authorised adding the
> citation ("Feature pages: HTMX fragment pattern with shell + fragment template split,
> 2026-05-30") to the ticket's Notes for the Engineer, then re-ran /orchestrate 30. This
> log records the successful re-run.

### Pre-flight (re-run)
- Type check: pass (`Type: feature`)
- Status check: pass (`Status: ready`)
- Required-sections check: pass (all required sections present)
- Touches non-empty: pass (`web/routes/projection.py`, `web/templates/projection/_matchup.html`)
- Audit check: pass — `python3 scripts/audit_due.py` → `AUDIT NOT DUE` (weighted 3 / 5)
- Architectural-surface coverage: pass
  - `web/routes/projection.py` → cites "Waiver and projection routes: per-stat bulk fetch,
    never per-player (2026-05-30)" (Notes line 48)
  - `web/templates/projection/_matchup.html` → now cites "Feature pages: HTMX fragment
    pattern with shell + fragment template split (2026-05-30)" (Notes line 44, added
    pre-run at owner's direction)

### Subagents spawned (in order)
1. Engineer (round 1) — `fh-engineer`
   - Inputs: `.team/engineer.md` (read from disk by shim), `tickets/030-projection-matchup-fragment.md`,
     cited DECISIONS.md entries (2026-05-30 fragment-split, 2026-05-30 bulk-fetch, 2026-04-19
     rank→Tailwind), `docs/LEARNINGS.md`, `pages/04_week_projection.py`, the 029 shell.
   - Output: `tickets/030-done.md`
   - Summary: Added stateless `GET /projection/matchup` (`_matchup_impl` + pure
     `_player_breakdown`): resolves opponent from scoreboard, one bulk `teams/stats` call,
     batched last-30-day for both rosters, projects/compares/tallies via existing pure
     functions. New bare fragment `_matchup.html` (context line, 3 tally cards, category
     table with per-cell highlight, per-team roster breakdown, bye state). Added
     `tests/test_projection_matchup_route.py` (10 tests). Suite: 372 passed. Flagged a
     genuine conflict: AC1's `?my_team=` vs the immutable 029 shell's `?team_key=` — resolved
     by accepting both (`selected = team_key or my_team`).

2. Test Engineer (round 1) — `fh-test-engineer`
   - Output: `tickets/030-qa.md` (+ supplementary `tests/test_projection_matchup_qa.py`)
   - Verdict: APPROVED
   - Summary: Independently re-ran suite (372 → 374 passed after adding 2 tests). All 5 ACs
     PASS via the real FastAPI+Jinja render stack + code inspection; added tests proving the
     opponent-wins and tie highlight cases. Bulk conformance confirmed (single
     `get_all_teams_week_stats`; batched last-30-day). Ruled the dual query-param acceptable
     and non-blocking, and ruled that NO acceptance criterion requires manual/visual browser
     inspection (unverified items are presentational, not ACs; off-season live data is empty
     anyway — demo mode / ticket 031 is the visual-check path).

3. Reviewer — `fh-reviewer`
   - Output: `tickets/done/030-review.md`
   - Verdict: APPROVED (no blocker, no should-fix)
   - Summary: Scope clean (product changes confined to the two Touches files). Architecture
     clean (bulk fetches, bare fragment, styling in template; conforms to DECISIONS.md
     2026-05-30 + 2026-04-19; port fidelity checked against `pages/04_week_projection.py`).
     Security clean (no token logging; bogus team key short-circuits to bye before any fetch;
     parameterised lookup). ~296-line product diff judged appropriately factored, not bloat.
     Dual query-param confirmed sound; filed as a `Type: quality` follow-up in
     `docs/improvements.md` rather than a change request.

### Files changed
- `web/routes/projection.py` (+185)
- `web/templates/projection/_matchup.html` (new, 111 lines)
- `tests/test_projection_matchup_route.py` (new — Engineer)
- `tests/test_projection_matchup_qa.py` (new — Test Engineer)
- `docs/improvements.md` (+1 `Type: quality` follow-up entry)
- Ticket + artifacts moved to `tickets/done/` (spec, done, qa, review); Status → `done`

### Halt conditions tripped
- None during the loop. (Pre-flight halt on the first run — resolved by the owner-authorised
  citation add — is noted above.)

### Notes for the owner
- **Follow-up filed (non-blocking):** `docs/improvements.md` line 127 — "Converge Week
  Projection matchup route on a single team query-param name". The route currently accepts
  both `team_key` (029 shell) and `my_team` (AC1). Both QA and Reviewer judged this sound;
  a small shell ticket could converge on one name later.
- **Diff size:** the ~296-line product diff exceeds the team's ~200-line heuristic. It went
  through the full mandatory Reviewer pass (the human-review the heuristic calls for) and was
  judged appropriately factored — flagging here only for visibility.
- **WORKFLOW.md staleness (worth fixing):** the "Architectural-surface escalation list" still
  points the Template-structure surface at the superseded 2026-04-19 fragment-split entry; the
  active entry is 2026-05-30. Updating that pointer would prevent the same pre-flight friction
  on future fragment tickets (e.g. 031).
- Git is untouched — the owner manages version control. Working tree has the changes staged
  as shown; nothing committed by the workflow.
