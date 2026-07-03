## Code Review — 030

**Files reviewed:**
- `web/routes/projection.py` — new `GET /projection/matchup` route (`projection_matchup` + `_matchup_impl` + pure `_player_breakdown`); stateless per-request fetch → compute → render.
- `web/templates/projection/_matchup.html` — bare HTMX fragment (no `base.html`): context line, three tally cards, category-comparison table with per-cell winner highlighting, two roster-breakdown tables via a shared macro.
- `tests/test_projection_matchup_route.py` — Engineer's 10 tests (every AC + bulk-call + param alias + session guards).
- `tests/test_projection_matchup_qa.py` — QA's 2 supplementary tests (opponent-win highlight lands on the correct column; tie applies no green).

### Scope: CLEAN
Product changes are confined to the two files in `Touches` (`web/routes/projection.py`, `web/templates/projection/_matchup.html`); the two test files are the mandated deliverable. The 029 shell route (`projection_shell`, lines 29–53) and `index.html` are untouched. No new `data/`/`analysis/` functions were added, as the ticket required. No "while I'm here" cleanup.

### Architecture: CLEAN
- **No framework import in a pure layer.** `fastapi` imports live only in the route module; `analysis/`/`data/` imports are pure. `_is_rate_stat` is passed into the template context — this matches the established precedent in `web/routes/waiver.py:281`, so it is a codebase convention, not a drift.
- **No per-entity Yahoo loop.** Team week stats come from a single bulk `get_all_teams_week_stats` call (line 131); last-30-day stats from one batched `get_players_lastmonth_stats` (line 145); remaining games from one bulk `get_remaining_games` (line 151). The only per-team calls are the two `get_team_roster` calls (one per team, inherent — no bulk roster endpoint). Conforms to DECISIONS.md 2026-05-30 "per-stat bulk fetch, never per-player" and the CLAUDE.md "Minimise API calls" rule.
- **Fragment pattern conforms** to DECISIONS.md 2026-05-30 "HTMX fragment pattern shell + fragment split": returns `_matchup.html` with no `base.html`.
- **Styling mapping lives in the template** (winner→CSS lines 46–55; rate/counting `fmt` lines 45, 91–95), consistent with DECISIONS.md 2026-04-19 "rank → Tailwind class mapping lives in templates."
- **No demo-counterpart gap** — no new `data/` function; the demo route is ticket 031 and `_matchup.html` carries no hardcoded route URLs, so 031 can reuse it unchanged.
- Port fidelity verified against source: `_player_breakdown` (lines 60–86) matches `pages/04_week_projection.py:504-527` exactly; the `team_a/team_b/Tie → name` tally mapping (lines 170–180) matches `pages/04_week_projection.py:457-469`; `project_team_stats` computes rate stats as a weighted average, never a sum, satisfying AC5.

### Verification adequacy: ADEQUATE
All five ACs are exercised through the real FastAPI + Jinja stack (TestClient renders the actual `_matchup.html`): context line, tally cards, winner-highlight classes, both roster breakdowns, bye message, and rate/counting precision. QA correctly identified and closed the AC2 gap in the Engineer's tests (Engineer only asserted green *exists* in the my-team-wins case; QA added correct-column and tie coverage). `tally` (analysis/matchup_sim.py:113) always returns all three keys with `0` defaults, so `counts[my_team_name]`/`counts["Tie"]`/`counts[opponent_name]` are safe. The skipped live-browser walk is justified twice over (no OAuth in-env; NHL off-season means a live week-keyed visit can only hit the empty state per LEARNINGS.md), and no AC requires visual inspection.

### Security: CLEAN
No tokens/secrets/session IDs logged (no logging in the new code). A bogus or unmatched `team_key`/`my_team` short-circuits to the bye message at line 114 **before** any roster/stats fetch, so it cannot drive spurious per-team API traffic. `_get_league_key` uses the existing parameterised query. No new dependencies. No auth-cookie surface touched. (Org rule "no client-side-only passwords" — N/A; no passwords here.)

### Issues
- **should-fix (logged, not blocking this ticket):** Dual query-param (`selected = team_key or my_team`, line 218). This is a **sound** pragmatic reconciliation, not a defect: AC1's literal URL uses `my_team`, but the immutable 029 shell sends `team_key` in both `<select name="team_key">` and the auto-load `hx-get`. Accepting both is the only way to satisfy the AC and the out-of-scope shell without editing 029. I agree with QA — non-blocking. Left in place, but the two names should eventually collapse to one via a future 029-shell ticket so the interface isn't permanently dual. Logged to `docs/improvements.md` as a `Type: quality` item.
- **nit:** `_player_breakdown` (route layer) recomputes counting-stat contributions with the same `lastmonth / gp * remaining` shape that `project_team_stats` uses internally. This is a faithful, ticket-directed port of the Streamlit page (which also kept this in the page layer) and produces display rows rather than analysis output, so it correctly stayed out of `analysis/`. No action needed.

### Verdict: APPROVED

Ticket status set to `done`; artifacts moved to `tickets/done/`. One new `docs/improvements.md` entry (`Type: quality`): "Converge Week Projection matchup route on a single team query-param name."
