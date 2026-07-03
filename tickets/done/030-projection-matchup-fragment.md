# 030 — Week Projection matchup fragment (compute + render)

## Status
done

## Type
feature

## Touches
- web/routes/projection.py
- web/templates/projection/_matchup.html

## Why
The shell (029) renders a team selector but no numbers. This ticket builds the
data-intensive fragment that makes the page useful: given a selected team, it
resolves the opponent from the live scoreboard, fetches both rosters, their
last-30-day rates, and remaining NHL games, then renders the projected final
matchup — the whole reason the page exists. This is the direct port of the
compute-and-render half of `pages/04_week_projection.py`.

## Acceptance criteria
- [ ] `GET /projection/matchup?my_team=<team_key>` returns 200 (HTML fragment, no `base.html`) for an authenticated session and renders a matchup context line — `Week {current_week} vs {opponent_name} · {week_start} – {week_end}` — and three tally cards showing projected category wins for my team, ties, and the opponent.
- [ ] The fragment renders a category-comparison table with one row per enabled stat and per-cell winner highlighting (win/lose/tie), matching `compare_projections` output.
- [ ] The fragment renders a per-team roster breakdown (both teams) listing each player's remaining games and projected per-stat contribution.
- [ ] If the selected team has no matchup this week (bye), the fragment returns 200 with a "no matchup this week" message instead of a table.
- [ ] Rate stats (GAA, SV%) display as per-game rates (2dp) and counting stats as totals (1dp), i.e. `_is_rate_stat` drives formatting — no rate stat is summed.

## Out of scope
- Any change to `index.html` or the shell route (029 owns those).
- Demo route `/demo/projection/matchup` — that is ticket 031 (but keep this fragment's template demo-reusable; see notes).
- A "Refresh" button / cache-busting UX — the Streamlit refresh button clears session state, which has no analog in the stateless HTMX request; each fragment request already fetches live. Do not port it.
- New data or analysis functions — everything needed already exists.

## Notes for the Engineer
- This request is stateless (like the waiver POST handler `_waiver_post_impl`). Fetch what you need per request; do not rely on shell state:
  - `client.get_settings_and_categories(session, league_key)` → `current_week` + `stat_categories`.
  - `scoreboard.get_current_matchup(session, league_key, current_week)` → resolve opponent: loop `scoreboard["matchups"]`, match `team_a_key`/`team_b_key` against `my_team` (see `pages/04_week_projection.py:352-369`). Also gives `week_start`/`week_end`.
  - `client.get_all_teams_week_stats(session, league_key, current_week, stat_categories)` → live week-to-date per team (**one bulk call for all teams — never per-team**, per `docs/LEARNINGS.md` "Bulk endpoints over per-entity loops").
  - `roster.get_team_roster(session, team_key, date=date.today().isoformat())` for **each** of the two teams (today's date excludes dropped players — see `pages/04_week_projection.py:396-398`).
  - `players.get_players_lastmonth_stats(session, league_key, all_player_keys)` → `{player_key: {stat_name: float, games_played: int}}` for both rosters at once (batches of 25 internally — bulk, not per-player).
  - `schedule.get_remaining_games(all_abbrs, from_date, week_end)` where `from_date = max(date.today(), week_start)` (see `pages/04_week_projection.py:407-409`).
- Compute with the existing pure functions: `project_team_stats`, `compare_projections`, `_is_rate_stat` from `analysis/projection.py`; `lower_is_better_from_categories` from `analysis/team_scores.py`; `tally` from `analysis/matchup_sim.py`. `compare_projections` returns `winner` as `"team_a"/"team_b"/"Tie"` — map to team names for `tally` exactly as `pages/04_week_projection.py:457-469`.
- Roster-breakdown per-player math is `pages/04_week_projection.py:504-527`: counting stat → `lastmonth / games_played * remaining`; rate stat → show the lastmonth rate directly; guard `games_played == 0`.
- This endpoint returns a bare HTML fragment (no `base.html`), per `docs/DECISIONS.md` 2026-05-30 "Feature pages: HTMX fragment pattern with shell + fragment template split": the shell (029) is `projection/index.html`; `_matchup.html` is the fragment it swaps in via `hx-get`.
- Templating: rank/format → CSS class mapping lives in the **template**, not analysis (`docs/DECISIONS.md` 2026-04-19 "rank → Tailwind class mapping lives in templates"). Use Tailwind utility classes (the Streamlit `_TABLE_CSS` shadow-DOM block does **not** port — the FastAPI app uses Tailwind via base.html). Roster-breakdown tabs may be an Alpine `x-data` toggle or two stacked tables — engineer's choice within the stack.
- Keep `_matchup.html` free of any hardcoded route URLs so ticket 031 can render it unchanged for demo.
- Yahoo gotchas from `docs/LEARNINGS.md` that apply here: GAA (`stat_id==23`) is recomputed for lastmonth inside `players.py` already — do not recompute again; `stat_id==0` is games-played, not a category; enabled-only via `is_enabled`. These are handled by the existing functions — just don't undo them.
- Conform to `docs/DECISIONS.md` 2026-05-30 "Waiver and projection routes: per-stat bulk fetch, never per-player" — the per-player loop anti-pattern is explicitly prohibited; the bulk functions above satisfy this.

## Verification
- Log in, visit `/projection`, let the default team's matchup auto-load: tally cards, category table, and both roster breakdowns render with real numbers.
- Change the selected team: the fragment re-fetches and the opponent/numbers update.
- Pick a team on a bye week (if available): the "no matchup this week" message shows, no error.
- Spot-check one category against the Streamlit page for the same league/week — projected totals should match (same underlying functions).
- Confirm in the network tab that team stats come from a single `teams/stats` call, not N per-team calls.

## Dependencies
- Ticket 029 must complete first (the shell renders the selector and targets this endpoint via `matchup_url`).
