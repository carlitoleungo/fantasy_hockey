# 035 — Converge Week Projection matchup route on a single team query-param

## Status
ready

## Type
refactor

## Process
light

## Touches
- web/routes/projection.py
- tests/test_projection_matchup_route.py
- tests/test_demo_projection_routes.py

## Why
The `/projection/matchup` and `/demo/projection/matchup` routes permanently accept
**two** query-param names for the same value (`selected = team_key or my_team`). This
dual interface exists only as a reconciliation artefact: ticket 030's AC specified
`?my_team=`, but the ticket-029 shell it depends on had already shipped
`<select name="team_key">` and an `hx-get="…?team_key=…"` auto-load. Accepting both was
the correct way to satisfy 030's AC without editing the out-of-scope 029 shell, but it
leaves the route with two names for one concept — a permanent source-of-truth ambiguity
flagged in audit 032. The shell (the only caller) already emits `team_key`, so `my_team`
is a dead alias that should be removed to leave one canonical param name.

## Acceptance criteria
- [ ] `GET /projection/matchup?team_key=<key>` (authenticated) returns 200 and the matchup fragment — unchanged behaviour.
- [ ] `GET /demo/projection/matchup?team_key=<key>` returns 200 with the matchup fragment and no auth required — unchanged behaviour.
- [ ] Neither `projection_matchup` nor `demo_projection_matchup` declares a `my_team` parameter, and neither route resolves the selected team from a `my_team` query value (the `selected = team_key or my_team` fallback is gone).
- [ ] `GET /demo/projection/matchup?my_team=<key>` (no `team_key`) redirects to `/demo/projection` (302), i.e. the removed alias is treated as "no team selected", not as a valid team.
- [ ] The full test suite passes (`python3 -m pytest tests/`).

## Out of scope
- Any change to `web/templates/projection/index.html` — the shell already emits `team_key` in both the `<select name="team_key">` control and the auto-load `hx-get`, so it is already converged. Do not edit it.
- The shared `_render_matchup` / `_matchup_impl` compute path — no compute change.
- Renaming the param to anything other than `team_key`. Converge on `team_key` (the shell's existing name), not `my_team`.

## Notes for the Engineer
- The alias lives on two handlers in `web/routes/projection.py`: `projection_matchup` (line 249, params `team_key`/`my_team`, `selected = team_key or my_team` at line 259) and `demo_projection_matchup` (line 287, same shape at line 294). Drop the `my_team` parameter and the `or my_team` fallback from both; keep the `if not selected: RedirectResponse(...)` guard.
- Two existing tests reference the alias and must be updated in the same ticket (they count as part of the diff, not scope creep):
  - `tests/test_projection_matchup_route.py:250` `test_matchup_my_team_alias` — this test asserts the alias resolves the same as `team_key`. Since the alias is being removed by design, delete this test (or convert it to assert that `?my_team=<key>` now redirects to `/projection`). Deleting is cleaner — the alias no longer exists to test.
  - `tests/test_demo_projection_routes.py` uses `?my_team=<key>` in ~5 call sites (lines 146, 192, 208, 209, 227) plus docstring/comment references (lines 8, 137). Change these to `?team_key=<key>`. These are exercising real behaviour via the alias, so they should keep testing the same behaviour via the canonical param.
- **DoD note (new this session — see audit 032 action 4):** this ticket was scoped from the `docs/improvements.md` item "Converge Week Projection matchup route on a single team query-param name" (under `## Open`). On completion, move that item to `## Closed` with a ticket-035 resolution note. This is baked into the verification below so it isn't forgotten.
- No architectural surface: this edits query-param handling inside existing handlers, not route registration in `web/main.py`, middleware, or the shell/fragment split. No Tech Lead consult required.

## Verification
- Run `python3 -m pytest tests/` — green, including the updated `test_demo_projection_routes.py`.
- Manual (authenticated): load `/projection`, pick a team from the selector; the matchup fragment loads (the auto-load `hx-get` and the select both send `team_key`).
- Manual (demo): visit `/demo/projection`, confirm the matchup auto-loads and the team selector still swaps correctly between the two demo teams.
- Manual (alias gone): `GET /demo/projection/matchup?my_team=<demo-team-key>` (no `team_key`) 302-redirects to `/demo/projection` rather than rendering a matchup.
- Confirm the `docs/improvements.md` "Converge Week Projection matchup route…" item has been moved to `## Closed` with a ticket-035 resolution note.

## Dependencies
- None (031 already shipped; the shell and both routes exist).
