# 021 — Demo mode: /overview/head-to-head

## Status
done

## Type
feature

## Touches
- web/routes/overview.py
- web/templates/overview/head_to_head.html (read-only — no change expected, but verify)

## Why
Completing demo coverage of the Overview section. After ticket 020 lands, unauthenticated visitors can see the leaderboard but still cannot use the head-to-head comparison view. `/overview/head-to-head` and its HTMX fragment endpoint both require a live session. Adding `/demo/overview/head-to-head` and `/demo/overview/head-to-head/table` closes this gap and fulfils the demo mode parity goal for the entire Overview section.

## Acceptance criteria
- [ ] `GET /demo/overview/head-to-head` returns 200 and renders the head-to-head shell with team dropdowns and week-range selectors populated from `data.demo.get_matchups()` — no Yahoo session required.
- [ ] `GET /demo/overview/head-to-head/table?team_a=X&team_b=Y&from_week=N&to_week=M` returns 200 and renders `overview/_head_to_head_table.html` with simulation results from demo data.
- [ ] No outbound Yahoo API calls are made when hitting either demo route (confirm via server logs).
- [ ] Changing team or week selection in the demo shell updates the table via HTMX (fragment fires against `/demo/overview/head-to-head/table`).
- [ ] An authenticated user visiting `/overview/head-to-head` still sees the live-data route unchanged.

## Out of scope
- Any changes to `data/demo.py` — `get_matchups()` already provides the correct data shape
- Nav links from the home or demo landing page to `/demo/overview/head-to-head`
- Demo mode for `/overview` (ticket 020, must ship first)

## Notes for the Engineer
- Follow the same `public_router` + inline demo import pattern used in ticket 020 and in `web/routes/waiver.py`.
- The authenticated shell at `web/routes/overview.py:119` (`head_to_head`) and fragment at line 177 (`head_to_head_table`) are the reference implementations. The demo versions skip `_get_league_key` and `make_session`; call `demo_module.get_matchups()` instead of the live version.
- The fragment endpoint (`/demo/overview/head-to-head/table`) accepts the same query params as the authenticated version (`team_a`, `team_b`, `from_week`, `to_week`) and passes them through `simulate()` and `tally()` from `analysis/matchup_sim.py` — no changes to the analysis layer.
- Check `head_to_head.html` for the HTMX `hx-get` target URL on the dropdowns/week selectors. If it's hard-coded rather than a context variable, add a `table_url` context variable (same pattern as waiver's `form_action`).
- The `not_enough_data` guard (line 138 in `overview.py`) should still be present: if the demo dataset has fewer than 2 teams, render the empty-state template rather than crashing.
- Decision 2026-04-19 applies: shell + fragment split; the shell renders page chrome and initial table, the fragment renders only `_head_to_head_table.html`.

## Verification
1. Complete ticket 020 first (demo leaderboard must be registered and working).
2. Start the server. Do **not** log in.
3. Visit `http://localhost:8501/demo/overview/head-to-head`. Confirm: page loads, two team dropdowns are populated with team names from the demo dataset, week-range selectors are populated, initial comparison table is rendered.
4. Change the team selection. Confirm: table updates via HTMX; server logs show `/demo/overview/head-to-head/table` request with correct params; no Yahoo API calls.
5. Log in as a real user, visit `/overview/head-to-head`. Confirm: live data loads normally.
6. While logged out, visit `/overview/head-to-head` directly. Confirm: still redirects to login.

## Dependencies
- Ticket 020 must complete first (establishes demo public_router registration pattern for the overview module)
