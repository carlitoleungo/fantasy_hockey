## Orchestration log — 034-projection-roster-readability

**Run started:** 2026-07-23 (ticket 034, Week Projection roster-breakdown readability)
**Run ended:** 2026-07-23
**Outcome:** completed — with one `should-fix` surfaced to the owner (see Halt conditions)

### Pre-flight
- Type check: pass — `Type: feature`, not `audit`.
- Status check: pass — `Status: ready`.
- Required-sections check: pass — `Status`, `Type`, `Touches`, `Why`, `Acceptance criteria`,
  `Out of scope`, `Notes for the Engineer`, `Verification` all present.
- `Touches` non-empty: pass — 2 paths (`web/templates/projection/_matchup.html`,
  `web/routes/projection.py`); both exist on disk.
- Audit check: `python3 scripts/audit_due.py` → **AUDIT NOT DUE** (weighted 1.5 / 5; highest
  audited ticket 31; 032 and 035 completed since). Note: `python` is not on PATH in this
  environment — `python3` was used throughout and this was passed to every subagent.
- Architectural-surface coverage: pass. `web/templates/projection/_matchup.html` sits on the
  WORKFLOW.md "Template structure (HTMX shell + fragment split)" surface, and AC4 engages the
  "Demo-mode parity" surface. The ticket cites both covering active decisions in its `Notes for
  the Engineer`: `docs/DECISIONS.md` 2026-05-30 "Feature pages: HTMX fragment pattern with shell
  + fragment template split" and 2026-04-19 "Feature pages: rank → Tailwind class mapping lives
  in templates, not analysis". Both confirmed active (not in `docs/archive/decisions-superseded.md`).
  The orchestrator additionally cited 2026-07-03 "Web routes: demo and live handlers share a
  single compute/render helper" to the Engineer, since the shared `_render_matchup` helper is
  where AC4 parity is actually secured.
- Dependency check: ticket declares a dependency on ticket 031 (Week Projection demo parity).
  Confirmed complete — `tickets/done/031-*.md` present.

### Model selection
- **Engineer: `opus`.** Heuristic branch (no `## Model` section in the ticket): `Process: full`
  **and** a `Touches` path is on the WORKFLOW.md architectural-surface list
  (`_matchup.html` → template structure).
- **Test Engineer: `opus`.** Same heuristic branch.
- **Reviewer: `opus`.** Always, per persona.

### Subagents spawned (in order)
1. **Engineer (round 1)** — `fh-engineer`, opus
   - Inputs: `.team/engineer.md` (read from disk by the agent shim), the ticket,
     `docs/DECISIONS.md` 2026-05-30 / 2026-04-19 / 2026-07-03 / 2026-05-31 entries,
     `docs/LEARNINGS.md`. Told that ticket 035 landed after 034 was written and converged the
     route on `team_key`, so the current code outranks stale route details in the ticket text.
   - Output: `tickets/034-done.md`; ticket Status → `qa`.
   - Summary: Chose **Option A** (separate "Skaters" / "Goalies" tables per team) — satisfies AC1
     by construction, since a goalie-only column is physically absent from the skater table, and
     it is the only option that also addresses the width complaint (skater table 17 → 12 columns,
     goalie table 6). `_player_breakdown` now tags each row `is_goalie`; the shared `_render_matchup`
     derives `skater_columns` / `goalie_columns` from `stat_categories` as `{"name", "abbr", "group"}`
     split on `stat_group != "goaltending"` — building it in the shared helper is what guarantees
     AC4 parity, so neither handler needed a new argument. Template: `roster_table(rows, columns)`
     takes columns as a parameter, new `team_breakdown` macro splits rows via
     `rejectattr`/`selectattr`. Headers show the Yahoo abbreviation with full name in `title=`;
     names render `C. McDavid` with full name in `title=`. 399 tests passed. Drove uvicorn against
     the real demo snapshot and, for AC5, captured the pre-change render via `git stash` and diffed:
     482 stat cells across 53 players, 0 mismatches.

2. **Test Engineer (round 1)** — `fh-test-engineer`, opus
   - Inputs: `.team/test-engineer.md`, `tickets/034-done.md`, the ticket, relevant DECISIONS /
     LEARNINGS entries. Instructed to run standard QA mode (not the `Process: light` combined
     mode), to independently re-verify rather than accept the Engineer's AC5 claim, and to state
     unconfirmable items as fact rather than hedge them.
   - Output: `tickets/034-qa.md`
   - **Verdict: APPROVED**
   - Summary: Did not accept the byte-diff claim — rebuilt a pre-change app from `git archive HEAD`
     into a scratch dir on port 8902 alongside the working tree on 8901 and compared with an
     `html.parser` walk: 535 common (player, stat) cells, 0 mismatches, all 53 players present
     before and after; region above "Roster Breakdown" differs only by three whitespace-only lines.
     AC1/2/3 from the live render: sections in order `Skaters, Goalies, Skaters, Goalies`;
     `>0.00<` below "Roster Breakdown" 45 times before, **0 after**; all 53 name cells match
     `^[A-Z]\. ` and carry a `title`. AC4: both demo team keys → 200; `/projection/matchup` with
     no cookie → 302 to `/auth/login`. Measured the goalie-Assists consequence rather than
     reasoning about it: every one of the 260 dropped cells per fragment held `0.0`/`0.00`.
     Test suite 399 → 403 passed. Added `tests/test_projection_breakdown_qa.py` (4 edge-case tests).

