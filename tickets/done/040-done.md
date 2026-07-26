## Implementation complete — 040

**What I did:**
- Renamed `tests/test_nav_shell_qa.py` to `tests/test_nav_shell.py` with `git mv` as a pure
  move (no content change in that step), then ran the full suite to confirm the module was
  still collected (30 tests) and the suite still green (457 passed) before touching content.
- Rewrote the module docstring. It described the file as "QA-targeted … supplementary to the
  engineer's TC17-TC19"; it now states the module is the canonical home of the nav contract
  across all three feature route modules, per DECISIONS.md 2026-07-26. The substantive notes
  (why `_nav_links` scopes to `<nav>`, why `_header_left` is what makes the label assertion
  discriminate, why the `base.html` default path is asserted against the template directly)
  are preserved, and the empty-state silent-failure rationale is added.
- Deleted `test_authenticated_nav_links_return_200` outright (3 parametrised cases). No
  replacement: the test directly above it parametrises the same three paths through the same
  helper and already asserts `status_code == 200` alongside the nav set and header label.
- Extended `_authenticated_feature_get`'s `module` lookup with `"/overview/head-to-head":
  "overview"` rather than adding a second helper, as the ticket directed.
- Added 3 new tests (5 parametrised cases) covering the five uncovered branches. Each asserts
  both the exact nav link set via `_nav_links` and the header label via `_header_left`.
- Moved the two `docs/improvements.md` entries named in the ticket's Why to
  `docs/archive/improvements-closed.md` with resolution notes citing ticket 040. Left the
  third (stale-comments) entry open and untouched.

**Files changed:**
- `tests/test_nav_shell_qa.py` → `tests/test_nav_shell.py` — `git mv`, history preserved
  (`git status` reports `RM`, rename detected).
- `tests/test_nav_shell.py` — new docstring, one redundant test deleted, helper path map
  extended, five branch cases added. +87 / -25.
- `docs/improvements.md` — the two scoped-from entries removed. -18.
- `docs/archive/improvements-closed.md` — the same two entries appended with ticket-040
  resolution notes. +18.

No file under `web/` was modified. `git status --porcelain | grep " web/"` returns nothing,
and `git diff --stat` lists only the three files above.

**The five branch tests, mapped to the ticket's table:**

| # | Branch | Test ID |
|---|---|---|
| 1 | `/overview/head-to-head` populated (line 174) | `test_authenticated_head_to_head_renders_authenticated_nav` |
| 2 | `/overview` empty (line 56) | `test_authenticated_empty_state_renders_authenticated_nav[/overview]` |
| 3 | `/overview/head-to-head` `len(teams) < 2` (line 146) | `test_authenticated_empty_state_renders_authenticated_nav[/overview/head-to-head]` |
| 4 | `/demo/overview` empty (line 241) | `test_demo_empty_state_renders_demo_nav[/demo/overview]` |
| 5 | `/demo/overview/head-to-head` `len(teams) < 2` (line 311) | `test_demo_empty_state_renders_demo_nav[/demo/overview/head-to-head]` |

Branches 2 and 3 patch `web.routes.overview.get_matchups` (module-level import). Branches 4
and 5 patch `data.demo.get_matchups`, because `demo_overview` and `demo_head_to_head`
`from data import demo as demo_module` inside the function body — the inversion documented in
`docs/LEARNINGS.md` "Tests must patch the importing module's namespace". Branch 1 needs no
patching subtlety; the helper's df already carries two teams.

**Mutation probe results (AC4) — all five confirmed:**

Method: delete only that branch's `**shell_context(...)` line from `web/routes/overview.py`,
run the single test ID, restore the original file bytes, repeat. Final integrity check
compared the restored file to the original string and to git; both identical.

| Line deleted | Failing test ID observed | Assertion that fired |
|---|---|---|
| 174 | `tests/test_nav_shell.py::test_authenticated_head_to_head_renders_authenticated_nav` | `assert "Alpha League" in _header_left(response.text)` |
| 56 | `tests/test_nav_shell.py::test_authenticated_empty_state_renders_authenticated_nav[/overview]` | `assert "Alpha League" in _header_left(response.text)` |
| 146 | `tests/test_nav_shell.py::test_authenticated_empty_state_renders_authenticated_nav[/overview/head-to-head]` | `assert "Alpha League" in _header_left(response.text)` |
| 241 | `tests/test_nav_shell.py::test_demo_empty_state_renders_demo_nav[/demo/overview]` | `assert _nav_links(response.text) == DEMO_NAV` |
| 311 | `tests/test_nav_shell.py::test_demo_empty_state_renders_demo_nav[/demo/overview/head-to-head]` | `assert _nav_links(response.text) == DEMO_NAV` |

Each probe returned `1 failed`. Two things worth stating about *why* they fail, because they
differ by nav family:

- On the authenticated branches the nav assertion alone would **not** catch the mutation.
  Dropping the spread leaves `is_authenticated` absent, and `base.html` deliberately defaults
  to the authenticated nav (the DECISIONS 2026-07-03 safety constraint), so `_nav_links`
  still equals `AUTHENTICATED_NAV`. The guard is the header-label assertion, which fails
  because `selected_league_name` is gone. This is exactly the trap the ticket flagged, and it
  is why both assertions are in every test rather than just the nav one.
- On the demo branches the nav assertion is what fails: the nav flips from `DEMO_NAV` to the
  authenticated default (`At index 0 diff: ('/overview', 'Overview') != ('/demo/overview',
  'Overview')`).

The probes also prove each test lands on its intended branch, which matters most for the demo
pair (where a wrong patch target would silently run against the populated branch and pass).
Deleting line 241 fails only the `/demo/overview` case and deleting line 311 fails only the
`/demo/overview/head-to-head` case, so both tests demonstrably rendered through the empty-state
branch. The same discrimination holds between branches 1 (line 174) and 3 (line 146). I also
inspected the failure output bodies: the line-56 probe's response contains "No matchup data
available yet", and the line-174 probe's contains "Alpha: 1 wins", confirming the empty and
populated branches respectively.

**Acceptance criteria status (self-check):**
- [x] AC1: `tests/test_nav_shell_qa.py` no longer exists; content lives at
  `tests/test_nav_shell.py`, moved with `git mv`, done first before any content edit —
  `git status --short` shows `RM tests/test_nav_shell_qa.py -> tests/test_nav_shell.py`.
  Suite was run green between the move and the content edits (457 passed, module collected
  as 30 tests). `ls tests/*_qa.py` still lists the other three files, which this ticket is
  explicitly forbidden to touch; it introduced no new `_qa` suffix.
- [x] AC2: `test_authenticated_nav_links_return_200` is gone
  (`grep -n test_authenticated_nav_links_return_200 tests/` returns nothing). Every remaining
  parametrised test in the file reads its parameter: the `path` params are passed to
  `client.get(path)` or `_authenticated_feature_get(client, path)`, the `source` param to
  `client.get(source)`, and the `context,expected` pair to the template render and the
  assertion.
- [x] AC3: each of the five branches has a test asserting the exact nav link set via
  `_nav_links` (equal to `AUTHENTICATED_NAV` or `DEMO_NAV`) and the header label via
  `_header_left`. See the mapping table above. With the 7 already covered, all 12 migrated
  branches now have a guard.
- [x] AC4: mutation probe run for all five, each failed, each reverted. Failing test IDs in
  the table above. `web/routes/overview.py` verified byte-identical afterwards.
- [x] AC5: `.venv/bin/python -m pytest tests/` — **459 passed** in 1.48s. Baseline before this
  ticket was 457 passed. Net change **+2** (removed 3 parametrised cases, added 5).
- [x] AC6: both Why entries moved to `docs/archive/improvements-closed.md` with resolution
  notes citing ticket 040; both removed from `docs/improvements.md`.

**How to verify (for QA):**
1. `git log --follow --oneline -- tests/test_nav_shell.py` — history should reach back past the
   rename, confirming `git mv` rather than delete-plus-create.
2. `.venv/bin/python -m pytest tests/ -q` — expect 459 passed.
3. `.venv/bin/python -m pytest tests/test_nav_shell.py -q` — expect 32 passed (was 30).
4. Re-run the mutation probe independently. Delete line 56, 146, 174, 241, or 311 of
   `web/routes/overview.py` (each is a lone `**shell_context(...)` line; confirm the content
   before deleting, since the line numbers shift if you do not restore between probes), run
   the matching test ID from the table, then `git checkout -- web/routes/overview.py`.
5. `git status --porcelain` — expect exactly three entries and nothing under `web/`.
6. No demo-mode data steps needed: the demo tests patch `data.demo.get_matchups` and never
   read the snapshot.

Per the persona's `Process: light` exception this is a `full` ticket, but the reasoning applies
in the same direction: every AC is asserted by a test I ran green and no route behaviour or
template changed, so no manual browser walk was performed. The ticket's own Verification
section says the same ("No manual browser walk needed").

**Scope notes:**
- I found no behavioural defect in any of the five branches. All render correct nav and header
  for their auth/demo state. Nothing to escalate under the ticket's "if a branch turns out to
  be wrong, stop" clause.
- **One stale reference I created and deliberately did not fix.** `docs/improvements.md` line
  215, inside the still-open entry "TC18's league-label assertion in `test_home_routes.py` does
  not discriminate", cites
  `tests/test_nav_shell_qa.py::test_authenticated_home_nav_and_league_label` as corroborating
  evidence. My rename makes that path stale. I left it alone: the ticket's DoD enumerates
  exactly two entries to move and the Out of scope section warns against sweeping others, and
  that entry's substance is unresolved so it cannot be closed. The referenced test still exists
  under the new module name, so the cross-reference is findable, just stale. Flagging for the
  Reviewer to decide — it is a one-path edit for whichever ticket next opens that entry.
  All other surviving `test_nav_shell_qa` references are in historical records (`tickets/done/`,
  `.team/audits/`, `.team/orchestration-logs/`) or in the DECISIONS.md entry that mandates the
  rename, none of which should be rewritten.
- I did **not** touch the "Projection route test scaffolding duplicated across three test
  files" item, and changed no `_make_db` / `ctx` / `_insert_session` scaffolding, per the
  ticket's explicit carve-out. The duplication did not obstruct the work: the five branch tests
  reuse the module's existing fixtures unchanged, so I had no reason to refactor around it.
- I did not create `tests/conftest.py`, did not touch the other three `*_qa.py` files, did not
  add nav assertions to `tests/test_head_to_head_routes.py`, and added no fragment-handler
  tests.
- No new live data function, so no demo-parity counterpart is owed.

**Improvements items closed:**
- "`test_authenticated_nav_links_return_200` is parametrised over an unused argument and adds
  no coverage" — moved to `docs/archive/improvements-closed.md`, resolution cites ticket 040.
- "Nav/header assertions cover 7 of the 12 `shell_context()` branches in the feature routes" —
  moved to `docs/archive/improvements-closed.md`, resolution cites ticket 040.
- Left open and untouched: "Post-036b stale comments about pages 'not yet' passing
  `shell_context()`" and "Projection route test scaffolding duplicated across three test files".

**Known limitations / things I couldn't fully test:**
- The mutation probe deletes the whole `**shell_context(...)` line, which is the regression the
  ticket describes. It does not cover a subtler mutation such as reordering the spread above an
  explicit `selected_league_name` key. That specific trap is already guarded for the demo pages
  by `test_demo_pages_header_keeps_demo_league_label`, which predates this ticket.
- Nothing visual was checked in a browser, by design: no template and no route behaviour
  changed, and `git diff` proves it.
