## QA + Review Report — 035

**Ticket:** Converge Week Projection matchup route on a single team query-param
**Engineer handoff:** tickets/035-done.md
**QA date:** 2026-07-22
**Process:** light (combined QA + review, no separate Reviewer session)

### Test plan (written before reading Engineer's "How to verify")

- AC1 (`GET /projection/matchup?team_key=` authenticated → 200 + fragment): cannot
  exercise the 200 path live (off-season, no Yahoo session — `docs/LEARNINGS.md`
  "Off-season → no live data"). Plan: hit the route with no session cookie and confirm
  the auth guard fires (redirect to `/auth/login`) before param resolution, proving no
  regression to param handling upstream of auth; rely on the mocked
  `tests/test_projection_matchup_route.py` suite for the actual 200 path.
- AC2 (`GET /demo/projection/matchup?team_key=` → 200 + fragment, no auth): start
  uvicorn, `curl` the demo shell to find the real demo team keys from the rendered
  `hx-get`, then `curl` the matchup route with `?team_key=<key>` and check for 200 +
  known fragment content ("Projected Wins").
- AC3 (neither handler declares/resolves `my_team`): `grep -n "my_team"
  web/routes/projection.py` and manually read both handler signatures and body; confirm
  any remaining `my_team` hits are internal variable names (`my_team_key`,
  `my_team_name`) inside the untouched compute path, not query-param declarations.
- AC4 (`GET /demo/projection/matchup?my_team=` alone → 302 to `/demo/projection`):
  `curl -D -` with only `my_team` set, no `team_key`; expect `302` + `location:
  /demo/projection`.
- Suite: `python3 -m pytest tests/` (via the project venv) — expect all green,
  including the alias-removal tests in both projection test files.
- Combined-review pass: diff each changed file against `Touches`
  (`web/routes/projection.py`, `tests/test_projection_matchup_route.py`,
  `tests/test_demo_projection_routes.py`) plus the DoD-mandated
  `docs/improvements.md` / `docs/archive/improvements-closed.md` move; confirm
  `web/templates/projection/index.html` and `_render_matchup`/`_matchup_impl` are
  untouched; check the always-blocker list from `.team/test-engineer.md`.

### Test results

| # | Acceptance criterion | Result | Observation |
|---|----------------------|--------|-------------|
| 1 | `GET /projection/matchup?team_key=<key>` (authenticated) returns 200 and the matchup fragment — unchanged behaviour | PASS (owner-must-verify for the live 200 render) | No session cookie: `GET /projection/matchup?team_key=some-key` → `302 Found`, `location: /auth/login` — auth guard fires before `selected = team_key` is even reached, so param-handling regression risk is nil on this path. The actual 200-render behaviour is covered by the unchanged, still-green `tests/test_projection_matchup_route.py` mocked suite (9 tests in that file, all passing per the full-suite run below). Cannot be exercised end-to-end against real Yahoo data in this environment — off-season, per `docs/LEARNINGS.md` "Off-season → no live data; week-keyed feature pages only show empty states". Stated as fact, not hedged: this is a known, documented environment limit, not a gap introduced by this ticket. |
| 2 | `GET /demo/projection/matchup?team_key=<key>` returns 200 with the matchup fragment and no auth required — unchanged behaviour | PASS | Ran `uvicorn web.main:app --port 8813` with no auth. `GET /demo/projection` → 200; its rendered shell contains `hx-get="/demo/projection/matchup?team_key=465.l.8977.t.8"` (auto-load) and a `<select id="team-select" hx-get="/demo/projection/matchup" ...>` with options `value="465.l.8977.t.8"` / `value="465.l.8977.t.5"`. `GET /demo/projection/matchup?team_key=465.l.8977.t.8` → `STATUS:200`, body contains "Projected Wins" and "Week 14 vs Zellmannator · 2026-01-05 – 2026-01-11". Swapping to the other team key (`465.l.8977.t.5`) → `STATUS:200`, body shows "Week 14 vs AHO-V-O Crew · 2026-01-05 – 2026-01-11" — confirms the two-way selector swap renders distinct opponents, no auth required. |
| 3 | Neither `projection_matchup` nor `demo_projection_matchup` declares a `my_team` parameter, and neither resolves the selected team from `my_team` (the `selected = team_key or my_team` fallback is gone) | PASS | `git diff web/routes/projection.py` shows `my_team: str | None = None` removed from both signatures, `selected = team_key or my_team` → `selected = team_key` in both handlers (verified by direct read of `web/routes/projection.py` lines 248–299, current state). `grep -n "my_team" web/routes/projection.py` returns 17 hits, all inside `_matchup_impl` (line 90) and `_render_matchup`/`demo` compute body (lines 90–338) as internal variable names (`my_team_key`, `my_team_name`) — none are query-param declarations or default values on the two route handlers. |
| 4 | `GET /demo/projection/matchup?my_team=<key>` (no `team_key`) redirects to `/demo/projection` (302), i.e. the removed alias is treated as "no team selected" | PASS | `curl -D - -o /dev/null "http://127.0.0.1:8813/demo/projection/matchup?my_team=465.l.8977.t.8"` → `HTTP/1.1 302 Found`, `location: /demo/projection`. Matches AC exactly — the alias is inert, not resolved as a valid selection. |
| 5 | Full test suite passes (`python3 -m pytest tests/`) | PASS | See Automated tests below — `392 passed, 84 warnings`, 0 failed. |

