## Code Review — 027

**Files reviewed:**
- `tests/test_demo_overview_routes.py` — new test file, 6 tests covering all five acceptance criteria; the only source change in the diff.

### Scope: CLEAN
Diff touches only `tests/test_demo_overview_routes.py`, exactly matching the ticket's `Touches` (Engineer took the "new file" option). No routes, templates, or `data/`/`analysis/`/`auth/` source modified — confirmed via `git status`. No "while I'm here" edits.

### Architecture: CLEAN
- **Patch targets are correct.** The live-path symbols `make_session` and `get_matchups` are imported into the `web.routes.overview` namespace (`overview.py:7,9`), so patching `web.routes.overview.make_session` / `web.routes.overview.get_matchups` correctly intercepts them for the AC5 never-called assertions. The demo routes lazily do `from data import demo as demo_module` then call `demo_module.get_matchups()` (`overview.py:234-236, 276-278`), so patching `data.demo.get_matchups` is the correct data-source swap. These are distinct symbols, so AC5 genuinely proves the live path is untouched.
- **AC4 no-auth is structurally sound:** `demo_overview` is on `public_router` with no `require_user` dependency (`overview.py:232-233`), so there is no redirect path to assert against — the 200 assertion is meaningful.
- Test structure mirrors the `test_demo_head_to_head_routes.py` precedent (same fixture shape, `TestClient(app, follow_redirects=False)`, same patch idiom).
- No framework-import-in-pure-layer concern (this is a test module; importing FastAPI/pandas in tests is expected).

### Verification adequacy
- All 5 ACs have automated coverage; re-ran `pytest tests/test_demo_overview_routes.py` → 6 passed. QA additionally drove both routes unpatched against real demo data, confirming the green tests aren't a mocking artifact.
- The AC2 adaptation is correct and stronger than the ticket's literal wording. The ticket said assert `table_url="/demo/overview/table"`, but `table_url` is a context key rendered as `hx-get="{{ table_url }}"`; `table_url` is set to `/demo/overview/table` at `overview.py:247,268`. Asserting the rendered `hx-get="/demo/overview/table"` present and `hx-get="/overview/table"` absent faithfully covers AC2's intent, and the `hx-get="` anchor correctly prevents the demo path matching the authenticated pattern as a substring.

### Security and data: CLEAN
No secrets, tokens, or session IDs in the test. No client-side auth assumptions (demo routes are public by design; no passwords involved). Static fixture data only; no live API calls.

### Issues
None. No blockers, should-fixes, or nits.

### Verdict: APPROVED
