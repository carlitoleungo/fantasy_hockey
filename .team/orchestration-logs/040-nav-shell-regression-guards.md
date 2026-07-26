## Orchestration log — 040-nav-shell-regression-guards

**Run started:** 2026-07-26 12:38
**Run ended:** 2026-07-26 13:32
**Outcome:** completed (with owner-facing findings — see Notes for the owner)

### Pre-flight
- Type check: pass (`refactor`, not `audit`)
- Status check: pass (`ready`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- `Touches` non-empty: pass (4 paths — the renamed test module both sides of the move, plus the two improvements files)
- Audit check: pass — `.venv/bin/python scripts/audit_due.py` → `AUDIT NOT DUE` (weighted 1 / 5 at pre-flight, 038 counted)
- Architectural-surface coverage: N/A — read `WORKFLOW.md` § "Architectural-surface escalation list" from disk; none of the 4 `Touches` paths is on it (this is a tests-and-docs ticket). Ticket cites DECISIONS 2026-07-03, 2026-04-19, and 2026-07-26 regardless.
- Dependency check: pass — none; 036b is in `tickets/done/`
- Process: `## Process: full` ⇒ Reviewer runs. No `Skip review: yes`.
- Orchestrator persona freshness: `.team/orchestrator.md` last committed 2026-07-23 (`d8293c9`) with no unstaged edits, so the copy read at session start was current.

### Model selection
- Engineer: **opus** — no `## Model` field, so the heuristic applied: `Process: full` **and** ≥ 3 paths in `Touches` (4) ⇒ opus
- Test Engineer: **opus** — same heuristic branch
- Reviewer: **opus** — always

### Subagents spawned (in order)
1. **Engineer (round 1)** — `fh-engineer`, opus
   - Inputs: `.team/engineer.md` (read from disk by the agent shim), `tickets/040-nav-shell-regression-guards.md`, DECISIONS 2026-07-03 / 2026-04-19 / 2026-07-26 entries, LEARNINGS "Tests must patch the importing module's namespace"
   - Output: `tickets/040-done.md`
   - Summary: Did AC1 first as a pure `git mv` (suite green at 457, module collected at 30) before any content edit, so the rename and the content diff are separable. Deleted `test_authenticated_nav_links_return_200`. Added 5 branch tests covering the ticket's table, each asserting both `_nav_links` and `_header_left`. Ran the mutation probe on all five branches and reported the failing test ID for each. Suite 459 passed, net +2 (removed 3 parametrised cases, added 5). Confirmed `web/` byte-identical after reverting probes. Held scope: no `conftest.py`, no other `*_qa.py` file touched, no scaffolding refactor. Surfaced two findings beyond "it fails": on authenticated branches the nav assertion alone does not catch the mutation (`base.html` defaults to authenticated nav when flags are absent) so the header label is the real guard; and the split failure pattern between lines 241 and 311 demonstrates the `data.demo.get_matchups` patch target took effect. Flagged one stale path reference for the Reviewer rather than editing a forbidden entry.

2. **Test Engineer (round 1)** — `fh-test-engineer`, opus
   - Output: `tickets/040-qa.md`
   - **Verdict: APPROVED** (all 6 ACs)
   - Summary: Re-derived the baseline instead of trusting it (`git archive HEAD` into a scratch tree → 457; working tree → 459; net +2 confirmed). Verified the rename is a true `rename … (100%)` with zero content delta, and proved history-following by cloning the repo and replaying the move as a commit (`--follow` reached back through 036b and 036a). Probed **all 12** migrated branches rather than the ticket's 5 — every deletion turns at least one test red, making "all 12 covered" a measured property. Confirmed both Engineer claims: ablating `_header_left` left all three authenticated mutations passing (32 passed), so the label is the sole guard; and ran the wrong-patch-target trap as a control (2 passed = silently-green no-op) while showing the correct target collapses `/demo/overview` from 23,194 to 1,465 bytes. Ran all probes in an out-of-repo copy. Found and diagnosed a `.pyc` staleness trap that made their own first probe pass report a false result.

3. Engineer (fix round) — **not run** (QA approved on round 1)

4. Test Engineer (round 2) — **not run**

5. **Reviewer** — `fh-reviewer`, opus
   - Output: `tickets/done/040-review.md`
   - **Verdict: APPROVED** — no blockers; 2 should-fix (logged, not blocking), 1 nit (resolved by the Reviewer)
   - Summary: Scope and architecture clean, verified independently — `git diff HEAD --stat -- web/` empty, no `conftest.py`, other three `*_qa.py` files diff-empty, `docs/LEARNINGS.md` unmodified. Suite re-run at review: 459 passed. Read the five branches in `web/routes/overview.py` and confirmed each test lands where the ticket's table says (both head-to-head handlers compute `teams` from the same guard, so `get_matchups → None` reaches `len(teams) < 2`). Did not repeat QA's 12-branch probe. Ruled no new convention needs a Tech Lead decision: the rename, the module's canonical status, and it keeping its own harness are all pre-ratified by the two 2026-07-26 entries. As curator of `docs/improvements.md`, fixed the three stale path citations themselves. Set Status to `done` and moved all artifacts to `tickets/done/`.

### Files changed
- `tests/test_nav_shell_qa.py` → `tests/test_nav_shell.py` (rename preserved, +112 −44)
- `docs/improvements.md` (2 entries moved out per the DoD, 2 new should-fix entries logged by the Reviewer, 3 stale path citations corrected)
- `docs/archive/improvements-closed.md` (+18 — ticket-040 resolution notes)
- `tickets/040-nav-shell-regression-guards.md` → `tickets/done/` (Status `ready` → `done`)
- `tickets/done/040-done.md`, `tickets/done/040-qa.md`, `tickets/done/040-review.md` (new artifacts)

Nothing under `web/` changed — confirmed by me directly after the Engineer's handoff and again after the Reviewer's, so all five mutation probes were genuinely reverted. Cumulative diff well under the ~200-line heuristic.

### Halt conditions tripped (if any)
None mid-run. Clean sequence: no fix round, no hedged verification claims, no scope escape, no dependency/env-var/config request, no architectural question requiring a Tech Lead.

Two Reviewer findings reached the `should-fix` bar, which the halt rules direct to the owner. Both arrived **with** the APPROVED verdict at the final step, so there was no subsequent step to halt before — surfaced below rather than blocking. Nothing was auto-promoted past a CHANGES_REQUESTED.

### Notes for the owner

**Two items to schedule. Neither blocks ticket 040, which is done and approved.**

1. **`base.html`'s authenticated-nav default is a latent hazard, and its blocker has now cleared (should-fix, logged to `docs/improvements.md`).** When shell-context flags are absent, `base.html` falls back to the authenticated nav — which means a dropped `**shell_context(...)` spread on an authenticated branch is invisible to any nav-set assertion. QA proved this by ablation: with `_header_left` stubbed out, all three authenticated mutations still passed. The sole guard is the league-label assertion, and it works only by the coincidence that `selected_league_name` vanishes along with the spread. An authenticated page without a selected league would have no guard at all. The Tech Lead already committed (DECISIONS 2026-07-25 "Forward commitment") to flipping this default once 036b landed; 036b is done, so the flip is unblocked but currently tracked only inside a decision paragraph rather than as work. The Reviewer judged it needs no further Tech Lead input — it is a PM scheduling call.

2. **A `.pyc` staleness trap in the mutation-probe methodology belongs in `docs/LEARNINGS.md` (should-fix, logged).** Lines 174, 241 and 311 of `web/routes/overview.py` are each exactly 77 bytes, so mutating one branch then another produces same-size files; with mtime inside the same second, CPython reuses the stale `.pyc`. `pytest -p no:cacheprovider` does **not** prevent it. QA's first probe pass silently reported a false result until they purged `__pycache__`. This matters because mutation probes are a standing technique here (036a, 036b, 040) and the failure mode mis-certifies which test guards which branch — the exact thing these tickets exist to establish. The Reviewer cannot append to `LEARNINGS.md` under their persona rules, so it is queued for the next ticket that opens that file.

**One thing the Reviewer changed that is worth knowing about:** they corrected three stale `tests/test_nav_shell_qa.py` citations in `docs/improvements.md` (lines 194, 195, 215) left behind by the mandated rename. The Engineer and QA both deliberately left these alone, correctly — editing them would have been the scope leak the ticket spent three paragraphs preventing. The Reviewer owns that file as curator, so the correction was theirs to make. Line 195 is the one that mattered: it is the file list the upcoming consolidation ticket will work from, and a nonexistent filename would have sent it hunting a fourteenth file. Both entries stay open with their substance untouched.

**Audit status after this ticket:** weighted 2 / 5. Not due.

**Version control:** untouched, as per my rules. The working tree holds the full change uncommitted, including the `tickets/040-*.md` → `tickets/done/` move.

### Round-1 QA report (archived if a round-2 ran)
N/A — QA approved on round 1, so no round-2 ran and no report was overwritten. The single QA report is at `tickets/done/040-qa.md`.
