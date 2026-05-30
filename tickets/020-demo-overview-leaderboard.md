# 020 — Demo mode: /overview leaderboard

## Status
ready

## Type
feature

## Touches
- web/routes/overview.py
- web/templates/overview/index.html (read-only — no change expected, but verify)

## Why
Unauthenticated visitors in demo mode can explore the waiver wire but cannot see the league leaderboard. `/overview` requires a live session and redirects unauthenticated users to login. The project's stated goal is "a demo mode lets unauthenticated users explore a pre-snapshotted dataset" — that goal is unmet for the Overview section. Adding `/demo/overview` closes the most visible gap: the leaderboard is the first page a visitor would want to see after the home screen.

## Acceptance criteria
- [ ] `GET /demo/overview` returns 200 and renders the leaderboard shell with week selector and stat table populated from `data.demo.get_matchups()` data — no Yahoo session required.
- [ ] `GET /demo/overview/table?week=N` returns 200 and renders `overview/_table.html` fragment populated from demo data for the requested week.
- [ ] No outbound Yahoo API calls are made when hitting either demo route (confirm via server logs).
- [ ] Navigating to `/demo/overview` and changing the week selector updates the table via HTMX (the fragment swap fires against `/demo/overview/table`).
- [ ] An authenticated user visiting `/overview` still sees the live-data route unchanged.

## Out of scope
- Demo mode for `/overview/head-to-head` (ticket 021)
- Any changes to `data/demo.py` — `get_matchups()` already exists and returns the correct shape
- Adding a nav link to `/demo/overview` from the home or demo landing page (separate UI ticket if desired)

## Notes for the Engineer
- Follow the pattern in `web/routes/waiver.py` lines 91–109 (`demo_waiver_shell`) and lines 310–320 (`demo_waiver_players`): use a `public_router` (no `require_user` dependency) and import demo module inline with `from data import demo as demo_module`.
- The authenticated shell at `web/routes/overview.py:34` is the reference implementation. The demo version is identical except: skip `_get_league_key`, skip `make_session`, call `demo_module.get_matchups()` instead of `get_matchups(session, league_key)`, and omit `selected_league_name` (or hardcode `"Demo League"`).
- The fragment route (`/demo/overview/table?week=N`) mirrors `/overview/table` (line 84) — same logic, same template (`overview/_table.html`), just sourced from demo data.
- The `overview/index.html` template renders a week selector whose HTMX `hx-get` target must point at `/demo/overview/table` in demo mode. Check the template; if the action URL is hard-coded rather than passed as a context variable, add a `table_url` context variable (follow the `form_action` pattern in the waiver shell).
- Decision 2026-04-19 (HTMX shell + fragment split): the shell renders the page chrome and the initial table; the fragment endpoint renders only `_table.html` for subsequent week-change swaps.
- `data.demo.get_matchups()` returns a DataFrame with `week`, `team_name`, and stat columns — same shape as the live `get_matchups()` return. Pass it through `weekly_scores_ranked` and `stat_columns` from `analysis/team_scores.py` exactly as the authenticated route does.
- Register `public_router` in `web/main.py` if it isn't already (check how the waiver demo routes are registered).

## Verification
1. Start the server (`uvicorn web.main:app --reload`). Do **not** log in.
2. Visit `http://localhost:8501/demo/overview`. Confirm: page loads, leaderboard table is populated with team names and stat values, week selector is present.
3. Change the week in the selector. Confirm: table updates via HTMX without a full page reload; server logs show a request to `/demo/overview/table?week=N` and no Yahoo API calls.
4. Log in as a real user, visit `/overview`. Confirm: live data still loads normally.
5. While logged out, visit `/overview` directly. Confirm: still redirects to login (authenticated route unchanged).

## Dependencies
- None
