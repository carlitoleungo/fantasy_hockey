## Orchestration log — 050-error-page-mobile-padding

**Run started:** 2026-09-17
**Run ended:** 2026-09-17
**Outcome:** completed (after one fix round)

### Pre-flight
- Status check: pass (`ready`)
- Type check: pass (`bug`)
- Required-sections check: pass (all eight present)
- `Touches` non-empty: pass (`web/templates/error.html`, `tests/test_error_handling.py`)
- Audit check: pass — 1 / 5, AUDIT NOT DUE
- Architectural-surface coverage: N/A — the ticket states no architectural surface is
  touched, and the orchestrator confirmed neither path is on WORKFLOW.md's list. The change
  is a container class on one page template, not a shell or fragment-split change.

### Model selection
- Engineer: `sonnet` — heuristic branch `Process: light`. No `## Model` section.
- Test Engineer: `sonnet` — same branch.
- Reviewer: not spawned (`Process: light`; the combined QA+review covers the checklist).

### Subagents spawned (in order)
1. Engineer (round 1)
   - Output: `tickets/050-done.md`
   - Summary: `error.html`'s container went from `max-w-xl mx-auto mt-16 text-center` to
     `max-w-xl mx-auto mt-16 px-4 text-center`, matching the four other page shells. Swept
     the forecast `scope="module"` fixture item in `tests/test_error_handling.py`. Moved the
     fixture item to the closed archive; left the "Back to home link" item open with a note
     appended. Suite: 477 passed, unchanged. Declared AC2 (375px) unverified — no Playwright
     or chromium available.

2. Test Engineer (round 1, combined QA + review)
   - Output: `tickets/050-qa-review.md`
   - Verdict: **NEEDS FIXES** — one blocker
   - Summary: Template diff correct, scope boundaries held, improvements bookkeeping correct
     and asymmetric, fixture scope change verified safe against cross-test leakage. But
     `grep -rn "px-4" tests/` returned zero — AC1 had no automated coverage, and the
     Engineer's round-1 check was an ad hoc uncommitted TestClient call, not a regression
     test. Returned rather than fixed, per persona Step 3.
   - On AC2, QA went considerably further than required: found a cached headless Chromium
     left from a Playwright install, installed `puppeteer-core`, established a working CDP
     connection, and still had every `page.goto()` time out with zero network activity —
     including to the app's own `/health` (which `curl` reaches instantly) and to
     `example.com`. Conclusion: the sandbox browser process has no network egress at all.
     Recorded as owner-must-verify rather than hedged into a pass.

3. Engineer (fix round — the one allowed)
   - Output: `tickets/050-fix.md`
   - Summary: Added `test_500_handler_content_container_has_horizontal_padding` and nothing
     else. Used a full container-tag assertion rather than QA's suggested
     `assert "px-4" in resp.text`, because `base.html`'s header also carries `px-4`
     (`border-b px-4 py-3`), so the bare substring would not guard the regression. Proved
     the test fails when `px-4` is reverted, then restored. Suite: 478 passed (+1).

4. Test Engineer (round 2, combined QA + review)
   - Output: `tickets/done/050-qa-review.md` (round-1 report overwritten; archived below)
   - Verdict: **APPROVED**
   - Summary: Reproduced the regression independently rather than trusting the fix note —
     stripped `px-4`, ran the new test alone, observed the AssertionError. The failure
     output still contained `base.html`'s `border-b px-4 py-3`, which directly proves QA's
     own round-1 suggestion would have passed on a broken page and the Engineer's stronger
     assertion is correct. Confirmed no scope expansion: only
     `tests/test_error_handling.py` changed in the fix round. Suite: 478 passed. Set Status
     `done` and moved all artifacts.

### Files changed
- `web/templates/error.html` (+1 -1)
- `tests/test_error_handling.py` (+7 -1)
- `docs/improvements.md` (+4 -9), `docs/archive/improvements-closed.md` (+9)
- Moved to `tickets/done/`: the ticket, `050-done.md`, `050-fix.md`, `050-qa-review.md`

Cumulative diff: 21 insertions, 12 deletions. Far under the ~200-line halt heuristic.
Orchestrator verified scope independently via `git status --short` and `git diff --stat`.

### Halt conditions tripped
- None. The NEEDS FIXES verdict was handled by the one permitted fix round, which QA
  confirmed did not expand scope. No second fix round was needed.

### Notes for the owner
- **AC2 is open and needs you.** "Renders at 375px with no horizontal page scroll" was
  never observed by any agent. QA established with real tooling that this sandbox cannot do
  it at all, so no future fix round will close it either. Open the error page in device
  emulation at 375px and confirm the heading, detail text and "Back to home" link all sit
  inside the viewport. This is the same class of item as audit 046's Finding 4 (the
  owner-must-verify queue) and belongs on that checklist.
- The "Back to home link does not read as clickable" improvements item is still open by
  design. Code Review 042 assigned it to the M1 UI re-design so one shared link style is
  settled once; a one-off restyle here is exactly what that item warns against.
- Worth noting for the process: QA's round-1 blocker was correct, and the Engineer's
  departure from QA's suggested fix was also correct. QA then verified the departure and
  said so. That is the quality model working rather than two agents deferring to each other.
- Nothing was committed by any subagent.

### Round-1 QA report (archived — round 2 overwrote the file)
Verdict: NEEDS FIXES. One blocker: AC1 had no automated test coverage —
`grep -rn "px-4" tests/` and `grep -rn "max-w-xl" tests/` both returned zero matches, so
nothing in `tests/` asserted the padding was present, and the Engineer's verification was an
ad hoc uncommitted TestClient check rather than a regression test. Suggested fix: a one-line
`assert "px-4" in resp.text` against the existing `/test/unhandled` route. (Round 2 later
established this suggestion was itself insufficient — see the round-2 summary above.)
Everything else passed: AC3 green at 477, scope boundaries held (`base.html` byte-identical,
"Back to home" link untouched), improvements bookkeeping correct and asymmetric, fixture
`scope="module"` verified safe against cross-test leakage across all 15 other test files,
and the full review blocker checklist clean. AC2 recorded as owner-must-verify after the
headless-Chromium investigation described above.
