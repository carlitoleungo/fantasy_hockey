# Code Review — 036b

**Reviewer date:** 2026-07-25
**QA verdict on entry:** APPROVED (`tickets/036b-qa.md`) — precondition met.

**Files reviewed:**
- `web/routes/overview.py` — 8 context dicts migrated across 4 full-page handlers; explicit `selected_league_name` keys removed, spread is last in every literal.
- `web/routes/waiver.py` — `waiver_shell` (auth) and `demo_waiver_shell` (demo) migrated; same shape.
- `web/routes/projection.py` — `projection_shell` (auth) and `demo_projection_shell` (demo) migrated; same shape.
- `tests/test_nav_shell_qa.py` — 036a tripwire deleted as the ticket mandated; 19 parametrised cases added covering the demo nav, the authenticated nav, and the demo-vs-auth difference.
- `tickets/036b-demo-nav-adoption.md` — Status `ready` → `qa` (normal workflow transition, not a code change).
- Read for context, not changed: `web/routes/common.py`, `web/templates/base.html`, `web/main.py`, `docs/DECISIONS.md` (2026-07-25, 2026-07-03, 2026-05-30, 2026-04-19 entries).

**Independently verified:** `.venv/bin/python -m pytest tests/` → `437 passed, 112 warnings in 1.13s`.

### Scope: CLEAN

Both extensions QA flagged are inside the ticket's intent, and I reach the same conclusion on my own reading.

| Extension | Judgment |
|---|---|
| `tests/test_nav_shell_qa.py` modified though absent from `Touches` | Required by the ticket, not creep. The Notes explicitly mandate deleting `test_demo_pages_still_render_default_authenticated_nav`, and AC4 requires new nav-difference assertions — neither is possible without touching a test file. The omission is in the ticket's `Touches` list, not in the Engineer's discipline. Choosing the existing file over a sixth copy of the `_make_db`/`ctx` scaffolding is also the right call given the open improvements item on that duplication. |
| `/demo/overview/head-to-head` migrated (a fourth full-page branch) | Required. The Notes say to cover *each* full-page branch that extends `base.html`, and `overview/head_to_head.html` does. It lives in `overview.py`, already in `Touches`. Leaving it out would have shipped the exact defect the ticket exists to fix, on a page reachable in one click from `/demo/overview`. |

No "while I'm here" cleanup. The three open improvements items on the touched files (goalie assists, two overview bugs, the waiver settings re-fetch) were correctly left alone — none is nav-related, one is an explicitly flagged product call. Surfacing the goalie-assists decision for review rather than guessing at it was the right instinct; I confirm the item's own text calls it a product call, so it needs a ticket, not a drive-by.

### Architecture: CLEAN

- **No second auth-derivation path (DECISIONS 2026-07-03).** Conformant. Authenticated handlers pass the `current_user` already resolved by `require_user`; no cookie read, no DB lookup, no context processor. Verified `shell_context()` itself only tests `current_user is not None`.
- **Demo handlers take no user dependency (DECISIONS 2026-05-30).** Confirmed by reading all four signatures: `demo_overview`, `demo_head_to_head`, `demo_waiver_shell`, `demo_projection_shell` each take `request: Request` only and pass a literal `None`.
- **Demo-route pairing (DECISIONS 2026-05-30).** No new routes registered; demo nav links point only at pre-existing demo counterparts (`base.html` untouched).
- **Feature-link ordering (DECISIONS 2026-04-19).** Preserved — the ordering lives in `base.html`, which this ticket does not touch, and is asserted against `DEMO_NAV`/`AUTHENTICATED_NAV` in tests.
- **DECISIONS 2026-07-25 (error-page nav).** No conflict. That entry sequences the `base.html` default flip *after* 036b as a separate ticket, and explicitly notes the two changes do not collide in either landing order. This diff leaves `error.html` as the sole remaining beneficiary of the "flags absent ⇒ authenticated nav" default, which is exactly the state that entry anticipates.
- **Out-of-scope files respected.** `web/templates/base.html` and `web/templates.py` are byte-unchanged, so the ticket's "escalate rather than edit" clause never had to fire.
- No framework imports in `data/`/`analysis/`/`auth/` (the diff never leaves `web/` and `tests/`), no Yahoo API calls added or changed, no new dependency, no implicit-decision drift — this ticket adopts an existing decided mechanism rather than establishing a convention.

