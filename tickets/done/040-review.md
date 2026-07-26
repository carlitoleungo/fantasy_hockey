## Code Review — 040

**Reviewed:** 2026-07-26. QA verdict on entry: APPROVED (`tickets/040-qa.md`), all six ACs
verified independently, so the ticket was eligible for review.

**Files reviewed:**
- `tests/test_nav_shell_qa.py` → `tests/test_nav_shell.py` — `git mv` (rename detected at 71%
  similarity, staged index holds the pure move), new docstring, one redundant test deleted,
  helper path map extended by one key, three tests / five parametrised cases added. +112 −44.
- `docs/improvements.md` — the two entries named in Why removed (−18, single hunk).
- `docs/archive/improvements-closed.md` — the same two entries appended with ticket-040
  resolution notes (+18).
- `tickets/040-nav-shell-regression-guards.md` — `## Status` `ready` → `qa`.
- `web/routes/overview.py`, `web/templates/base.html`, `web/routes/common.py` — read as
  context only, confirmed unchanged.

### Scope: CLEAN

`git diff HEAD --stat -- web/` is empty: every file under `web/` is byte-identical, so the
five mutation probes were genuinely reverted. `tests/conftest.py` does not exist. The other
three `*_qa.py` files (`test_overview_routes_qa.py`, `test_projection_breakdown_qa.py`,
`test_projection_matchup_qa.py`) show an empty diff. No `_make_db` / `_insert_session` / `ctx`
scaffolding was touched, so the thirteen-file duplication item the ticket carved out is intact
and still open. `docs/LEARNINGS.md` is unmodified. `tests/test_head_to_head_routes.py` gained no
nav assertions and no fragment-handler tests were added, both as instructed. Four files changed,
all inside `Touches`. The unusually long `Out of scope` list held on every clause.

### Architecture: CLEAN

No framework import in a pure layer, no Yahoo call added at all (the tests patch every data
helper), no new live data function and therefore no demo-parity obligation, no SQL, no secrets,
no cookie handling changed. Test-only diff, so the security and data checklist is not engaged
beyond confirming the fixture session rows use the existing parameterised `?` insert, which they
do (unchanged code).

Decision conformance, checked against the three entries the ticket names:

| Decision | Status |
|---|---|
| 2026-07-03 nav shell via shared `shell_context()` | Conformed. The tests exercise the mechanism through the routes and, for the default path, directly against the template. No second auth-derivation path introduced. |
| 2026-04-19 Overview → Waiver → Projection ordering | Conformed. `AUTHENTICATED_NAV` / `DEMO_NAV` are ordered lists compared with `==` inside `<nav>`, so ordering is genuinely asserted, not just membership. |
| 2026-07-26 one module per feature surface | Conformed exactly, and no further. The ruling assigns `test_nav_shell_qa.py` and only that file to this ticket; the diff renames that file and no other. |

**No new convention, so no Tech Lead ruling is owed by this ticket.** The rename, the module's
status as canonical home of the nav contract, and the decision to leave its harness in place are
all pre-ratified by the 2026-07-26 entries. The rewritten docstring restates those rulings rather
than inventing anything; the `# ---- Ticket 040` banner matches the existing 036b banner in the
same file. There is one architectural item for an owner, but it predates this ticket and is
already ruled on — see the first finding.

### Do the tests guard what they claim?

Yes, and QA's probe work is sufficient evidence — I did not repeat it. What I checked instead was
whether the probes prove the right thing.

- All 12 spreads exist where claimed (`grep -c` over the three route modules returns 12), and
  QA mutation-probed all 12, not just the ticket's 5. Every deletion turned at least one test red.
  AC3's "all 12 covered" is therefore a measured property.
- I read the five target branches in `web/routes/overview.py` and confirmed each test lands where
  the ticket's table says. `/overview` and `/demo/overview` gate on `df is None or df.empty`;
  both head-to-head handlers compute `teams = ... if df is not None and not df.empty else []` and
  gate on `len(teams) < 2`, so `get_matchups → None` reaches the `len(teams) < 2` branch and not
  some earlier guard. QA's per-branch discrimination (deleting 241 fails only `/demo/overview`,
  deleting 311 only the head-to-head case) confirms it from the other direction.
- The `data.demo.get_matchups` patch target is load-bearing, proven by QA running the wrong-target
  trap as a control: `2 passed`, i.e. a silently-green no-op. The inline comment above
  `test_demo_empty_state_renders_demo_nav` explains the inversion and points at the LEARNINGS.md
  exception clause, which does exist at lines 51-67. A future reader who copies this test will not
  copy the bug.
- The nav assertions on the three authenticated branches are inert **today** — QA's ablation proved
  the header-label assertion is the sole guard, because `base.html` falls back to the authenticated
  nav when the flags are absent. They are not decorative, though, and I would not want them removed:
  they still catch a different mutation class (a branch that passes `demo=True`, or a nav link set or
  ordering change), and they become the primary guard the moment the DECISIONS 2026-07-25 default flip
  lands. Keeping both assertions in every test is the right call and the ticket was right to insist.

