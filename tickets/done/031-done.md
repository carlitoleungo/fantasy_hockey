## Implementation complete — 031

**What I did:**
- Added a `public_router` (no `Depends(require_user)`) to `web/routes/projection.py` with two demo handlers: `GET /demo/projection` (shell) and `GET /demo/projection/matchup` (fragment), mirroring the `demo_overview*` / `demo_waiver*` pattern.
- Extracted the compute + render tail of `_matchup_impl` into a shared `_render_matchup(...)` helper so the live and demo paths run identical projection/tally/breakdown logic; the only difference is how each path assembles rosters, last-30 stats, games-remaining, and live week-to-date. `_matchup_impl` behaviour is unchanged (it now calls the helper).
- The demo shell reuses `projection/index.html` with `matchup_url="/demo/projection/matchup"` and `selected_league_name="Demo League"`; the demo fragment reuses `projection/_matchup.html` unchanged. No template edits.
- The demo fragment resolves the matchup pair directly from `demo.get_projection_pair_data()` (no scoreboard-matching loop), and swaps `my`/`opp` rosters when the opponent team is the selected side so breakdowns stay correct in both orderings.
- Registered `projection_public_router` in `web/main.py` alongside the overview/waiver public routers.
- Added `tests/test_demo_projection_routes.py` (new file) covering all four ACs, mirroring the ticket-027 demo-route test approach (patch `data.demo.*` accessors, assert with `TestClient`).

**Files changed:**
- `web/routes/projection.py` — added `public_router` + two demo handlers; extracted `_render_matchup` shared helper from `_matchup_impl`.
- `web/main.py` — imported and registered `projection_public_router`.
- `tests/test_demo_projection_routes.py` — new test file for the four ACs (new code paths require coverage per the Engineer persona).

**Acceptance criteria status (self-check):**
- [x] AC1: `GET /demo/projection` returns 200 with no auth, renders the same shell (team selector + matchup container) with "Demo League" and the container's `hx-get` pointing at `/demo/projection/matchup`. — Verified: end-to-end smoke test (status 200, "Demo League" present, `hx-get="/demo/projection/matchup"` present, authenticated `/projection/matchup` string absent) and `test_demo_projection_shell_renders_demo_shell`.
- [x] AC2: `GET /demo/projection/matchup?my_team=<team_key>` returns 200 with no auth, rendering tally cards, category table, and roster breakdowns from the demo dataset. — Verified: `test_demo_projection_matchup_returns_fragment` (bare fragment, "Projected Wins", "(Proj)" headers, "Roster Breakdown", both players) and smoke test.
- [x] AC3: The demo default matchup auto-loads (`load` trigger against the demo fragment URL) and shows real projected numbers from the Week 14 demo snapshot. — Verified: `test_demo_projection_shell_autoloads_default_team` (`hx-trigger="load"`, `hx-get="/demo/projection/matchup?team_key=465.l.8977.t.8"`); smoke test against the real committed JSON returned my_wins=9 / ties=0 / opp_wins=5 across 14 categories with non-zero per-category projected values.
- [x] AC4: `/projection` and `/projection/matchup` still require auth (logged-out request redirects to `/`, unchanged). — Verified: `test_authenticated_projection_still_requires_auth` and `test_authenticated_projection_matchup_still_requires_auth` (both 302 → `/auth/login`, unchanged from prior behaviour). Note: the redirect target for a logged-out request is `/auth/login` (via the `RequiresLogin` handler in `web/main.py`), not literally `/`; the ticket's parenthetical "redirects to `/`" describes the no-league case. The AC's substantive requirement — auth still enforced, behaviour unchanged — holds.

**How to verify (for QA):**
- Run `python3 -m pytest tests/` (this env: `.venv/bin/python -m pytest tests/`). Full suite: 385 passed. The 11 new tests are in `tests/test_demo_projection_routes.py`.
- Logged-out browser (or `TestClient`, no cookie): `GET /demo/projection` → 200, shell shows "Demo League", team selector with both demo teams, and the `#projection-matchup` container auto-loads `/demo/projection/matchup?team_key=465.l.8977.t.8` on `load`.
- `GET /demo/projection/matchup?team_key=465.l.8977.t.8` → 200 bare fragment with tally cards (9/0/5), the category comparison table, and both roster breakdowns from the Week 14 snapshot.
- Switch the selected team to the opponent (`?team_key=465.l.8977.t.5`) → the roster breakdown ordering swaps (opponent's roster leads the first table).
- `GET /projection` and `GET /projection/matchup` with no cookie → 302 to `/auth/login`.

**Scope notes:**
- Pre-existing quality item in `docs/improvements.md` ("Converge Week Projection matchup route on a single team query-param name", Source: Code review 030) lives on `web/routes/projection.py`. I did **not** close it: its own fix text requires converging the shell's param name in `web/templates/projection/index.html`, which is outside this ticket's `Touches` and explicitly out of scope (029/030 template parameterization only). The new demo fragment route accepts both `team_key` and `my_team` to match the existing live route's interface; a future shell ticket should converge both routes on one name and remove the alias. Left the improvements item open for that follow-up.
- No `docs/`, `data/`, `analysis/`, or template files were modified. No new dependencies, env vars, or config knobs. This ticket satisfies `docs/DECISIONS.md` 2026-05-30 "demo route pairing policy" for the projection route (demo counterpart ships here — no backlog deferral).

**Known limitations / things I couldn't fully test:**
- Route/compute correctness is covered by automated tests plus a scripted end-to-end run through the real committed demo JSON via `TestClient`. I did not open a live browser (no rendering/CSS/HTMX-swap visual check) — the HTMX attributes (`hx-get`, `hx-trigger="load"`, `hx-target`) are asserted in the rendered HTML but the actual client-side swap in a browser is a visual check QA should confirm.
