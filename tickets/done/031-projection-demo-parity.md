# 031 — Week Projection demo parity

## Status
done

## Type
feature

## Touches
- web/routes/projection.py
- web/main.py

## Why
Unauthenticated visitors get a demo of Overview and Waiver but would hit a dead
end on Projection. The project promises demo mode for every feature page, and
`docs/DECISIONS.md` (2026-05-30 "Web routes: demo route pairing policy") requires
a demo counterpart (or a tracked deferral) for each authenticated feature route.
The demo data already exists — `demo.get_projection_context()` and
`demo.get_projection_pair_data()` return the exact shapes the page needs — so this
is pure route plumbing that reuses the templates from 029/030.

## Acceptance criteria
- [ ] `GET /demo/projection` returns 200 with **no authentication**, rendering the same shell as `/projection` (team selector + matchup container) with league label "Demo League", and the matchup container's `hx-get` points at `/demo/projection/matchup`.
- [ ] `GET /demo/projection/matchup?my_team=<team_key>` returns 200 with no auth, rendering the tally cards, category table, and roster breakdowns from the demo dataset.
- [ ] The demo default matchup auto-loads (the container's `load` trigger fires against the demo fragment URL) and shows real projected numbers from the Week 14 demo snapshot.
- [ ] `/projection` and `/projection/matchup` still require auth (a logged-out request redirects to `/`, unchanged).

## Out of scope
- Any change to `index.html` / `_matchup.html` other than what 029/030 already parameterized. If a template still hardcodes a route URL, that is a bug to fix in the owning ticket's spirit — but this ticket should only need to pass the demo URLs as context.
- Regenerating or editing the demo JSON snapshots (`demo/data/projection_*.json`) — the demo snapshot tooling is a separate roadmap item.
- Season/last-30 toggle or any interactivity not present in the authenticated version.

## Notes for the Engineer
- Follow the demo-route pattern in `web/routes/overview.py:232-385` (`demo_overview*`) and `web/routes/waiver.py:91-111, 310-321`: define handlers on a `public_router` (no `Depends(require_user)`), and register `public_router` in `web/main.py` the way the overview/waiver public routers are registered.
- Demo data sources (both already exist, framework-free):
  - `demo.get_projection_context()` → dict with `current_week`, `stat_categories`, `teams`, `live_stats_rows`, `scoreboard` (same shape the authenticated shell/fragment assemble from the API — see `pages/04_week_projection.py:244` and `data/demo.py:116-127`).
  - `demo.get_projection_pair_data()` → `my_team_key`, `opp_team_key`, `my_roster`, `opp_roster`, `lastmonth_stats`, `games_remaining` (`data/demo.py:130-142`).
- The demo fragment computes projections with the **same** `analysis/projection.py` functions as ticket 030 — feed it the demo pair data instead of live API results. Since the demo snapshot is a single fixed matchup, resolve the pair directly from `get_projection_pair_data()` rather than the scoreboard-matching loop.
- Reuse `index.html` (029) by passing `matchup_url="/demo/projection/matchup"` and `selected_league_name="Demo League"`; reuse `_matchup.html` (030) unchanged. This is why 029/030 parameterized their URLs (ticket 025 lesson).
- This ticket **satisfies** `docs/DECISIONS.md` 2026-05-30 "demo route pairing policy" for the projection route — no backlog deferral needed since the demo counterpart ships here.
- Do not add Streamlit/demo logic into `analysis/` or `data/` — the demo accessors already exist; this is route-layer only.

## Verification
- In a logged-out browser (or incognito), visit `/demo/projection`: the shell renders with "Demo League", the default matchup auto-loads, tally cards + category table + roster breakdowns show the Week 14 snapshot numbers.
- Change the selected team in demo mode: the demo fragment re-renders (both orderings are present in the snapshot — see `pages/04_week_projection.py:249-264`).
- Confirm `/projection` (authenticated) still redirects to `/` when logged out.
- Run the route tests (`python -m pytest tests/`) — mirror the demo-route test approach from ticket 027 (`027-test-demo-overview-routes`) if adding coverage.

## Dependencies
- Ticket 030 must complete first (the demo routes reuse `index.html` and `_matchup.html` and the same compute path).
