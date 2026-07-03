## Implementation complete — 030

**What I did:**
- Added the `GET /projection/matchup` fragment route in `web/routes/projection.py`. It is stateless (like `_waiver_post_impl`): per request it fetches settings+categories, teams, scoreboard, all-teams week stats (one bulk call), both rosters (today's date), both rosters' last-30-day stats (one bulk batch call), and remaining NHL games, then computes and renders the projection.
- Resolved the opponent from the scoreboard matchup pairings, projected both teams with `project_team_stats`, compared with `compare_projections` (using `lower_is_better_from_categories`), and tallied category wins with `tally` — mapping `"team_a"/"team_b"/"Tie"` to team names exactly as the Streamlit page does.
- Added a pure `_player_breakdown` helper (plain Python, sorted by games left desc) porting the per-player math from `pages/04_week_projection.py:504-527`: counting stat = `lastmonth / games_played * remaining`, rate stat = the lastmonth rate directly, guarding `games_played == 0`.
- Created `web/templates/projection/_matchup.html` — a bare HTML fragment (no `base.html`): context line, three tally cards (my wins / ties / opp wins), category-comparison table with per-cell winner highlighting, and a roster-breakdown table for each team. All rank/format → CSS class mapping lives in the template (Tailwind utility classes). Bye state renders a "no matchup this week" message and no tables.
- Added `tests/test_projection_matchup_route.py` (10 tests) covering every AC plus the bulk-call, param-alias, and session guards.

**Files changed:**
- `web/routes/projection.py` — added `/projection/matchup` route + `_matchup_impl` + `_player_breakdown`; imports for the analysis/data functions the ticket names.
- `web/templates/projection/_matchup.html` — new fragment template (created).
- `tests/test_projection_matchup_route.py` — new test file (created).

**Query-param note (needs a QA/Reviewer eye):**
- Ticket AC1 says `GET /projection/matchup?my_team=<team_key>`, but the ticket-029 shell (`web/templates/projection/index.html`, immutable here — Out of scope) sends the selected team as `team_key` (the `<select name="team_key">` and the auto-load `?team_key=...`; confirmed by `tests/test_projection_routes.py`). To satisfy both the immutable shell and the AC's literal URL, the route accepts **both** `team_key` and `my_team` query params and uses whichever is present (`selected = team_key or my_team`). This is the only way to make the page work end-to-end without modifying the 029 shell. If the team prefers a single param name, that is a shell (029) change and belongs in a separate ticket.

**Acceptance criteria status (self-check):**
- [x] AC1: 200 HTML fragment (no `base.html`), context line `Week {current_week} vs {opponent_name} · {week_start} – {week_end}`, three tally cards — verified by `test_matchup_context_line_and_tally_cards` (asserts no `base.html`/`<html`, the exact context line, two "Projected Wins" cards + "Tied").
- [x] AC2: category-comparison table, one row per enabled stat, per-cell winner highlighting matching `compare_projections` — verified by `test_matchup_category_table_winner_highlight` (asserts `bg-green-100` on winning cells and the projected values).
- [x] AC3: per-team roster breakdown for both teams with each player's remaining games and projected per-stat contribution — verified by `test_matchup_roster_breakdown_both_teams` (both player names, both remaining-game counts render).
- [x] AC4: bye week → 200 with "no matchup this week" message, no table — verified by `test_matchup_bye_week_message`.
- [x] AC5: rate stats 2dp, counting stats 1dp, `_is_rate_stat` drives formatting, no rate stat summed — verified by `test_matchup_rate_vs_counting_formatting` (GAA weighted rate `2.50`, projected Goals `11.0`, breakdown Goals `6.0`).
- [x] Bulk fetch: single `teams/stats` call — verified by `test_matchup_uses_single_bulk_team_stats_call` (`get_all_teams_week_stats` called exactly once). Rosters and last-30-day use the bulk functions named in the ticket (`get_players_lastmonth_stats` batches internally).

**How to verify (for QA):**
- `cd /Users/carlinleung/personal_dev/fantasy_hockey && .venv/bin/python -m pytest tests/test_projection_matchup_route.py tests/test_projection_routes.py -q` (17 pass). Full suite: `.venv/bin/python -m pytest tests/ -q` (372 pass).
- Browser (requires live Yahoo OAuth): `uvicorn web.main:app --reload`, log in, visit `/projection`. Default team's matchup auto-loads via `hx-get`; tally cards, category table, and both roster breakdowns show real numbers. Change the team in the selector — the fragment re-fetches and opponent/numbers update. If a team is on a bye, the "no matchup this week" message shows with no error. In the network tab, team stats should be a single `teams/stats;type=week` call.
- Spot-check one projected category total against the Streamlit page for the same league/week (same underlying pure functions).

**Scope notes:**
- Demo route `/demo/projection/matchup` is ticket 031. `_matchup.html` is kept free of hardcoded route URLs (it references no endpoints), so 031 can render it unchanged for demo.
- No new `data/`/`analysis/` functions were added, so no demo-counterpart gap to flag.
- `docs/improvements.md` has one open item ("Move `_is_rate_stat` import to module level in `tests/test_projection.py`") — it is on `tests/test_projection.py`, not a file in this ticket's `Touches`, so I did not touch it.

**Known limitations / things I couldn't fully test:**
- I could not perform a live browser walk (it requires real Yahoo OAuth credentials/tunnel, which are not available in this environment). Template rendering IS exercised end-to-end: the route tests go through the full FastAPI + Jinja stack and render the real `_matchup.html` with mocked data, asserting the context line, tally cards, winner-highlight classes, both roster breakdowns, the bye message, and rate/counting formatting. What I could not observe is purely visual layout in a real browser (spacing, sticky-column behaviour, wide-table horizontal scroll).