`.venv/bin/python -m pytest tests/` re-run at review: **459 passed** in 1.48s.
`tests/test_nav_shell.py` alone: **32 passed**. Both match the handoff and the QA report.

### Issues

- **should-fix (logged, not blocking): `base.html`'s authenticated-nav default is a latent hazard,
  and its blocker has cleared.** This is a genuine architectural item, so I am stating it for its
  owner rather than resolving it. The Tech Lead has already ruled (DECISIONS 2026-07-25, "Forward
  commitment"): the default should flip to nav-free once 036b lands. **036b is done, so the flip is
  unblocked**, and it is currently tracked only inside a decision paragraph and two side-notes on
  other tracker entries, not as work. Ticket 040 adds the strongest evidence yet for it: with the
  default in place, dropping `**shell_context(...)` from an authenticated branch is invisible to any
  nav assertion, and the only thing catching it is the league-label assertion, which works by the
  coincidence that `selected_league_name` vanishes along with the spread. An authenticated page
  rendered without a selected league would have no guard at all. That is the exact silent failure
  mode 036a and 036b existed to fix, still live on the authenticated side. Not this ticket's defect
  and not fixable here (`base.html` is explicitly out of scope). Filed to `docs/improvements.md` as
  "`base.html`'s authenticated-nav default is now unblocked, and 040 measured what it costs", with
  the ablation evidence and a sequencing note pairing it with the `auth_state_unknown` error-page
  ticket. **For the PM to schedule; the mechanism needs no further Tech Lead input.**

- **should-fix (logged, not blocking): the `.pyc` staleness trap belongs in `docs/LEARNINGS.md`.**
  My call, and my answer is yes. Three arguments. It affects future unrelated tickets, which is
  LEARNINGS.md's stated admission test: mutation probes are now a standing technique here (036a,
  036b and 040 all ran one, and 040 made one an acceptance criterion), and the collision is a
  property of CPython's cache validation, not of this ticket. The file already carries test-harness
  gotchas, so QA's reasoning that this is "a harness technique rather than a code gotcha" would also
  have excluded "Tests must patch the importing module's namespace", the entry directly load-bearing
  for this very ticket. And the failure mode is a silently wrong result, not a crash: QA's first pass
  certified the wrong test as the guard for line 241, and `pytest -p no:cacheprovider` does not
  prevent it because that flag governs pytest's cache, not CPython's. A trap that can quietly
  mis-certify a verification method is exactly what a shared gotchas file is for. Leaving it in
  `tickets/040-qa.md` only helps someone re-running *this* probe. Not a defect in the work and not
  worth returning the ticket for a docs append, so it is filed to `docs/improvements.md` as
  "Mutation-probe `.pyc` staleness trap is recorded only in a QA report" for the next ticket that
  opens LEARNINGS.md. I cannot append it myself under the persona rules.

- **nit (resolved by me, no action for the Engineer): the three stale `test_nav_shell_qa.py`
  citations.** Acceptable exactly as shipped. The Engineer and QA both read the constraint correctly:
  the ticket forbids touching those two entries, both are substantively unresolved, and editing them
  would have been the scope leak the ticket spent three paragraphs preventing. Flagging them in the
  handoff and the QA report rather than silently fixing them was the right move. The correction
  belongs with the curator of `docs/improvements.md`, which is the Reviewer, and I have made it in
  this review: lines 194, 195 and 215 now name `tests/test_nav_shell.py`, with line 194 keeping the
  historical name in parentheses since that sentence is a statement about what ticket 036a did. These
  are pure path substitutions; no entry's substance, `Type`, `Source` or `Detail` reasoning changed,
  and all three entries remain open. Line 195 was the one that actually mattered: it is the file list
  the consolidation ticket will work from, and a name that no longer exists in `tests/` would have
  sent that ticket looking for a fourteenth file. Deferring these to "whichever ticket next reopens
  the entry" would have left a dangling path in a work list for an unknown number of tickets.

No blockers. Nothing under `web/` changed, so there is nothing that could regress behaviour.

### Verdict: APPROVED

Test-only, and the tests earn their place: five real branches, five probes, each failing for a
reason the handoff states correctly and QA re-derived independently. The handoff's own honesty is
worth noting — it volunteered that the nav assertion does not catch the authenticated mutations and
explained why, which is what let QA go straight to the ablation that confirmed it, and it flagged
the stale reference it created rather than quietly fixing or ignoring it.

**Changes I made to `docs/improvements.md` as its curator:**
- Corrected three stale `tests/test_nav_shell_qa.py` path references (lines 194, 195, 215) to
  `tests/test_nav_shell.py`. No substantive edit to either entry; both stay open.
- Added `Type: quality` entry: "`base.html`'s authenticated-nav default is now unblocked, and 040
  measured what it costs".
- Added `Type: quality` entry: "Mutation-probe `.pyc` staleness trap is recorded only in a QA
  report".

**For the PM:** the `base.html` default flip is unblocked and now has a tracker entry. It is the
last remaining half of the silent-nav failure mode 036a/036b/040 have been chipping at.
