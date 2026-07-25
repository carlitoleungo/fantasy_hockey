## Orchestration log — 036b-demo-nav-adoption

**Run started:** 2026-07-25 16:36
**Run ended:** 2026-07-25 16:58
**Outcome:** completed (ticket promoted to `done`), with one halt-and-surface condition tripped at the final step — Reviewer raised two `should-fix` findings. Surfaced to the owner; no further spawns.

### Pre-flight
- Type check: pass (`feature`, not `audit`)
- Status check: pass (`ready`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- `Touches` non-empty: pass (3 paths — `web/routes/overview.py`, `web/routes/waiver.py`, `web/routes/projection.py`)
- Audit check: `.venv/bin/python scripts/audit_due.py` → **AUDIT NOT DUE** (weighted 3.5 / 5; highest audited ticket 31). Note: bare `python` is not on PATH — the script must be run with `.venv/bin/python`.
- Architectural-surface coverage: pass. Touches fall under the template-shell surface (`WORKFLOW.md` § Architectural-surface escalation list). Active covering decision: `docs/DECISIONS.md` 2026-07-03 "Nav shell: conditional on auth/demo state via shared shell-context; no second auth-derivation path", cited explicitly in the ticket's Notes for the Engineer, together with 2026-05-30 (`optional_user`, demo-route pairing) and 2026-04-19 (feature-link ordering). The 2026-07-25 entry extends 2026-07-03 rather than superseding it; nothing relevant sits in `docs/archive/decisions-superseded.md`.

### Model selection
- No `## Model` section and no `## Process` section in the ticket ⇒ full process, heuristic applied.
- Engineer: **opus** — `Process: full` with 3 paths in `Touches` (≥ 3 branch).
- Test Engineer: **opus** — same branch.
- Reviewer: **opus** — always.

### Subagents spawned (in order)
1. **Engineer (round 1)** — `fh-engineer`, opus
   - Inputs: `.team/engineer.md` (read from disk by the agent shim), the ticket, DECISIONS 2026-07-03 / 2026-07-25 / 2026-05-30 / 2026-04-19, `tickets/done/036a-nav-shell-foundation.md`, `web/routes/home.py` as the reference pattern, `docs/LEARNINGS.md`
   - Output: `tickets/036b-done.md`
   - Summary: Replaced all 12 explicit `selected_league_name` keys across the three route files with `shell_context()` spreads placed last in every dict literal. Authenticated handlers reuse the `require_user`-resolved user; demo handlers pass `shell_context(None, demo=True, league_name="Demo League")`. Deleted 036a's tripwire test and added 19 parametrised cases. Also migrated `/demo/overview/head-to-head`, a fourth full-page branch inside `overview.py`. `base.html` and `web/templates.py` needed no change. Suite: 437 passed. Ran two mutation probes (both reverted) confirming the new guard discriminates. Flagged that the authenticated browser walk needs live Yahoo OAuth it has no credentials for, and deliberately left a `Type: quality` improvements item on `projection.py` unfixed as a product call needing its own ticket.

2. **Test Engineer (round 1)** — `fh-test-engineer`, opus
   - Output: `tickets/036b-qa.md`
   - Verdict: **APPROVED**
   - Summary: Re-ran the suite independently — 437 passed, `test_nav_shell_qa.py` 30/30. Walked all four demo pages on a real uvicorn server with no cookie: identical nav (`Overview`, `Waiver`, `Projection`, `Log in with Yahoo`), 12/12 followed links returned 200 with redirects disabled, zero 3xx, no `/auth/logout` and no bare feature hrefs in any demo body, header reading `Demo League`. Confirmed zero explicit `selected_league_name` keys remain under `web/` and all 14 `shell_context()` call sites spread last; 12 of 24 `TemplateResponse` calls in the three files extend `base.html` and all 12 got shell context, the other 12 being fragments and none did. Own mutation probe (monkeypatching the bound helper, no source edits) confirmed the failure is silent and that the header-scoped `_header_left()` assertion catches it. Judged the `/demo/overview/head-to-head` migration required rather than creep, and AC3 adequately covered by automated tests with only visual/CSS left as owner-only.

3. **Reviewer** — `fh-reviewer`, opus
   - Output: `tickets/done/036b-review.md`
   - Verdict: **APPROVED**, no blockers
   - Summary: Scope clean — the `tests/test_nav_shell_qa.py` change is mandated by the ticket despite the file's absence from `Touches` (the `Touches` list was incomplete), and the head-to-head migration was required. Architecture clean — no second auth-derivation path, all four demo handlers take `request: Request` only and pass literal `None`, no new routes, ordering preserved, `base.html` and `web/templates.py` byte-unchanged, no conflict with the 2026-07-25 entry which sequences the default flip after this ticket. Re-ran the suite: 437 passed. Raised two `should-fix` and two `nit` findings, logged to `docs/improvements.md` rather than returned. Per its persona's non-negotiable rule, set Status to `done` and moved all four `036b-*.md` artifacts into `tickets/done/`.

### Files changed
- `web/routes/overview.py` (+11 -7)
- `web/routes/projection.py` (+3 -3)
- `web/routes/waiver.py` (+3 -3)
- `tests/test_nav_shell_qa.py` (+130 -6)
- `docs/improvements.md` (+27 -0) — written by the Reviewer, three new `Type: quality` entries
- `tickets/036b-demo-nav-adoption.md` → `tickets/done/` (Status `ready` → `done`), plus `036b-done.md`, `036b-qa.md`, `036b-review.md` in `tickets/done/`

Cumulative source+test diff at the point of the Touches check: ~168 lines, under the ~200-line heuristic. All changes remain uncommitted — the owner manages version control.

### Halt conditions tripped
- **"Reviewer raises any `blocker` or `should-fix`"** — tripped after the Reviewer step, the final step of the loop. Two `should-fix` findings, both logged to `docs/improvements.md` and classified non-blocking by the Reviewer, who nonetheless returned APPROVED and promoted the ticket. Nothing remained to spawn, so the run completed; the findings are surfaced to the owner below for a disposition decision rather than auto-actioned.

### Notes for the owner
- **Two `should-fix` findings need your call** (both now `Type: quality` entries in `docs/improvements.md`, neither a live defect):
  1. `test_authenticated_nav_links_return_200` is parametrised over a `path` its body never reads and is fully subsumed by the test directly above it — nine mocked renders for zero coverage. Delete it or drop the parametrisation.
  2. Nav/header assertions cover 7 of the 12 migrated branches. Authenticated `/overview/head-to-head` has no nav assertion anywhere, and none of the four empty-state branches is covered. All 12 are correct in this diff (both QA and the Reviewer read each), so this is a regression-guard gap — and it matters because the failure mode is silent.
- **The Reviewer changed the ticket Status despite the spawn prompt telling it not to**, citing its persona's non-negotiable promote-on-approval rule as overriding the task prompt. The outcome is correct (APPROVED ⇒ `done`), but the persona/prompt conflict is worth resolving in `.team/reviewer.md` or in the orchestrator's Reviewer spawn instruction so the two stop contradicting each other.
- **The authenticated browser walk in the ticket's Verification section was never run** — it needs live Yahoo OAuth over ngrok. QA and the Reviewer independently judged AC3 adequately covered by automated tests, reasoning that `shell_context()` cannot distinguish a mocked `CurrentUser` from a real one and the nav markup lives in an untouched template. What remains genuinely owner-only is visual/CSS confirmation in a real browser.
- **Two follow-ups the Reviewer flagged for the PM**, neither a 036b defect: the `base.html` "flags absent ⇒ authenticated nav" default flip promised by the DECISIONS 2026-07-25 entry is now unblocked (`error.html` is the only page still relying on the old default, and `auth_state_unknown` exists in neither `base.html` nor `common.py`, so that fix is still unimplemented); and the "Try the demo" home-page entry point is now the last gap in the demo journey.
- **One item deliberately left unfixed by the Engineer**, contrary to the default fix-quality-nits-on-touched-files rule: the `docs/improvements.md` "Goalie breakdown table omits the shared offense categories (Assists)" item on `web/routes/projection.py`. Its own text calls it a product call rather than a defect, and fixing it would change projection output on a ticket whose diff is otherwise pure context-dict plumbing. It needs its own ticket.
- Minor: the handoff note claims 21 new parametrised test cases; the actual count is 19.

### Round-1 QA report
Not applicable — QA passed on the first round, no fix round ran. `tickets/done/036b-qa.md` is the only QA report and was not overwritten.