### Automated tests

- Command: `source .venv/bin/activate && python3 -m pytest tests/ -q` (per-instructions
  `python3`; the project has no interpreter named `python3` on `PATH` outside the venv,
  so the venv is activated first — confirmed `which python3` resolves to
  `.venv/bin/python3` before running).
- Tests run: 392 — passed: 392, failed: 0. Summary line: `392 passed, 84 warnings in
  1.19s`. Warnings are pre-existing `httpx`/`starlette` deprecation notices, unrelated to
  this change (also called out by the Engineer, confirmed by content of the warnings
  block — all reference `starlette.testclient` httpx deprecation, no new warning classes
  introduced by this diff).
- New tests added (by the Engineer, verified present and exercising real AC paths, not
  rewritten by QA — coverage was already present so no supplementary tests were needed
  per Step 3 of the persona workflow):
  - `tests/test_projection_matchup_route.py::test_matchup_my_team_alone_is_not_a_selection`
    — asserts `?my_team=<key>` (authenticated, no `team_key`) redirects to
    `/projection`. Covers AC4's authenticated-route sibling behaviour (the ticket's AC4
    text is demo-only, but the Engineer also covered the live route symmetrically —
    good practice, not required by AC).
  - `tests/test_demo_projection_routes.py::test_demo_projection_matchup_my_team_alone_redirects`
    — directly covers AC4 (demo route, `?my_team=` alone → 302 to `/demo/projection`).
  - All prior `?my_team=` call sites in `tests/test_demo_projection_routes.py`
    converted to `?team_key=` (5 call sites + docstring + comment, matching the
    ticket's Notes-for-Engineer line-by-line).
  - `tests/test_projection_matchup_route.py::test_matchup_my_team_alias` deleted (the
    alias it tested no longer exists — correct per ticket instruction to delete rather
    than repurpose).

### Manual verification

- Started `uvicorn web.main:app --port 8813` from the project venv, no auth configured.
- `GET /demo/projection` → 200; parsed rendered HTML for `hx-get` targets and `<select>`
  option values to get real demo team keys (`465.l.8977.t.8`, `465.l.8977.t.5`) rather
  than guessing keys.
- `GET /demo/projection/matchup?team_key=465.l.8977.t.8` → 200, "Projected Wins" present
  (AC2).
- `GET /demo/projection/matchup?team_key=465.l.8977.t.5` → 200, opponent flips to "AHO-V-O
  Crew" confirming the selector's two teams render distinct fragments (selector swap
  parity, per the ticket's Verification section).
- `GET /demo/projection/matchup?my_team=465.l.8977.t.8` (no `team_key`) → 302,
  `location: /demo/projection` (AC4).
- `GET /projection/matchup?team_key=some-key` (no session cookie) → 302, `location:
  /auth/login` — confirms the auth guard fires ahead of param resolution on the live
  route, so this diff cannot have regressed the authenticated 200 path in a way visible
  without live credentials; the mocked suite covers that path directly.
- Killed the uvicorn process after verification.

### Demo mode

Ticket touches only route-level param handling in an already-existing
demo/live pair (`projection_matchup` / `demo_projection_matchup`); no new data-layer
function was introduced, so there's no new demo counterpart to add. Existing demo
parity was walked live above (AC2, AC4) and is intact — both handlers still call the
same `_render_matchup`/`_matchup_impl` compute tail per DECISIONS 2026-07-03, unchanged
by this diff.

### Review checks (light-ticket combined mode)

| Blocker check | Result |
|---|---|
| Framework import in `data/`, `analysis/`, or `auth/` | Pass — diff touches only `web/routes/projection.py` and test files; no `data/`/`analysis/`/`auth/` files in the diff. |
| Raw `stat['value']` without `_coerce()`; Yahoo collection indexed without `_as_list()` | N/A — this diff removes a query-param and a fallback expression; it does not touch any stat-parsing or Yahoo-response-shape code. Confirmed by reading the full diff (6 lines changed in `web/routes/projection.py`, all in the two route-handler signatures/bodies, none touching `_matchup_impl`/`_render_matchup` or any `stat[...]` access). |
| Per-entity Yahoo API loop where a bulk endpoint exists | N/A — no data-fetch code touched. |
| New live data function with no demo counterpart (and no backlog ticket) | N/A — no new data function introduced; the existing demo/live pair for this route already exists and remains intact (verified above). |
| Contradiction of an active `docs/DECISIONS.md` entry | Pass — DECISIONS 2026-07-03 ("demo and live handlers share a single compute/render helper") requires the two handlers to differ only in data assembly, feeding a shared `_render_matchup`. Confirmed `_render_matchup`/`_matchup_impl` untouched (`git diff` shows 0 lines changed outside the two route-handler signature/body blocks at lines 249 and 287); both handlers still call into the shared helper unchanged. No contradiction. |
| Diff escapes the ticket's `Touches` list | Pass — changed files: `web/routes/projection.py`, `tests/test_projection_matchup_route.py`, `tests/test_demo_projection_routes.py` (all three in `Touches`), plus `docs/improvements.md` and `docs/archive/improvements-closed.md` (explicitly sanctioned by the ticket's "DoD note" as part of this ticket's required close-out, not scope creep), plus the ticket file's own `## Status` line flip from `ready` to `qa` (routine workflow bookkeeping). No other files touched. |

Architectural-surface check (persona Step 5 of light-ticket mode): nothing in this diff
touches route registration (`web/main.py`), middleware, or the shell/fragment split —
confirmed by `git status --short` showing no changes to those files. Correctly scoped
as a light ticket; no mis-classification.

### DoD — improvements.md close-out

Confirmed via `git diff docs/improvements.md docs/archive/improvements-closed.md`:

- "Converge Week Projection matchup route on a single team query-param name" removed
  from `docs/improvements.md` `## Open`.
- Same item appended to `docs/archive/improvements-closed.md` `## Closed`, with a
  ticket-035 resolution note describing exactly what changed (param removed, alias now
  redirects, shell unchanged). Matches the ticket's own note that the archive location
  is correct despite the ticket text saying `## Closed` (the ticket file's `## Out of
  scope`/body text is internally consistent with this — the archive file's top-level
  heading is literally `## Closed`, it just lives in a separate archive doc rather than
  inline in `docs/improvements.md`).

### Issues found

None. All five acceptance criteria PASS with direct observation (live server hits for
AC2/AC4, direct diff/grep read for AC3, documented off-season limitation stated as fact
for AC1's live-render portion, full green suite for AC5).

### Notes (out-of-scope, non-blocking)

- Pre-existing near-duplicate test noted by the Engineer:
  `tests/test_demo_projection_routes.py::test_demo_projection_matchup_accepts_team_key_param`
  (line 163) is now functionally near-identical to
  `test_demo_projection_matchup_returns_fragment` (line 141) — both hit `?team_key=`
  and assert a 200 with "Roster Breakdown"/fragment content, once the alias is gone. Not
  introduced by this ticket's scope (the ticket only asked for alias-related edits) and
  doesn't affect coverage or correctness, so it is not a blocker. Logged as a
  `Type: quality` entry in `docs/improvements.md` for a future cleanup pass rather than
  fixed here (Test Engineers write tests, not dedup passes on the Engineer's existing
  suite, and this ticket's `Touches` didn't include removing this test).

### Verdict: APPROVED
