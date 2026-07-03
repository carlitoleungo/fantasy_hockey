## Implementation complete — 029

**What I did:**
- Added the authenticated `GET /projection` shell route, mirroring `waiver_shell`: reads `league_key` from the session via `_get_league_key` (imported from `web.routes.common`, per ticket 028), redirects to `/` when absent, resolves the league name, and fetches the team list via `client.get_teams` for the selector. No scoreboard/live-stats fetch — that footprint belongs to the 030 fragment.
- Created `projection/index.html` shell: `<h1>Week Projection`, a `<select name="team_key">` populated one option per team (value = `team_key`, label = `team_name`, first option `selected`), and a `#projection-matchup` container. The select drives the container via `hx-get="{{ matchup_url }}"` + `hx-target="#projection-matchup"` + `hx-trigger="change"`; the container auto-populates with `hx-trigger="load"` and `hx-get="{{ matchup_url }}?team_key=<first team>"`.
- Parameterized the fragment URL as the `matchup_url` context var (default `/projection/matchup`) — not hardcoded in the template — so ticket 031 can reuse this same `index.html` for `/demo/projection`.
- Empty-state: when `get_teams` returns an empty list, the shell renders a friendly "season may not have started" message and no selector.
- Registered `projection_router` in `web/main.py` (after the waiver routers) and added the "Projection" nav link in `base.html`, positioned after "Waiver" (ordering Overview → Waiver → Projection).
- Added `tests/test_projection_routes.py` covering all five ACs plus the two session guards (no-league redirect, no-cookie redirect).

**Files changed:**
- `web/routes/projection.py` (new) — `GET /projection` shell route.
- `web/templates/projection/index.html` (new) — shell template with team selector + HTMX matchup container.
- `web/main.py` — import and `include_router(projection_router)`.
- `web/templates/base.html` — "Projection" nav link after "Waiver".
- `tests/test_projection_routes.py` (new) — AC + guard coverage.

**Acceptance criteria status (self-check):**
- [x] AC1: `GET /projection` returns 200 for an authenticated session with league data, HTML contains `<h1>` "Week Projection" — verified by `test_projection_shell_returns_200_with_header` (passing).
- [x] AC2: response contains a team `<select>` with one option per team from `get_teams`, and a matchup container targeted by `hx-get` to `{{ matchup_url }}` carrying the selected team — verified by `test_projection_shell_has_team_select_and_matchup_target` (passing). The selected team is carried as `name="team_key"` on the select (value = `team_key`).
- [x] AC3: matchup container issues `hx-get` to `matchup_url` on load (`hx-trigger="load"`) with the default-selected (first) team — verified by `test_projection_matchup_container_loads_default_team` (passing); asserts `hx-get="/projection/matchup?team_key=<first>"` and `hx-trigger="load"`.
- [x] AC4: `base.html` nav shows a "Projection" link after "Waiver" pointing to `/projection` — verified by `test_projection_nav_link_present_and_after_waiver` (passing; asserts the Waiver link's index precedes the Projection link's).
- [x] AC5: with no league data (empty `get_teams`), `/projection` returns 200 and shows the empty-state message instead of the selector — verified by `test_projection_empty_league_shows_empty_state` (passing; asserts empty-state copy present and `<select` absent).

**How to verify (for QA):**
- `.venv/bin/python -m pytest tests/test_projection_routes.py -q` — 7 tests, all pass.
- Full suite: `.venv/bin/python -m pytest tests/ -q` — 362 pass, no regressions from the `main.py`/`base.html` edits.
- `/demo/projection` still 404 (confirmed via TestClient) — the demo route is ticket 031.
- Manual browser walk (uvicorn): log in, visit `/projection` — header, subtitle/instructions, and team selector render; nav shows Overview / Waiver / Projection / Logout. View source: `#projection-matchup` has `hx-get="/projection/matchup?team_key=..."` and `hx-trigger="load"`. The `hx-get` target will 404 until 030 lands — that is expected per the ticket.

**Interpretation note (empty-state trigger):**
- The ticket says the shell's only data fetch is `get_teams`, and AC5 describes the trigger as "empty matchups / pre-season." Since the shell does not fetch matchups (per "Keep the shell's API footprint minimal"), I keyed the empty-state off `get_teams` returning an empty list. This is the single-API-call reading the ticket directs; the fragment (030) owns matchup/scoreboard emptiness. Flagging explicitly in case QA expected a `get_matchups`-based check.

**Contract for ticket 030 (fragment):**
- The selected team is sent to the fragment as query param `team_key` (option `value` is `team_key`, not the display name). The fragment resolves the opponent from the scoreboard by `team_key` — matching the Streamlit `pages/04_week_projection.py` logic. If 030 prefers `team_name`, it must adjust the select's option `value`.

**Scope notes:**
- `docs/improvements.md` has an open `Type: quality` item ("Nav header shows auth links to unauthenticated visitors", on `base.html` lines 22–24). Its prescribed fix requires passing an `is_authenticated` var from *every* route context (`home.py`, `overview.py`, `waiver.py`, `projection.py`) — files outside this ticket's `Touches` list. I could not close it cleanly within scope (a base.html-only change has no such variable to read and would break authenticated nav), so I left it open. It should get a dedicated ticket. My new "Projection" link inherits the same behaviour as the existing Overview/Waiver links, so this ticket does not worsen the item.

**Known limitations / things I couldn't fully test:**
- I verified rendering through the FastAPI TestClient (which exercises the full Jinja template path and asserts the emitted HTML), not through a live browser session — no browser automation is available in this environment. The HTMX attributes are asserted as literal strings in the response body; actual HTMX swap behaviour (the `load`/`change` fetch firing) is a browser-runtime behaviour that will only be observable once the 030 fragment endpoint exists.
