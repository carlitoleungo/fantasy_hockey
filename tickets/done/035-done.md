## Implementation complete — 035

**What I did:**
- Removed the `my_team` query parameter and the `selected = team_key or my_team` fallback from both `projection_matchup` and `demo_projection_matchup` in `web/routes/projection.py`. `team_key` is now the sole query param on both routes; the `if not selected: RedirectResponse(...)` guard is unchanged.
- Deleted `test_matchup_my_team_alias` (asserted the now-removed alias behaviour) and added `test_matchup_my_team_alone_is_not_a_selection` to assert `?my_team=` alone now redirects to `/projection`.
- Updated `tests/test_demo_projection_routes.py`: all `?my_team=` call sites (lines that were 146, 192, 208, 209, 227) now use `?team_key=`; docstring (line 8) and inline comment (line 137) updated to reference `team_key`. Added `test_demo_projection_matchup_my_team_alone_redirects` to cover AC4 (the removed alias treated as no selection, 302 to `/demo/projection`).
- Moved the "Converge Week Projection matchup route on a single team query-param name" item from `docs/improvements.md` `## Open` to `docs/archive/improvements-closed.md` `## Closed`, with a ticket-035 resolution note.

**Files changed:**
- `web/routes/projection.py` — dropped `my_team` param + fallback from `projection_matchup` and `demo_projection_matchup`; `team_key` is the sole param on both.
- `tests/test_projection_matchup_route.py` — deleted the alias test, added a redirect-on-alias-alone test.
- `tests/test_demo_projection_routes.py` — all `?my_team=` call sites, docstring, and comment converted to `team_key`; added an alias-alone-redirects test.
- `docs/improvements.md` — removed the scoped-from item.
- `docs/archive/improvements-closed.md` — appended the closed item with a ticket-035 resolution note.

**Acceptance criteria status (self-check):**
- [x] `GET /projection/matchup?team_key=<key>` (authenticated) returns 200 and the matchup fragment — unchanged behaviour. Evidence: `tests/test_projection_matchup_route.py` full suite passes unchanged (all pre-existing `?team_key=` tests still green); ran real server, `GET /projection/matchup?team_key=...` without a session cookie 302-redirects to `/auth/login` (auth guard fires before param resolution, confirming no regression to the param-handling path — full 200 path already covered by the existing mocked test suite).
- [x] `GET /demo/projection/matchup?team_key=<key>` returns 200 with the matchup fragment and no auth required — unchanged behaviour. Evidence: ran the real app (`uvicorn`, no mocks) — `GET /demo/projection?` shell returns 200, its auto-load `hx-get` targets `?team_key=<default-team>`, and `GET /demo/projection/matchup?team_key=<key>` returns 200 with "Projected Wins" in the body.
- [x] Neither `projection_matchup` nor `demo_projection_matchup` declares a `my_team` parameter, and neither route resolves the selected team from a `my_team` query value. Evidence: `git diff web/routes/projection.py` — `my_team: str | None = None` param removed from both signatures; `selected = team_key or my_team` → `selected = team_key` in both. `grep -n "my_team" web/routes/projection.py` shows only internal variable names (`my_team_key`, `my_team_name`) inside the shared compute path, never query-param declarations.
- [x] `GET /demo/projection/matchup?my_team=<key>` (no `team_key`) redirects to `/demo/projection` (302). Evidence: ran the real app — `curl -D - "http://127.0.0.1:8811/demo/projection/matchup?my_team=<key>"` returned `HTTP/1.1 302 Found` with `location: /demo/projection`. Also covered by the new automated test `test_demo_projection_matchup_my_team_alone_redirects`.
- [x] The full test suite passes (`python3 -m pytest tests/`). Evidence: `.venv/bin/python -m pytest tests/ -q` → `392 passed, 84 warnings` (warnings are pre-existing httpx/starlette deprecation notices, unrelated to this change).

**How to verify (for QA):**
- `cd /Users/carlinleung/personal_dev/fantasy_hockey && .venv/bin/python -m pytest tests/ -q` — expect all green.
- Manual (authenticated, needs a real session): load `/projection`, pick a team from the selector; the matchup fragment loads via `?team_key=`.
- Manual (demo, no auth needed): `uvicorn web.main:app --reload`, then visit `http://127.0.0.1:8000/demo/projection` — confirm the matchup auto-loads and the team selector swaps correctly between the two demo teams (both send `?team_key=`).
- Manual (alias gone): `curl -D - "http://127.0.0.1:8000/demo/projection/matchup?my_team=<any-demo-team-key>"` (omit `team_key`) — expect `302` with `location: /demo/projection`, not a rendered matchup.
- Confirm `docs/improvements.md` no longer has the "Converge Week Projection matchup route…" item, and `docs/archive/improvements-closed.md` has it under `## Closed` with a ticket-035 note.

**Scope notes:**
- `web/templates/projection/index.html` was not touched — it already emitted `team_key` on both the `<select name="team_key">` and the auto-load `hx-get`, confirmed unchanged by `git diff --stat` showing no template in the diff.
- `_render_matchup` / `_matchup_impl` compute path untouched — confirmed by `git diff web/routes/projection.py` showing only the two route-handler signatures and their `selected = ...` lines changed.
- I noticed `tests/test_demo_projection_routes.py` still has `test_demo_projection_matchup_accepts_team_key_param`, which is now functionally near-identical to `test_demo_projection_matchup_returns_fragment` (both hit `?team_key=` and assert success) now that the alias is gone. Left it in place since the ticket didn't ask for test dedup and removing tests not specified by the ticket felt like scope creep — flagging as a minor follow-up cleanup candidate, not fixing it here.

**Improvements items closed:**
- "Converge Week Projection matchup route on a single team query-param name" (`docs/improvements.md`, Type: quality, Source: Code review 030) — moved to `docs/archive/improvements-closed.md` with a ticket-035 resolution note.

**Known limitations / things I couldn't fully test:**
- I did not exercise the authenticated `/projection` → `/projection/matchup?team_key=` path against a real Yahoo session (would require live OAuth credentials and an active league during hockey season — out of reach in this environment, consistent with the off-season gotcha in `docs/LEARNINGS.md`). Coverage for that path comes from the existing mocked `tests/test_projection_matchup_route.py` suite (unchanged except for the alias test swap) plus a live-server check that the auth guard and redirect-on-no-cookie behaviour are intact.
- Visual/browser confirmation of the demo team-selector swap (`AHO-V-O Crew` ↔ `Zellmannator`) was done via the automated `test_demo_projection_matchup_swaps_orderings` test (now using `team_key`) and the shell's rendered `hx-get` URL, not a manual click-through in an actual browser window — no browser tool was available in this environment, only `curl`/`TestClient`.
