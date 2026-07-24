## Code Review — 034

**Reviewer date:** 2026-07-23
**QA verdict on entry:** APPROVED (`tickets/034-qa.md`) — gate satisfied.

**Files reviewed:**
- `web/routes/projection.py` — `is_goalie` tag on each breakdown row; `skater_columns` / `goalie_columns` built inside the shared `_render_matchup`; `enabled_stats` dropped from the template context.
- `web/templates/projection/_matchup.html` — `roster_table(rows, columns)` parameterised; new `team_breakdown(rows)` macro splits Skaters / Goalies; abbreviation headers with full-name `title`; first-initial + surname player names with full-name `title`.
- `tests/test_projection_matchup_route.py` — 6 new ticket-034 tests; `_patched()` gained `rosters` / `lastmonth` overrides; `stat_group` fixture corrected to real Yahoo values.
- `tests/test_demo_projection_routes.py` — 2 new AC4 demo-parity tests; duplicate test removed.
- `tests/test_projection_matchup_qa.py` — `stat_group` fixture corrected (`skaters` → `offense`).
- `tests/test_projection_breakdown_qa.py` — QA's 4 supplementary edge-case tests (new file).
- `docs/improvements.md` / `docs/archive/improvements-closed.md` — one `Type: quality` item closed.
- `tickets/034-projection-roster-readability.md` — `## Status` `ready` → `qa`.

Suite re-run independently: `.venv/bin/python -m pytest tests/ -q` → **403 passed**, 0 failed.

### Scope: CLEAN

The only `web/` files touched are the two in `Touches`. Everything else falls into a
category the process already sanctions:

| Outside `Touches` | Judgement |
|---|---|
| 3 test files + 1 new test file | Not creep. `Touches` lists never include tests in this repo (checked 030, 031), and `docs/DECISIONS.md` 2026-05-31 makes AC coverage the Engineer's job — the tests have to land somewhere. |
| `docs/improvements.md`, `docs/archive/improvements-closed.md` | Not creep. My own checklist names the improvements close-out as an explicitly allowed doc edit, and `.team/engineer.md` line 36-40 *requires* closing a `Type: quality` item that lives on a file the Engineer is already modifying. |
| Ticket `## Status` line | Expected workflow bookkeeping. |