3. **Reviewer** — `fh-reviewer`, opus
   - Inputs: `.team/reviewer.md`, ticket, `034-done.md`, `034-qa.md`, the diff. Asked additionally
     to judge (a) the out-of-`Touches` `docs/improvements.md` close-out, (b) QA authoring a test
     file against the 2026-05-31 decision, (c) QA's flag on `test_breakdown_values_unchanged_from_ticket_030`,
     and whether the evidence suffices given no viewport and no live authenticated render.
   - Output: `tickets/done/034-review.md`
   - **Verdict: APPROVED** — Scope CLEAN, architecture CLEAN, 403 tests passed on an independent run.
   - Set ticket Status to `done` and moved all four `034-*` artifacts into `tickets/done/`.

### Files changed
- `web/routes/projection.py` (+22 / -3) — in `Touches`
- `web/templates/projection/_matchup.html` (+35 / -8) — in `Touches`
- `tests/test_projection_matchup_route.py` (+131 / -2) — Engineer-owned AC coverage
- `tests/test_demo_projection_routes.py` (+94 / -8) — Engineer-owned AC coverage
- `tests/test_projection_matchup_qa.py` (+1 / -1) — fixture `stat_group` corrected from
  `skaters`/`goalies` to the real Yahoo `offense`/`goaltending`
- `tests/test_projection_breakdown_qa.py` (new) — QA supplementary edge-case tests
- `docs/improvements.md` — one tracker item closed by the Engineer, three `Type: quality` items
  added by the Reviewer
- `docs/archive/improvements-closed.md` — the closed item archived
- `tickets/034-*.md` → `tickets/done/`

Source diff across the two `Touches` files is ~65 changed lines — well inside the ~200-line
review heuristic.

### Halt conditions tripped
- **"Reviewer raises any `blocker` or `should-fix`" — tripped, at step 4 (Reviewer).** The
  Reviewer logged one `should-fix`: `test_breakdown_values_unchanged_from_ticket_030` asserts
  literal values in the test body rather than performing a pre/post comparison, and its
  assertions are unanchored substring matches (`assert "6.0" in body` also matches `16.0` or
  `6.05`), so it pins no particular cell. This is a **test-quality** finding, not a defect in the
  shipped change — the Reviewer nonetheless returned APPROVED, logged it to `docs/improvements.md`,
  and promoted the ticket. Surfaced to the owner rather than reversed; AC5 itself rests on QA's
  independent two-server 535-cell diff, not on that test.
- No blocker was raised. No fix round was needed (QA approved on round 1).
- Diff-outside-`Touches` was checked and judged by the Reviewer as acceptable hygiene, not a
  scope finding — see Notes.

### Notes for the owner
- **Owner-must-verify (viewport-level, no browser automation connected in this environment).**
  Every acceptance criterion is a statement about rendered markup and all five were confirmed
  against real parsed HTTP responses, but nobody looked at a screen. Unobserved: horizontal-scroll
  reduction at real widths, spacing between the two stacked tables, sticky-column behaviour in
  each of the now-two scroll containers, and hover tooltips (the `title` attributes were confirmed
  present in the DOM; no tooltip was seen). These sit in the ticket's `Verification` section, not
  its ACs.
- **No live authenticated Yahoo render was possible** (off-season, no OAuth session). Only the
  302-to-login guard was observed on the running app; the authenticated 200 path is mocked-suite
  evidence only.
- **Out-of-`Touches` doc edit — resolved as acceptable, one persona ambiguity to settle.** The
  Engineer closed the tracker item "Near-duplicate demo projection matchup tests after ticket 035's
  alias removal" and archived it as `Resolved: Ticket 034`. The Reviewer confirmed the deleted
  test's assertions were a strict subset of the survivor's, so no coverage was lost, and that
  `.team/engineer.md` lines 36-40 actively require closing a `Type: quality` item on a file the
  Engineer is already modifying. **Ambiguity for the owner:** that persona item opens with "on a
  file in `Touches`" then broadens to "a file you're already modifying" — the two clauses disagree
  for exactly the test-file case, and one clarifying word would settle it. The orchestrator's own
  read is that the entry should stay archived (un-archiving would restore a false open item for
  work that is genuinely done).
- **Product call for the PM: goalie Assists.** Under the `stat_group` partition the ticket
  prescribed, Yahoo's Assists category (group `offense`, but applicable to goalies) no longer
  renders for goalie rows. Currently zero-impact — QA measured that all 260 dropped cells per
  fragment held `0.0`/`0.00`, and all 8 demo goalies have no offense stats at all — but it is a
  real behaviour change. Logged to `docs/improvements.md` by the Reviewer; the PM may want to
  promote it.
- **Test scaffolding is now triplicated.** `tests/test_projection_breakdown_qa.py` is the third
  verbatim copy of the projection route harness and there is still no `tests/conftest.py`. Logged
  as `Type: quality`.
- **QA authoring tests was checked, not waved through.** The Reviewer confirmed against the
  2026-05-31 decision that QA verified AC coverage was complete *first*, then added four tests no
  AC demands (mononym, goalie-only roster, multi-token `display_position`, league with no
  goaltending categories) — supplementary, which that decision permits, rather than backfilling
  missing coverage.
- **Three nits recorded in the review, not actioned:** a defensive `c.get("abbreviation", ...)`
  sitting next to a hard `c["stat_group"]` in the same comprehension; `team_breakdown` reaching
  for columns from context while its sibling macro takes them as a parameter; `<p>` used where the
  section labels are structurally headings.
- **Nothing was committed.** All changes are in the working tree, including the artifact moves
  into `tickets/done/` (which git currently reports as one delete plus four untracked files).
  Version control is yours.

### Round-1 QA report
Not archived here — QA approved on round 1 and no round-2 ran, so `tickets/done/034-qa.md` is
the live, un-overwritten report.
