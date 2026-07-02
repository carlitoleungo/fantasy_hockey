## Implementation complete — 025

**What I did:**
- Parameterized the "Compare two teams →" link in `overview/index.html` to use a
  `{{ head_to_head_url }}` context variable instead of the hardcoded
  `/overview/head-to-head`.
- Parameterized the "← Back to Leaderboard" link in `overview/head_to_head.html` to use a
  `{{ overview_url }}` context variable instead of the hardcoded `/overview`.
- Passed `head_to_head_url` from both branches (empty-state and normal) of `overview()`
  (`/overview/head-to-head`) and `demo_overview()` (`/demo/overview/head-to-head`).
- Passed `overview_url` from both branches (not_enough_data and normal) of
  `head_to_head()` (`/overview`) and `demo_head_to_head()` (`/demo/overview`).
- Added four route tests covering all four ACs.
- Closed the `docs/improvements.md` item '"Compare two teams" link hard-codes
  `/overview/head-to-head` in shared template' (moved to Closed with a ticket-025
  resolution note).

**Files changed:**
- `web/templates/overview/index.html` — compare link now `href="{{ head_to_head_url }}"`.
- `web/templates/overview/head_to_head.html` — back link now `href="{{ overview_url }}"`.
- `web/routes/overview.py` — added the two URL context vars to all four handlers, both
  branches each (8 context dicts total).
- `tests/test_overview_routes.py` — added TC7/TC8 for the authenticated shells.
- `tests/test_demo_head_to_head_routes.py` — added TC-D14/TC-D15 for the demo shells.
- `docs/improvements.md` — closed the resolved quality item.

**Acceptance criteria status (self-check):**
- [x] AC1: On `/demo/overview`, "Compare two teams →" targets `/demo/overview/head-to-head`
  — verified by `test_demo_overview_compare_link_targets_demo_route`: body contains
  `href="/demo/overview/head-to-head"` and does NOT contain `href="/overview/head-to-head"`.
- [x] AC2: On `/demo/overview/head-to-head`, "← Back to Leaderboard" targets `/demo/overview`
  — verified by `test_demo_head_to_head_back_link_targets_demo_route`: the back-link anchor
  renders with `href="/demo/overview"` and the authenticated back-link anchor is absent.
- [x] AC3: Authenticated `/overview`, "Compare two teams →" targets `/overview/head-to-head`
  — verified by `test_overview_compare_link_targets_authenticated_route`: body contains
  `href="/overview/head-to-head"` and does NOT contain `href="/demo/overview/head-to-head"`.
- [x] AC4: Authenticated `/overview/head-to-head`, "← Back to Leaderboard" targets `/overview`
  — verified by `test_head_to_head_back_link_targets_authenticated_route`: the back-link
  anchor renders with `href="/overview"` and the demo back-link anchor is absent.

**How to verify (for QA):**
- `.venv/bin/python -m pytest tests/` — full suite: 349 passed. (This environment has no
  system `pytest`; use the `.venv` interpreter.)
- Targeted: `.venv/bin/python -m pytest tests/test_overview_routes.py::test_overview_compare_link_targets_authenticated_route tests/test_overview_routes.py::test_head_to_head_back_link_targets_authenticated_route tests/test_demo_head_to_head_routes.py::test_demo_overview_compare_link_targets_demo_route tests/test_demo_head_to_head_routes.py::test_demo_head_to_head_back_link_targets_demo_route` — 4 passed.
- Manual (optional): `uvicorn web.main:app --reload`, then walk the ticket's Verification
  section (logged out via `/demo/overview` round-trip; logged in via `/overview` round-trip).

**Implementation note for QA (test-assertion nuance):**
- `web/templates/base.html` line 22 renders an unconditional nav link `href="/overview"`
  on every page (including demo). A bare `'href="/overview"' not in body` assertion would
  therefore be a false negative. The two back-link tests instead assert the full
  "← Back to Leaderboard" anchor markup (href + class + link text) so they distinguish the
  back link from the nav link. The compare-link tests use the bare `href="/overview/head-to-head"`
  substring, which is safe because `/overview/head-to-head` never appears in the nav.

**Scope notes:**
- The `docs/improvements.md` "Nav header shows auth links to unauthenticated visitors"
  quality item lives on `web/templates/base.html`, which is NOT in this ticket's `Touches`
  list and I did not touch it. I only observed base.html's nav while writing test
  assertions. Leaving it open for its own ticket.
- Fragment endpoints (`overview_table`, `demo_overview_table`, and the head-to-head table
  fragments) were correctly out of scope — neither link lives in a fragment template.

**Known limitations / things I couldn't fully test:**
- I did not run the browser walkthrough (no interactive browser in this environment). The
  four route tests exercise the real FastAPI app end-to-end (real templates rendered via
  TestClient) and assert the exact rendered `href` values per context, which covers each
  AC's observable behaviour. A human browser click-through is still worth a QA glance for
  visual confirmation but the link targets are verified by the tests.