**The central risk was handled correctly.** All 12 spreads are the final entry in their dict literal, and no explicit `selected_league_name` / `is_authenticated` / `demo_mode` key survives anywhere under `web/` outside the helper. The label assertion is `<header>`-scoped via `_header_left()`, so it genuinely discriminates — QA's mutation probe (independent of the Engineer's) proved the label vanishes on all seven pages under the trap while the page still returns 200 with a correct nav. That is the right test for a silent failure.

**Security:** nothing to flag. No tokens, session IDs, or PII enter a log or a template; no user input newly crosses an HTTP boundary; no SQL added outside the test fixture's parameterised insert; no cookie attributes touched.

### Issues

- **should-fix (logged, not blocking):** `test_authenticated_nav_links_return_200` is parametrised over `path` its body never reads, and is fully subsumed by `test_authenticated_feature_pages_render_authenticated_nav` directly above it — same three paths, same helper, and that test already asserts 200 alongside the nav set and header label. Nine mocked renders for zero coverage. Delete it, or drop the parametrisation.
- **should-fix (logged, not blocking):** Nav/header assertions cover 7 of the 12 migrated branches. Authenticated `/overview/head-to-head` has no nav assertion anywhere (`tests/test_head_to_head_routes.py` asserts only 200s), and none of the four empty-state branches is covered. Every one of the 12 is correct in this diff — I read them — so this is a regression guard gap, not a live defect. It matters because the empty-state branches are the likeliest place for a future edit to drop the spread, and the failure mode is silent.
- **nit:** The handoff says "21 new parametrised cases"; the actual count is 19. Immaterial, recorded so the number is not carried forward.
- **nit:** `"Demo League"` is now written as a literal in six demo call sites (four in `overview.py`). A module constant would centralise it, but the literal was already the pre-existing pattern at those same sites, so changing it is not something I'd ask for on this ticket.

Verification adequacy is good: QA exercised the ACs against a live uvicorn server with the real demo snapshot, followed all 12 demo nav hrefs with redirects disabled, confirmed all four demo fragments still render shell-free, and re-confirmed auth gating on the un-cookied feature routes. I agree with QA that AC3 does not require a live Yahoo walk — `shell_context()` cannot distinguish a mocked `CurrentUser` from a real one, and the nav markup lives in an untouched template. The residual owner-only check is visual/CSS, and no template changed.

### Verdict: APPROVED

New entries written to `docs/improvements.md` (the only file I modified):

1. **`test_authenticated_nav_links_return_200` is parametrised over an unused argument and adds no coverage** — `Type: quality`.
2. **Nav/header assertions cover 7 of the 12 `shell_context()` branches in the feature routes** — `Type: quality`.
3. **Post-036b stale comments about pages "not yet" passing `shell_context()`** — `Type: quality`; covers the stale comment in `tests/test_overview_routes.py::test_overview_renders_authenticated_nav_by_default` (flagged by both the Engineer and QA) and the now-narrowed `base.html` comment, which should be resolved by the DECISIONS 2026-07-25 default-flip follow-up rather than edited on its own.

**Follow-ups for the PM, not defects in this ticket:**

- The `base.html` default flip (absent flags ⇒ nav-free) was explicitly blocked on 036b by the DECISIONS 2026-07-25 forward commitment. It is now unblocked, and `error.html` is the only page still relying on the old default.
- "Add demo mode entry point on home page" (already open in `docs/improvements.md`) is now the last gap in the demo journey: a visitor can navigate within demo mode but still has no linked way in from `/`.
