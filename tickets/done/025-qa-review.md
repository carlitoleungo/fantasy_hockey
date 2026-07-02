## QA + Review Report — 025 (Process: light)

**Ticket:** Parameterize hardcoded navigation links in overview templates
**Engineer handoff:** tickets/025-done.md
**QA date:** 2026-07-02

### Test plan (written from source/test inspection, before the Engineer's "How to verify")
- AC1: Render `/demo/overview` (no cookie), extract the "Compare two teams" anchor, confirm `href="/demo/overview/head-to-head"`. Fail if it is `/overview/head-to-head`.
- AC2: Render `/demo/overview/head-to-head` (no cookie), extract the "← Back to Leaderboard" anchor, confirm `href="/demo/overview"`. Must assert on the full anchor markup, not a bare `/overview` substring — base.html renders an unconditional nav `href="/overview"` that would mask a regression. Fail if the back anchor is `/overview`.
- AC3: Render authenticated `/overview` (valid session + league), confirm the compare anchor is `href="/overview/head-to-head"`. Fail if it is the demo route.
- AC4: Render authenticated `/overview/head-to-head`, confirm the back anchor (full markup) is `href="/overview"`. Fail if it is the demo route.
- Cross-check: all four handler branches (empty-state / not_enough_data as well as normal) pass the URL context vars, so the parameterization can't fall back to a template default that doesn't exist.

### Test results

| # | Acceptance criterion | Result | Observation |
|---|----------------------|--------|-------------|
| 1 | `/demo/overview` compare link → `/demo/overview/head-to-head` | PASS | Rendered anchor: `<a href="/demo/overview/head-to-head" class="text-sm text-gray-500 hover:text-gray-700">Compare two teams &rarr;</a>`. No `/overview/head-to-head` present. |
| 2 | `/demo/overview/head-to-head` back link → `/demo/overview` | PASS | Rendered back anchor: `<a href="/demo/overview" class="...">&larr; Back to Leaderboard</a>`. base.html nav `href="/overview"` appears exactly once (the header nav), so the full-anchor assertion is necessary and correctly distinguishes it. |
| 3 | Authenticated `/overview` compare link → `/overview/head-to-head` | PASS | Rendered anchor: `<a href="/overview/head-to-head" class="...">Compare two teams &rarr;</a>`. Demo route absent. |
| 4 | Authenticated `/overview/head-to-head` back link → `/overview` | PASS | Rendered back anchor: `<a href="/overview" class="...">&larr; Back to Leaderboard</a>`. Demo route absent. |

### Automated tests
- Command: `.venv/bin/python -m pytest tests/`
- Tests run: 349 — passed: 349, failed: 0
- AC coverage present from Engineer: TC7/TC8 in `tests/test_overview_routes.py` (auth shells) and TC-D14/TC-D15 in `tests/test_demo_head_to_head_routes.py` (demo shells). Each renders the real templates through the FastAPI app via TestClient and asserts the exact rendered `href`. The two back-link tests correctly assert the full anchor markup (href + class + link text) rather than a bare substring, so they are not masked by base.html's nav `/overview` link.
- New tests added by QA: none needed — AC coverage was complete.

### Manual verification
- I did not run an interactive browser click-through (no browser in this environment). Instead I rendered all four routes end-to-end through the FastAPI app (`TestClient`, real Jinja templates) with `data.demo.get_matchups` / `web.routes.overview.get_matchups` mocked, and extracted the actual nav anchors with a regex. The observed `href` values (table above) are the authoritative link targets a browser would follow. The only thing a human click-through would add is visual confirmation that the link is clickable/positioned correctly, which is cosmetic and not part of any AC — owner-may-verify, not required for approval.
- Confirmed by source read that all four handlers pass the URL context vars in **both** branches: `overview()` empty-state (lines 62–63) and normal (83–84); `head_to_head()` not_enough_data (150–153) and normal (180–181); `demo_overview()` (246–248 / 268–269); `demo_head_to_head()` (316–318 / 344–346). No branch renders the template without the variable.

### Demo mode
- Ticket does not add or modify any `data/` function; the demo path already exists (ticket 021). Demo parity verified directly: `/demo/overview` and `/demo/overview/head-to-head` render 200 without auth and the nav links point at the demo routes (AC1/AC2 above). Matches the live-mode rendering shape.

### Review checks (light-ticket always-blockers)
- Framework import in `data/` / `analysis/` / `auth/`: PASS — diff touches only `web/routes/overview.py`, two `web/templates/overview/*.html`, tests, and `docs/improvements.md`. No shared-layer files touched.
- Raw `stat['value']` without `_coerce()` / Yahoo collection indexed without `_as_list()`: PASS — no Yahoo response parsing added; change is pure URL string context passing.
- Per-entity Yahoo API loop where a bulk endpoint exists: PASS — no API calls added or changed.
- New live data function with no demo counterpart: PASS — no new data function; live and demo handlers were updated symmetrically.
- Contradiction of an active `docs/DECISIONS.md` entry: PASS — follows the existing `table_url` context-variable pattern (tickets 020/021); no decision contradicted.
- Diff escapes the ticket's `Touches` list: PASS — the three source files match `Touches` exactly. The additional changes (two test files, `docs/improvements.md`) are explicitly directed by the ticket's "Notes for the Engineer" (add tests; close the improvements item). The improvements.md item was correctly moved to the Closed section with a resolution note; the sibling "Back to Leaderboard" hardcode is covered by the same note.

### Issues found
None.

### Notes
- No pre-existing/out-of-scope bugs surfaced. The Engineer correctly left the separate `web/templates/base.html` "auth links shown to unauthenticated visitors" improvements item open (out of this ticket's `Touches`); that remains a valid future item.

### Verdict: APPROVED
