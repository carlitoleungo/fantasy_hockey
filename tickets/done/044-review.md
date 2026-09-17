## Code Review — 044

**Files reviewed:**
- `web/templates/base.html` — combined condition split into an empty `{% elif is_authenticated is undefined %}` followed by `{% elif is_authenticated %}`; stale lines 21-22 comment deleted; a three-line comment citing DECISIONS 2026-07-25 added on the new empty branch
- `tests/test_nav_shell.py` — two matrix rows flipped to `[]` with rewritten comments, docstring bullet 4 rewritten, one test added (`test_base_html_absent_flags_keep_the_brand_link`)
- `tests/test_overview_routes.py` — TC9 comment rewritten, test renamed `test_overview_renders_authenticated_nav`; assertions untouched
- `docs/LEARNINGS.md` — new "Purge `__pycache__` between mutation probes" entry, placed next to the patch-target gotcha
- `docs/improvements.md` / `docs/archive/improvements-closed.md` — three items moved with `**Resolved:** Ticket 044 …` notes; no `## Closed` section created in the active tracker
- `web/routes/overview.py` — **not changed**; verified independently (below)

### Scope: CLEAN

`git status` shows exactly seven paths: the four in `Touches`, the two tracker files the ticket's
Notes explicitly authorise, and the ticket file's own `Status` line. No route module, no
`shell_context()` change, no nav styling, ordering, or copy change. The `auth_state_unknown`
branch is untouched and still the first `{% if %}` in the block, as Out of scope required.

**`web/routes/overview.py` restoration confirmed independently.** It is absent from `Touches` but
was mutated eight times across the Engineer's and QA's probes. I checked it myself rather than
taking either report's word: `md5 -q web/routes/overview.py` → `53e0ec6ee9ad6a77e03e66a122b939bf`,
matching both reports, and `git status --porcelain` does not list the file at all. Restored
byte-identical.

### Architecture: CLEAN

- **Pre-existing consult verified against the commitment, not merely cited.** I read the full
  2026-07-25 entry. Its "Forward commitment" paragraph specifies: absent flags render the nav-free
  header so a page that forgets `shell_context()` degrades visibly instead of lying; the flip is
  blocked on 036b (done, 2026-07-25); and the explicit `auth_state_unknown` key stays, named for
  its cause rather than its effect, so the error-page fix does not wait on the flip. The
  implementation matches all three. The nav-free default is achieved by an empty branch rather
  than by collapsing into `auth_state_unknown`, which preserves the entry's insistence that the
  key not become a generic "hide the nav" switch. No new architectural surface is established and
  no ruling is contradicted, so no new Tech Lead consult was owed.
- The one subtlety the ticket warned about is handled structurally, not incidentally: a bare
  `{% elif is_authenticated %}` would have merged "absent" into "explicitly False". The separate
  `is undefined` branch placed ahead of it keeps the two rows distinguishable, and QA's matrix
  demonstrates it (`{}` → `[]`; `is_authenticated=False` → the login link).
- No `data/`/`analysis/`/`auth/` involvement, no Yahoo call, no new dependency, no logging, no SQL,
  no cookie handling. Sections 2 and 6 of the checklist are non-applicable beyond the above.

### Verification adequacy: strong

- QA reproduced the ticket's central claim rather than confirming the Engineer's arithmetic. The
  counterfactual it ran was not required by any acceptance criterion: it repeated QA 040's
  assertion ablation (replacing the four `assert "Alpha League" in _header_left(...)` lines with
  `pass`) against both the new and the pre-044 template, and showed each of the four mutations
  fails its own branch test under the new template while **no** branch test fires for any of them
  under the old one. That converts AC4 from "these tests fail now" into "these tests fail *because
  of this change*", which is the actual claim in the ticket's Why. It also correctly identified
  why the naive counterfactual is confounded. This is the strongest piece of evidence in the
  ticket and I am weighting it as such.
- The `.pyc` trap the ticket warned about was live in QA's run (four mutations produced identical
  11536-byte files) and each probe still named a distinct test, which is direct evidence the purge
  procedure worked rather than an assertion that it was followed.
- I re-ran `.venv/bin/python -m pytest tests/` → **479 passed**, matching both reports.
- The two gaps are honestly recorded, not papered over: the authenticated-page walk and the error
  page walk in a running app are marked **owner-must-verify** by both Engineer and QA, who hit the
  same Yahoo OAuth/429 wall. I accept this. The residual risk is low and asymmetric: every one of
  those pages passes flags explicitly, so they land on branches the diff does not touch, and QA
  showed that rendering `error.html` with no shell flags at all now yields zero nav anchors where
  it previously yielded the full authenticated nav. The flip makes the unverifiable surface
  strictly safer.

### Issues

- **nit:** the new branch is an empty `{% elif %}` body. It reads as an oversight at a glance, and
  Jinja gives no better idiom short of restructuring the block. The comment directly above it
  citing DECISIONS 2026-07-25 is exactly the mitigation this needs, and restructuring to avoid the
  empty body would cost more clarity than it buys. Take it or leave it; I would leave it.
- No blockers. No should-fixes against the diff.

**Rulings on the three judgement calls referred to me:**

1. **The third stale comment (`tests/test_nav_shell.py:168`) — the Engineer was right to leave
   it, and QA was right to endorse that.** AC5 names two comments and this is not one of them;
   Out of scope is explicit about not widening; and a comment edit inside a file already open is
   precisely the kind of "while I'm here" cleanup my checklist tells me to flag, not reward. That
   it was flagged in the done note rather than silently taken is the correct handling of an
   out-of-scope observation. Logged to `docs/improvements.md` as a `Type: quality` item pointing
   at the `tests/conftest.py` consolidation ticket audit 041 reserved, which already names this
   file.
2. **DECISIONS.md.** The flip needs no entry of its own — it is the literal execution of a ruling
   already made, with the same rationale and the same branch structure, and a second entry would
   restate the first. What the entry does need is a discharge marker, because its final paragraph
   still reads as pending work "blocked on 036b" when in fact it has shipped. That is Tech Lead
   territory and I have not edited it; logged as a `Type: quality` item flagged **Tech Lead
   action**, naming the resulting branch shape so the amendment can be written without re-deriving
   it.
3. **The ticket's wrong line numbers (174/241/311).** Both personas handled this well and
   independently — the Engineer caught the misclassification and probed 56/77/146/174, QA
   re-derived the mapping from scratch rather than trusting either source, and additionally
   established that 241 and 311 are demo spreads and that lines 82/179 are HTMX fragment routes
   that legitimately carry no spread. I am not filing a tracker item for this. The correction is
   now recorded in three places that survive the ticket: the closed-archive entry for the
   `.pyc` trap cites the corrected four lines, `docs/LEARNINGS.md` describes the trap generically
   without depending on any line number, and `tickets/done/044-qa.md` carries the full
   classification table. Line numbers in a prose Note are inherently perishable; the durable fix
   is that the LEARNINGS entry a future ticket will actually read does not cite any.

### Verdict: APPROVED

New `docs/improvements.md` entries written:
- "Stale 'dormant until 036b adopts it' comment on the demo row of the nav branch matrix"
  (`Type: quality`, `tests/test_nav_shell.py` line 168)
- "DECISIONS 2026-07-25's 'Forward commitment' paragraph has been discharged but still reads as
  pending" (`Type: quality`, `docs/DECISIONS.md`, **Tech Lead action**)

Carried forward for the owner, unchanged from QA: the authenticated-page and error-page walks in a
running app remain **owner-must-verify**.
