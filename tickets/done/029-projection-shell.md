# 029 — Week Projection shell route + nav

## Status
done

## Type
feature

## Touches
- web/routes/projection.py
- web/templates/projection/index.html
- web/main.py
- web/templates/base.html

## Why
The Week Projection page is the last feature page still living only in the
Streamlit prototype (`pages/04_week_projection.py`). A fantasy manager can't yet
see, in the FastAPI app, how their current matchup is likely to end. This ticket
builds the page **shell** — the authenticated route, the team selector, and the
nav link — following the established shell-then-fragment split. It deliberately
does not compute projections; that is the fragment (ticket 030), scaffolded
separately per the "scaffold first, populate second" rule.

## Acceptance criteria
- [ ] `GET /projection` returns 200 for an authenticated session with league data, and the response HTML contains an `<h1>` titled "Week Projection".
- [ ] The response contains a team `<select>` (or radio group) populated with one option per team name from `client.get_teams`, and a matchup container element targeted by an `hx-get` to `{{ matchup_url }}` (default `/projection/matchup`) carrying the selected team.
- [ ] The matchup container issues an `hx-get` to `matchup_url` on load (`hx-trigger="load"`) with the default-selected team, so the page auto-populates once 030 lands.
- [ ] `base.html` nav shows a "Projection" link (after "Waiver") pointing to `/projection`.
- [ ] With no league data (empty matchups / pre-season), `/projection` still returns 200 and shows a friendly empty-state message instead of the selector.

## Out of scope
- The `/projection/matchup` fragment endpoint and any projection computation — that is ticket 030. The `hx-get` target may 404 until 030 lands; do not stub the computation here.
- Demo route `/demo/projection` — that is ticket 031.
- Roster breakdown tables, tally cards, category comparison — all live in the fragment (030).

## Notes for the Engineer
- Mirror the shell pattern in `web/routes/waiver.py:57-88` (`waiver_shell`) and `web/templates/waiver/index.html`: `{% extends "base.html" %}`, `hx-get`/`hx-target` for the swappable region.
- Use `require_user` + `make_session` + `_get_league_key` (import from `web.routes.common` — see ticket 028) exactly as `overview.py`/`waiver.py` do. Redirect to `/` if no league_key.
- Data for the shell: `client.get_teams(session, league_key)` for the selector. You do **not** need scoreboard/live-stats here — those belong to the fragment (030). Keep the shell's API footprint minimal.
- **Parameterize the fragment URL** as a context var (`matchup_url`) rather than hardcoding `/projection/matchup` in the template — ticket 031 will reuse this same `index.html` for `/demo/projection` by passing `/demo/projection/matchup`. This is the exact lesson from ticket 025 (parameterized overview nav links); do not hardcode.
- Register the authenticated router in `web/main.py` alongside the existing `overview`/`waiver` routers (same `include_router` pattern). The public/demo router registration is ticket 031's job.
- Conform to `docs/DECISIONS.md`: 2026-04-19 "Feature pages: HTMX fragment pattern (shell + fragment split)"; 2026-04-19 "League context: session-state propagation retained" (route stays bare `/projection`, league read from session); 2026-04-19 "Nav shell: feature links added per ticket" (ordering Overview → Waiver → Projection).
- `data/`, `analysis/`, `auth/` are framework-free — do not import Streamlit or add page logic to them; all orchestration lives in the route.

## Verification
- Log in, visit `/projection`: the header, subtitle/instructions, and a team selector render. The nav bar shows Overview / Waiver / Projection / Logout.
- View source: the matchup container has `hx-get="/projection/matchup"` (or the parameterized value) and `hx-trigger` including `load`.
- Temporarily point a browser at a pre-season / empty league (or assert via the test that empty matchups → 200 + empty-state copy).
- Demo-mode: no demo route yet (031) — confirm `/demo/projection` is still 404 after this ticket.

## Dependencies
- Ticket 028 must complete first (import `_get_league_key` from `web.routes.common`).
