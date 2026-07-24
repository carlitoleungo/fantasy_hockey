## Implementation complete — 034

**Option chosen: A — two tables per team ("Skaters" / "Goalies"), each showing only its own columns.**
Rationale: it is the only option that satisfies AC1 by *construction* rather than by
formatting — a goalie-only column is physically absent from the skater table, so there is
no `0.00` filler cell to blank and no way for a future edit to reintroduce one. It also
does the most for the width complaint in the ticket's Why: against the real demo snapshot
the skater table drops from 17 columns to 12 and the goalie table to 6, on top of the
name abbreviation. Option B would have kept one 17-column table (no width win); Option C
(Alpine tabs) hides half the data behind a click and adds client-side state to a fragment
that currently needs none.

**What I did:**
- `_player_breakdown` now tags each row with `is_goalie` (`"G" in display_position.split(",")`),
  the data-driven partition the ticket specified. No change to any stat value it computes.
- `_render_matchup` (the shared live+demo helper) derives the breakdown columns from
  `stat_categories`: `skater_columns` = enabled categories whose `stat_group != "goaltending"`,
  `goalie_columns` = the rest. Each column is `{"name", "abbr", "group"}` — `name` still keys
  `p.stats[...]` (so `_player_breakdown`'s output shape is untouched) and `abbr` is the Yahoo
  `abbreviation`. Building this inside the shared helper is what guarantees AC4: both
  `_matchup_impl` and `demo_projection_matchup` reach it, and neither handler needed a new
  argument.
- Replaced the template's `enabled_stats` context var (now unused) with `skater_columns` /
  `goalie_columns`.
- `_matchup.html`: `roster_table(rows, columns)` now takes its columns as a parameter, and a new
  `team_breakdown(rows)` macro splits the rows with `rejectattr("is_goalie")` /
  `selectattr("is_goalie")` and renders a "Skaters" table and a "Goalies" table per team. A
  section is omitted entirely when it has no players (skater-only team → no Goalies table).
- Headers now render `c.abbr` (`G`, `A`, `P`, `SOG`, `GAA`, `SV%`…) with the full stat name in
  `title=`; `GR` gained a `title="Games Remaining"`.
- Player names render first-initial + surname (`Connor McDavid` → `C. McDavid`) via Jinja
  `split(' ', 1)`, with the full name in `title=` on the name cell. Single-token names fall
  through unabbreviated.
- The fragment stays a bare fragment (no `base.html`, no hardcoded route URLs) — asserted by
  the existing tests and re-confirmed against the running app.

**Files changed:**
- `web/routes/projection.py` — `is_goalie` on each breakdown row; `skater_columns` /
  `goalie_columns` built in the shared `_render_matchup`; `enabled_stats` dropped from the
  template context.
- `web/templates/projection/_matchup.html` — roster breakdown split into Skaters/Goalies tables,
  abbreviated headers, abbreviated player names with full-name tooltips. Tally cards and
  category-comparison table untouched.
- `tests/test_projection_matchup_route.py` — corrected the `stat_group` fixture values to the real
  Yahoo ones (`offense` / `goaltending`; they said `skaters` / `goalies`, which no longer matches
  what the route partitions on); `_patched()` gained `rosters` / `lastmonth` overrides; added six
  ticket-034 tests.
- `tests/test_projection_matchup_qa.py` — same `stat_group` fixture correction (`skaters` → `offense`).
- `tests/test_demo_projection_routes.py` — added two demo-parity tests for the split + abbreviations
  (AC4); removed the duplicate test flagged in `docs/improvements.md`.
- `docs/improvements.md` / `docs/archive/improvements-closed.md` — closed the near-duplicate-demo-test
  quality item (see below).

**Acceptance criteria status (self-check):**
- [x] **AC1 — goalie stats visually separated; no `0.00` filler on skater rows.** Evidence: drove the
  running app (`uvicorn`, port 8836) at `GET /demo/projection/matchup?team_key=465.l.8977.t.8` against
  the real Week 14 snapshot and parsed the response. Sections rendered in order
  `['Skaters', 'Goalies', 'Skaters', 'Goalies']` (both teams). Skater table headers:
  `Player, GR, G, A, P, +/-, PIM, PPP, SOG, FW, HIT, BLK` — no `W/GAA/SV/SHO`, and the string
  `0.00` does not occur anywhere in the skater tables (23 rows). Goalie table headers:
  `Player, GR, W, GAA, SV, SHO` — no skater columns (4 rows, e.g. `S. Knight | 3 | 1.1 | 2.74 | 79.5 | 0.2`).
  Before the change the same Robert Thomas row ended `… 2.0 | 0.0 | 0.00 | 0.0 | 0.0`. Automated:
  `test_breakdown_splits_skaters_and_goalies`, `test_skater_section_has_no_goalie_columns`,
  `test_goalie_section_has_no_skater_columns`, `test_demo_projection_matchup_splits_skaters_and_goalies`.
- [x] **AC2 — headers show the Yahoo abbreviation.** Evidence: header lists above are abbreviations only;
  full names survive as `title=` tooltips. Automated: `test_breakdown_headers_use_abbreviations`,
  `test_demo_projection_matchup_abbreviates_headers_and_names`.
- [x] **AC3 — first-initial + surname, full name in `title`.** Evidence: real demo render shows
  `R. Thomas`, `M. Celebrini`, `S. Knight`, `P. Grubauer`; each cell carries `title="Robert Thomas"` etc.
  Automated: `test_breakdown_abbreviates_player_names_with_full_name_title` (uses `Connor McDavid` →
  `C. McDavid`), plus the demo counterpart.
- [x] **AC4 — both routes 200, demo parity.** Evidence: against the running app, `/demo/projection` → 200,
  `/demo/projection/matchup?team_key=465.l.8977.t.8` → 200, `…?team_key=465.l.8977.t.5` (the other team) → 200,
  and `/projection/matchup?team_key=…` without a cookie → 302 to `/auth/login` (auth guard intact). The
  authenticated 200 path is covered by the mocked suite in `tests/test_projection_matchup_route.py` — I
  could not exercise it against live Yahoo (no OAuth session; off-season, per `docs/LEARNINGS.md`). Both
  paths share `_render_matchup`, which is where the new context is built, so neither can miss it.
- [x] **AC5 — tally cards and comparison table unchanged; values identical to ticket 030.** Evidence: I
  captured the demo fragment from the pre-change code (`git stash` of the two source files, restart,
  `curl`) and diffed. Everything above the "Roster Breakdown" heading (tally cards + comparison table)
  is byte-identical apart from three blank lines introduced by the new macro block. Then I matched every
  rendered breakdown cell against the pre-change render across both teams: **482 stat cells plus the GR
  column, 53 players, 0 mismatches.** Automated: `test_breakdown_values_unchanged_from_ticket_030`.

**How to verify (for QA):**
- `cd /Users/carlinleung/personal_dev/fantasy_hockey && .venv/bin/python -m pytest tests/ -q` → expect
  399 passed. (Count is 399, not 400: I removed one duplicate demo test as an improvements-item fix.)
- Demo, no auth: `uvicorn web.main:app --reload`, open `http://127.0.0.1:8000/demo/projection` in a
  browser. Each team should show a "Skaters" table then a "Goalies" table. Confirm visually:
  goalie columns (`W GAA SV SHO`) appear only in the goalie table, headers are abbreviations, names read
  `R. Thomas`, hovering a name shows the full name and hovering a header shows the full stat name.
  Switch the team selector to `Zellmannator` — the fragment re-renders with the same structure.
- Width check (the ticket's Why): the skater table now has 12 columns and the goalie table 6, versus 17
  before. Worth eyeballing at ~1280px and on a narrow viewport; both tables keep their own
  `overflow-x-auto` wrapper and sticky first column.
- Authenticated: log in, open `/projection`, let a matchup auto-load; same checks. Note that during the
  off-season the live path may render an empty/placeholder state (`docs/LEARNINGS.md`).
- Value spot-check: pick any player in the demo render and confirm the number matches the pre-change
  render (`git stash` the two source files, restart, compare) — I did this exhaustively, 482/482 cells.

**Scope notes:**
- Yahoo's Assists category applies to both skaters and goalies but carries `stat_group == "offense"`, so
  under Option A a goalie's assists no longer appear in the breakdown. This is inherent to the
  group-based partition the ticket specified (goalie assists were a rounding-error contribution and were
  previously buried in a 17-column row); flagging it as a possible follow-up if the owner wants
  goaltending tables to also carry the shared offense categories.
- If a league had zero enabled categories in one group, that group's table would render with just
  Player/GR rather than dropping the players. No such league shape exists in the demo data; I chose to
  keep players visible rather than hide them.
- I did not touch the tally cards, the comparison table, `projection/index.html`, the shell route, the
  demo snapshot JSON, or the query-param work — all listed as out of scope.

**Improvements items closed:**
- "Near-duplicate demo projection matchup tests after ticket 035's alias removal" (Type: quality, Source:
  QA 035) — moved to `docs/archive/improvements-closed.md` with a ticket-034 resolution note. This ticket
  was *not* scoped from it; I closed it under the persona rule "a `Type: quality` item on a file you're
  already modifying", since I was adding the AC4 demo tests to `tests/test_demo_projection_routes.py`.
  Fix applied: deleted `test_demo_projection_matchup_accepts_team_key_param`, which asserted nothing
  `test_demo_projection_matchup_returns_fragment` did not already assert.
- No open improvements item exists on either file in `Touches`.

**Known limitations / things I couldn't fully test:**
- **No browser screenshot.** The Chrome extension is not connected in this environment, so I drove the
  running uvicorn app over HTTP and asserted on the exact rendered markup rather than looking at a
  rendered viewport. Everything structural is verified; what I have *not* seen with my own eyes is how
  the two stacked tables and the section labels look at real widths (spacing between the Skaters and
  Goalies tables, sticky-column behaviour while scrolling). QA should confirm that visually.
- The authenticated `/projection/matchup` 200 render was exercised only through the mocked test suite —
  no live Yahoo session is available (off-season, no OAuth credentials here). The demo path exercises the
  identical compute + render tail via `_render_matchup`.
- I corrected `stat_group` fixture values in two existing test files from `skaters`/`goalies` to the real
  Yahoo `offense`/`goaltending`. Before that correction the new partition would have been exercised
  against values Yahoo never returns. Worth a reviewer glance since it edits pre-existing test data.