On the specific question of the closed item ("Near-duplicate demo projection matchup
tests after ticket 035's alias removal"): **acceptable hygiene, not a scope finding.**
Three things make it clean rather than opportunistic. The item lives on
`tests/test_demo_projection_routes.py`, which this ticket had to modify anyway for the
AC4 demo tests, so it is squarely inside the Engineer's standing instruction. The fix is
a deletion of `test_demo_projection_matchup_accepts_team_key_param`, whose assertions
(`200` + `"Roster Breakdown"`) are a strict subset of the surviving
`test_demo_projection_matchup_returns_fragment` — I confirmed that from the diff, not
from the handoff, so no coverage was lost. And it changes no product behaviour. The
Engineer flagged it proactively in the handoff and QA re-verified the close was factually
correct; that is the process working, not bypassing it.

One wording ambiguity for the owner, not a finding against this ticket: `.team/engineer.md`
item 6 opens with "for any open item on a file in `Touches`" and then broadens to "a file
you're already modifying". Since test files are never in `Touches` but are always modified,
the two clauses disagree for exactly this case. Worth one clarifying word in the persona.

### Architecture: CLEAN

- **2026-05-30 (HTMX shell + fragment split).** `_matchup.html` still opens on
  `{% if not has_matchup %}` — no `base.html`, no `<html>`/`<body>`, no hardcoded route
  URLs. The new macros are defined inside the existing `{% else %}` branch and change the
  fragment's contents only, never its status as a fragment.
- **2026-04-19 (presentation mapping lives in templates).** Correctly split: the *derived*
  presentation (name abbreviation, section labels, which table a row lands in, cell
  formatting) is Jinja; the route only forwards real Yahoo fields (`abbreviation`,
  `stat_group`, `display_position`). Nothing was pushed into `analysis/` — that layer is
  untouched by this diff.
- **2026-07-03 (demo and live share one compute/render helper).** Verified by reading the
  route, not the handoff: `_matchup_impl` returns `_render_matchup(...)` at
  `web/routes/projection.py:159` and `demo_projection_matchup` returns it at `:349`, and
  `skater_columns` / `goalie_columns` are built at `:228-241` — inside the helper, below
  the assembly seam. Neither handler gained a new argument, so the two paths cannot
  diverge on this context. This is the decision's reference implementation being used as
  intended.
- **2026-05-31 (Engineer owns AC coverage).** Satisfied — 8 Engineer tests spanning all
  five criteria, present before QA started.
- No framework import in `data/` / `analysis/` / `auth/` (none of those layers changed).
- No new Yahoo call of any kind, so no per-entity-loop risk; no new `data/` function, so
  no missing `data/demo.py` counterpart.
- No implicit-decision drift: no new directory, no new template-naming pattern, no new
  route, no new dependency, no new env var. Nothing here needs a DECISIONS entry.

### Verification adequacy: sufficient

Two things could not be observed in this environment — a rendered viewport (no browser
automation connected) and a live authenticated Yahoo render (off-season, no OAuth
session). QA stated both as flat facts and declined to count them as passes, which is the
right handling. My judgement is that the remaining evidence carries all five acceptance
criteria:

- Every AC is a statement about **rendered markup** (which columns exist in which
  section, what a `<th>` says, what a name cell says, 200 status, value equality). All
  five were checked against real HTTP responses from a running uvicorn against the real
  Week 14 snapshot, parsed with `html.parser` rather than grep. None of them requires
  seeing pixels.
- AC5 got the strongest possible evidence short of a live session: QA rebuilt the
  pre-change app from `git archive HEAD` on a second port and compared 535 (player, stat)
  cells per team key with 0 mismatches, plus a byte-level diff above "Roster Breakdown"
  showing three whitespace-only lines and nothing else. That is an independent
  reconstruction, not a re-run of the Engineer's method.
- AC4's authenticated 200 render is the one criterion resting on mocks rather than live
  Yahoo. I accept it because the shared-helper structure makes it a structural
  consequence, not a hope: the demo path exercises the identical compute + render tail,
  and the only authenticated-only code is the fetch/assembly head this ticket did not
  touch. This is exactly the residual gap `docs/DECISIONS.md` 2026-07-03 (past-week
  testing) accepts by design.

What genuinely remains unseen is viewport-level and sits under the ticket's *Verification*
section rather than its acceptance criteria: how much horizontal scroll actually
disappears at 1280px and on a phone, the spacing between the stacked Skaters and Goalies
tables, whether the sticky first column still behaves in each of the two scroll
containers, and whether the `title` tooltips surface on hover. The objective proxy is
strong (widest breakdown table 16 → 12 columns, goalie table 6, plus shorter names) and
points the right way, but it is a column count, not a measurement. Carry these forward as
owner-must-verify on next login; none is a reason to hold the ticket.

### Issues

- **should-fix (logged, not blocking):** `test_breakdown_values_unchanged_from_ticket_030`
  (`tests/test_projection_matchup_route.py`) does not do what its name says. It asserts
  `"11.0" in body`, `"6.0" in body`, `"2.50" in body` and `body.count("Projected Wins") == 2`
  against a single mocked render. Two weaknesses: it is not a pre/post comparison, so it
  cannot detect that a value *changed* relative to ticket 030; and unanchored substring
  matching does not pin which cell holds the value (`"6.0"` also matches `16.0` or
  `6.05`). QA reached the same conclusion independently. It is still a useful regression
  pin, and AC5 itself is properly evidenced by QA's 535-cell pre/post comparison, so this
  is a test-strength issue rather than a coverage hole. A true pre/post assertion cannot
  live in a unit test anyway — the fix is to rename it to what it does (e.g.
  `test_comparison_table_and_tally_cards_render_expected_values`) and anchor the
  assertions to specific cells. Logged to `docs/improvements.md`; not worth returning the
  ticket.
- **nit:** `web/routes/projection.py:234` uses `c.get("abbreviation", c["stat_name"])`
  while the adjacent line reads `c["stat_group"]` as a hard key. `data/client.py:119`
  always sets `abbreviation` from Yahoo's `display_name`, and all 15 categories in
  `demo/data/stat_categories.json` carry it, so the fallback defends a shape that has no
  producer. Inconsistent defensiveness on two lines of the same dict comprehension; a
  plain `c["abbreviation"]` would fail loudly if Yahoo ever dropped the field, which is
  the more useful behaviour.
- **nit:** `roster_table(rows, columns)` takes its columns as an explicit parameter (good
  — that is what made the split possible), but `team_breakdown(rows)` reaches for
  `skater_columns` / `goalie_columns` out of the surrounding template context. Passing
  them in would make the macro's inputs self-evident and match the sibling macro's style.
- **nit:** the "Skaters" / "Goalies" section labels are `<p>` elements between an `<h3>`
  team name and a `<table>`. They are structurally headings; `<h4>` (or a `<caption>` on
  each table) would read better to a screen reader at no visual cost given the classes
  already applied.

### Process question — QA's supplementary test file: not a finding

`tests/test_projection_breakdown_qa.py` is **within** the 2026-05-31 decision, not a
breach of it. That decision's chosen Option B reads: "QA may add supplementary edge-case
or regression tests on top of existing AC coverage, but is not responsible for writing
the primary AC test suite," and `.team/test-engineer.md` Step 3 repeats it verbatim ("If
AC coverage is present, you may add supplementary edge-case or regression tests"). The
prohibited sequence is QA silently backfilling *missing* AC coverage instead of returning
the ticket. That is not what happened: QA verified AC coverage was present for all five
criteria first (8 Engineer tests, mapped criterion by criterion in the report), and only
then added four tests that no AC demands — a mononym name, a goalie-only roster, a
multi-token `display_position` like `C,G`, and a league with no enabled goaltending
categories. Every one of those is an edge case around the new partition, and all four are
gaps the Engineer's happy-path tests genuinely leave open.

**The tests should stay**, in the file QA put them in. No action for the Engineer.

One consequence worth tracking, and it is about duplication rather than authorship: this
new file is the **third** verbatim copy of the projection-route test harness (`_make_db`,
the `user_sessions` schema, the `TestClient` fixture, `TEAMS` / `SETTINGS` / `SCOREBOARD`
/ `LIVE_STATS` constants) alongside `test_projection_matchup_route.py` and
`test_projection_matchup_qa.py`. There is no `tests/conftest.py` to hold it. Pre-existing
pattern, amplified here; logged to `docs/improvements.md` rather than fixed in this
ticket.

### Also logged, not blocking

Goalie Assists no longer render anywhere in the breakdown. Yahoo tags Assists as
`stat_group == "offense"` even though it applies to goalies too (`data/client.py:107-108`
comments on precisely this), so under the group partition the ticket prescribed, the
Assists column is absent from the Goalies table. I am not treating this as a defect: the
ticket explicitly directed partitioning on `stat_group`, explicitly sanctioned Option A,
and QA measured the actual impact rather than reasoning about it (260 cells disappeared
per fragment, every one of them holding `0.0` or `0.00`; all 8 demo goalies have no
offense stats at all). No number a manager could have read changed. But it is a real
behaviour difference in a live league where a goalie records an assist, and whether
goalie tables should carry the shared offense categories is a product call. Logged as a
`Type: quality` item for the PM to promote if the owner wants it.

### Verdict: APPROVED

Clean, well-argued change. Option A was the right call and the handoff's reasoning for it
holds up: making the goalie column physically absent satisfies AC1 by construction, so no
future edit can reintroduce a `0.00` filler cell the way a blank-the-cell approach could.
Building the new context inside `_render_matchup` rather than in the two handlers is the
detail that makes demo parity structural instead of a promise. The `stat_group` fixture
correction (`skaters`/`goalies` → `offense`/`goaltending`) in two pre-existing test files
deserves particular credit — it was flagged for reviewer attention, and without it the new
partition would have been exercised against values Yahoo never returns, i.e. the tests
would have been green against fiction.

**New `docs/improvements.md` entries:**
- "Goalie tables omit shared offense categories (Assists)" — `Type: quality`, Source: Code review 034.
- "`test_breakdown_values_unchanged_from_ticket_030` name overstates what it asserts" — `Type: quality`, Source: Code review 034.
- "Projection route test scaffolding duplicated across three test files" — `Type: quality`, Source: Code review 034.

**Carried forward as owner-must-verify on next authenticated login (not blocking):**
horizontal-scroll reduction at real widths, spacing between the stacked Skaters/Goalies
tables, sticky-first-column behaviour inside each of the two scroll containers, and
`title` tooltips appearing on hover.
