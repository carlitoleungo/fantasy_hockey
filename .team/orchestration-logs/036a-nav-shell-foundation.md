## Orchestration log — 036a-nav-shell-foundation

**Run started:** 2026-07-25 10:46
**Run ended:** 2026-07-25 11:05
**Outcome:** completed

### Pre-flight
- Status check: pass (`ready`)
- Type check: pass (`feature`, not `audit`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- `Touches` non-empty: pass (3 paths — `web/routes/common.py`, `web/templates/base.html`, `web/routes/home.py`)
- Audit check (`python3 scripts/audit_due.py`): **AUDIT NOT DUE** (weighted 2.5 / 5). Note: the `python` on PATH does not exist on this machine; `python3` is required to run the script.
- Architectural-surface coverage: pass. `web/templates/base.html` is on the WORKFLOW.md list ("Template structure — HTMX shell + fragment split"). The ticket cites the active `docs/DECISIONS.md` 2026-07-03 "Nav shell: conditional on auth/demo state via shared shell-context; no second auth-derivation path" (Option C), plus 2026-04-19 "Nav shell: minimal league label + logout in base.html" and 2026-05-30 "Shared route helpers". All three verified active (not in `docs/archive/decisions-superseded.md`).

### Model selection
No `## Model` section in the ticket, so the heuristic applied. No `## Process` section either, so the ticket is full process by WORKFLOW.md default.
- Engineer: **opus** — `Process: full` with 3 `Touches` paths (≥ 3) and an architectural-surface path (`base.html`).
- Test Engineer: **opus** — same heuristic branch.
- Reviewer: **opus** — always.

### Subagents spawned (in order)
1. **Engineer (round 1)** — `fh-engineer`, opus
   - Inputs: `.team/engineer.md` (read from disk by the agent shim), `tickets/036a-nav-shell-foundation.md`, the four cited `docs/DECISIONS.md` entries, `docs/LEARNINGS.md`
   - Output: `tickets/036a-done.md`
   - Summary: Added `shell_context(current_user, *, demo=False, league_name=None)` to `web/routes/common.py`, returning `is_authenticated` / `demo_mode` / `selected_league_name` from the user the route dependency already resolved (no second cookie/DB lookup). `base.html` now branches `demo_mode` → `is_authenticated is undefined or is_authenticated` → logged-out, so pages passing neither flag keep the authenticated nav. `web/routes/home.py` spreads the helper into both `GET /` branches, fixing the pre-existing `selected_league_name` drift on the authenticated home branch. `web/templates.py` untouched; no `context_processors`. Suite: 407 passed (403 baseline + 4 new tests). Moved the improvements item "Nav header shows auth links to unauthenticated visitors" to `docs/archive/improvements-closed.md` per the DoD note.
   - Flagged by the Engineer: they declined to apply the improvements item "Simplify redundant assertion in TC14 of `test_home_routes.py`" because the prescribed fix fails (`Your Leagues` is in the `<title>` of both branches, so the `split("</head>")` idiom the item calls unnecessary is what makes the test work). Item left open for re-wording. They also deliberately did not fold in the "Add demo mode entry point on home page" quality item, correctly deferring to the ticket's explicit exclusion over the persona's fix-while-in-scope rule.

2. **Test Engineer (round 1)** — `fh-test-engineer`, opus
   - Output: `tickets/036a-qa.md`
   - Verdict: **APPROVED**
   - Summary: Re-ran the suite independently — 407 passed, confirming the Engineer's number. Re-derived AC2 rather than trusting the handoff: rendered the authenticated home through the real handler, real `optional_user` against a real session row, and real Jinja, observing nav anchors in roadmap order (`/overview`, `/waiver`, `/projection`, `/auth/logout`) and the header label `Alpha League`. Ran uvicorn against a scratch `DB_PATH` and confirmed `app.db` unchanged at exit. AC3 verified by rendering `base.html` at HEAD and at working tree with an empty context — byte-identical anchors. Added `tests/test_nav_shell_qa.py` (14 supplementary tests, suite → 421 passed). No acceptance criterion required a manual inspection they could not perform.
   - Findings raised but not gating: TC18's `assert "Alpha League" in body` does not discriminate (proved by mutation probe — the content-area league list contains the same string), though pre-existing TC9 isolates the `<header>` and does catch it. Separately, AC4's literal `python3 -m pytest tests/` cannot succeed on this machine (`python3` is Homebrew 3.14 without pytest); the suite runs under `.venv/bin/python`. Pre-existing ticket boilerplate, not introduced by 036a.

3. **Reviewer** — `fh-reviewer`, opus
   - Output: `tickets/036a-review.md`
   - Verdict: **APPROVED** — no blockers, no should-fixes
   - Summary: Scope CLEAN, architecture CLEAN. Independently re-ran the suite (421 passed), confirmed `web/templates.py` untouched (rejected Option B stayed rejected), confirmed the new `common.py` → `middleware/session.py` import introduces no cycle, and confirmed the `is_authenticated is undefined` default yields the authenticated nav on an empty context. Ruled the dormant `demo_mode` branch in scope (the ticket's Notes require it and 036b scopes `base.html` out with an escalate-don't-edit clause). Ruled TC18's redundant assertion a nit. Ruled QA's `tests/test_nav_shell_qa.py` permitted supplementary coverage under DECISIONS 2026-05-31, since the Engineer shipped discriminating AC coverage first. Set Status to `done` and moved all four artifacts to `tickets/done/`.

No fix round was needed — QA approved on round 1.

### Files changed
- `web/routes/common.py` (+24 -0)
- `web/routes/home.py` (+3 -2)
- `web/templates/base.html` (+16 -4)
- `tests/test_home_routes.py` (+65 -0)
- `tests/test_overview_routes.py` (+25 -0)
- `tests/test_nav_shell_qa.py` (new, 239 lines — added by QA as supplementary coverage)
- `docs/archive/improvements-closed.md` (+7 -0, DoD item move)
- `docs/improvements.md` (Reviewer added two `Type: quality` entries and amended the test-scaffolding entry)

Source + Engineer-authored test diff is 139 lines, inside the ~200-line heuristic. QA's supplementary test file is additive verification, not implementation.

### Halt conditions tripped (if any)
None. Diff stayed inside `Touches` (plus test files and the DoD doc move the ticket explicitly authorises). No hedged verification claims — the Engineer stated plainly what they had not verified rather than hedging it, and QA then verified it directly. No new dependency, env var, or config knob. No DECISIONS conflict.

### Notes for the owner
- **Ticket 036b is now unblocked.** Two carry-forwards the Reviewer identified for it:
  1. `tests/test_nav_shell_qa.py::test_demo_pages_still_render_default_authenticated_nav` is a deliberate tripwire that **will fail when 036b lands** and must be deleted then.
  2. `shell_context()` can silently clobber `selected_league_name`. Fourteen context dicts across `overview.py`/`waiver.py`/`projection.py` pass that key explicitly (demo handlers use the literal `"Demo League"`). Spreading the helper after an explicit key without `league_name=` replaces the label with `None`. 036b must use e.g. `shell_context(None, demo=True, league_name="Demo League")`.
- **New improvements entries need PM triage.** The Reviewer filed a `Type: quality` item for `web/templates/error.html`, which extends `base.html` and passes no shell context, so error pages show the authenticated nav to logged-out visitors. It is not a drive-by fix: both render sites are FastAPI exception handlers at `web/main.py:48-65` with no resolved `CurrentUser` in scope, and passing `None` would give authenticated users the logged-out nav. The Reviewer notes this hits the `Revisit if` clause of DECISIONS 2026-07-03, so **a Tech Lead ruling is needed before an Engineer picks it up** — I did not spawn one.
- **The `python3 -m pytest tests/` boilerplate in ticket Verification sections is wrong for this machine.** The PATH `python3` has no pytest; the suite needs `.venv/bin/python -m pytest tests/`. Worth correcting in the ticket template so future ACs are literally runnable.
- **The improvements item "Simplify redundant assertion in TC14 of `test_home_routes.py`" prescribes a fix that breaks the test.** The Engineer tried it, caught the failure, and reverted. Its second claim (the `"<h1" in body` guard is always true) is correct, so the entry needs re-wording rather than closing.
- Working tree still contains unrelated pre-existing modifications (`.team/pm.md`, `CLAUDE.md`, `docs/DECISIONS.md`, `docs/LEARNINGS.md`, `docs/ROADMAP.md`, `docs/backlog.md`, `docs/archive/decisions-superseded.md`, `tickets/036b-*`) and untracked tickets 037/038/039 from before this run. Nothing in this run touched them. Commits are yours to make.

### Round-1 QA report
Not archived here — no round-2 QA ran, so `tickets/done/036a-qa.md` is the round-1 report unmodified.
