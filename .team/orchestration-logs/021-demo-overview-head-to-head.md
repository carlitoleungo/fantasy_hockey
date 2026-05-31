## Orchestration log — 021-demo-overview-head-to-head

**Run started:** 2026-05-31 (session start)
**Run ended:** 2026-05-31
**Outcome:** completed

### Pre-flight
- Status check: pass (`ready`)
- Required-sections check: pass (all 8 sections present)
- Architectural-surface coverage: pass
  - Template structure (HTMX shell + fragment split): ticket cites "Decision 2026-04-19" in Notes for the Engineer; active superseding entry is 2026-05-30 but engineering guidance is identical. Citation sufficient.
  - `web/main.py` not in Touches: verified pre-flight that `overview_public_router` is already imported and registered in `web/main.py` (lines 16, 69) — no changes to `web/main.py` needed.
  - `data/demo.py` not touched (explicitly out of scope in ticket).

### Subagents spawned (in order)

1. **Engineer (round 1)**
   - Inputs: `.team/engineer.md`, `tickets/021-demo-overview-head-to-head.md`, `docs/DECISIONS.md`, `docs/LEARNINGS.md`
   - Output: code changes landed correctly; `tickets/021-done.md` NOT written; ticket Status NOT updated
   - Summary: Two new `@public_router.get` handlers added to `web/routes/overview.py`; `hx-get` in `head_to_head.html` de-hardcoded to `{{ table_url }}`; authenticated handlers updated to pass `table_url`; server verified returning 200 on demo routes and 302 on protected route. Handoff artifacts missing.

   **Blocker between round 1 and fix:** Engineer subagent ran in `don't ask` mode — file-edit tools were blocked. Permissions issue required owner to update `.claude/settings.json`. Once fixed, code changes were present in the files.

2. **Engineer (fix round — artifact-only)**
   - Inputs: `.team/engineer.md`, narrow instruction to write missing `tickets/021-done.md` and update Status; code changes already in place
   - Output: `tickets/021-done.md` written; Status updated to `qa`
   - Summary: Handoff document written with full AC self-check (static-inspection-only caveat noted), six-step QA guide, and one scope note about missing nav link.

3. **Test Engineer (round 1)**
   - Output: `tickets/021-qa.md`
   - Verdict: APPROVED
   - Summary: 345 tests passed (332 pre-existing + 13 new in `tests/test_demo_head_to_head_routes.py`). All 5 ACs verified manually: demo shell 200 with 12 team dropdowns and week selectors, `hx-get` pointing to `/demo/overview/head-to-head/table`, fragment returning partial HTML with tally results, no Yahoo API calls in logs, auth guard preserved (302 on unauthenticated `/overview/head-to-head`).

4. **Reviewer**
   - Output: `tickets/021-review.md`
   - Verdict: APPROVED
   - Summary: Scope clean, architecture clean. One artifact issue flagged: diff passed to Reviewer had a transcription error (duplicate `team_a: str` param) — confirmed as orchestrator copy-paste error, not present in actual code; QA's 345-test pass corroborates. `docs/improvements.md` updated: open "Compare two teams link hard-codes `/overview/head-to-head`" item (from review 020) marked unblocked now that `/demo/overview/head-to-head` exists.

### Files changed
- `web/routes/overview.py` (+88 lines): two demo handlers added to `public_router`; `table_url` added to both render paths of authenticated `head_to_head` handler
- `web/templates/overview/head_to_head.html` (-1 +1 line): `hx-get` de-hardcoded to `{{ table_url }}`
- `tests/test_demo_head_to_head_routes.py` (new, +13 tests): added by Test Engineer

### Halt conditions tripped
- **Permissions block (Engineer round 1):** Engineer subagent blocked by `don't ask` mode — could not write files. Surfaced to owner; owner updated `.claude/settings.json`. Not a design or architecture halt; resolved with owner action.
- **Missing handoff artifacts (Engineer round 1):** Engineer produced correct code but did not write `tickets/021-done.md` or update Status. Surfaced to owner; owner approved re-spawning Engineer for artifact-only round.

### Notes for the owner
- The orchestrator passed a slightly incorrect diff to the Reviewer (duplicate `team_a: str` in the fragment handler signature). The actual file is correct; this was a copy-paste error in the prompt. No code change needed, but worth being aware of in case the Reviewer's report references it.
- `docs/improvements.md` item "Compare two teams link hard-codes `/overview/head-to-head`" (from review 020) is now unblocked — the demo route exists. The fix (making the back-link a context variable) is a natural candidate for the next ticket touching `head_to_head.html` or the overview route.
- Nav link from home/demo landing to `/demo/overview/head-to-head` is explicitly out of scope for this ticket. Follow-up ticket needed.
