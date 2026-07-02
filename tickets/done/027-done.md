## Implementation complete — 027

**What I did:**
- Added test coverage for the previously-untested demo overview routes (`GET /demo/overview` and `GET /demo/overview/table`) in a new isolated test file, matching the `test_demo_head_to_head_routes.py` precedent.
- Patched `data.demo.get_matchups` (the lazy-imported module attribute the routes call) so no live Yahoo path is exercised.
- No routes, templates, or non-test source were modified.

**Files changed:**
- `tests/test_demo_overview_routes.py` — new file, 6 tests covering all five acceptance criteria (includes the three required test names).

**Acceptance criteria status (self-check):**
- [x] AC1: `GET /demo/overview` returns 200 with no session cookie — `test_demo_overview_shell_returns_200` asserts 200 (TestClient sends no cookies). PASSED.
- [x] AC2: response contains the demo table URL, not the authenticated one — `test_demo_overview_table_url_targets_demo` asserts `hx-get="/demo/overview/table"` present and `hx-get="/overview/table"` absent (the `hx-get="` anchor prevents the authenticated path matching the demo path as a substring). PASSED.
- [x] AC3: `GET /demo/overview/table?week=N` returns 200 and a bare fragment — `test_demo_overview_table_returns_fragment` asserts 200, body `.lstrip().startswith("<div")`, no `<html`, no `<!DOCTYPE`. PASSED.
- [x] AC4: no session cookie returns 200, not 302 — `test_demo_overview_no_auth_required` asserts `status_code == 200` and `!= 302`. PASSED.
- [x] AC5: live Yahoo path never touched — `test_demo_overview_no_yahoo_calls` and `test_demo_overview_table_no_yahoo_calls` patch `web.routes.overview.make_session` and `web.routes.overview.get_matchups` and assert both `assert_not_called()`. PASSED.

**How to verify (for QA):**
- `.venv/bin/python -m pytest tests/test_demo_overview_routes.py -v` — 6 tests, all green.
- `.venv/bin/python -m pytest` — full suite 355 passed, no regressions in `test_overview_routes.py` or `test_overview_routes_qa.py`.
- Confirm the three minimum test names are present: `test_demo_overview_shell_returns_200`, `test_demo_overview_table_returns_fragment`, `test_demo_overview_no_auth_required` (all shown in the `-v` output above).

**Scope notes:**
- AC2's ticket wording (`table_url="/demo/overview/table"`) describes the context key; the template actually renders it as `hx-get="/demo/overview/table"`. I asserted against the rendered form, which is the accurate and robust check (and matches the head-to-head precedent). No literal `table_url="..."` string exists in the response body.
- Out-of-scope branches (empty/missing demo data empty-state, table content correctness) were intentionally not tested per the ticket.

**Known limitations / things I couldn't fully test:**
- None. All five acceptance criteria are covered by automated tests; no purely-visual criteria in this ticket.
