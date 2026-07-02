# 027 — Add tests for /demo/overview and /demo/overview/table routes

## Status
done

## Type
feature

## Touches
- tests/test_demo_overview_routes.py  *(new file, Engineer's call — may instead append to tests/test_overview_routes.py)*

## Why
The demo overview routes (`GET /demo/overview` and `GET /demo/overview/table`) were added in ticket 020 but never received test coverage. Any regression — a broken import, a bad template variable, a redirect accidentally added — would go undetected. Unauthenticated users land on these routes in demo mode, so breakage is immediately visible to all visitors.

## Acceptance criteria
- [ ] `GET /demo/overview` returns 200 with no session cookie present.
- [ ] `GET /demo/overview` response contains `table_url="/demo/overview/table"` (HTMX points at the demo fragment, not the authenticated one).
- [ ] `GET /demo/overview/table?week=N` returns 200 and the response body starts with `<div` (fragment, not a full page — no `<html>` tag, no `<!DOCTYPE`).
- [ ] `GET /demo/overview` with no session cookie returns 200, not 302.
- [ ] No call is made to `web.routes.overview.make_session` or `web.routes.overview.get_matchups` (live Yahoo path is never touched).

## Out of scope
- Testing table content correctness (rankings, stat columns, cell highlighting) — that belongs in the analysis layer tests.
- Edge cases for empty or missing demo data (the empty-state branch in `demo_overview`).
- Any changes to routes or templates.

## Notes for the Engineer
- **Patch target:** `data.demo.get_matchups` — the routes do a lazy `from data import demo as demo_module` then call `demo_module.get_matchups()`. Patch it the same way as `test_demo_head_to_head_routes.py` uses `patch("data.demo.get_matchups", return_value=df)`.
- **Fixture shape:** `_make_matchups_df()` needs columns `team_key`, `team_name`, `week`, `games_played`, and at least one stat column (e.g. `Goals`). Two teams × two weeks is sufficient — same minimal shape used in `test_demo_head_to_head_routes.py`.
- **Client:** `TestClient(app, follow_redirects=False)` — identical to all other route tests. No DB override needed; demo routes don't touch the session DB.
- **Fragment check:** `overview/_table.html` opens with `{% if ranked %}` then `<div class="overflow-x-auto">`. The response body will start with `<div` (or whitespace then `<div`) when data is present.
- **HTMX URL check:** template context key is `table_url`; its value for demo is `/demo/overview/table`. Assert that string appears in the shell response body and that `/overview/table` (the authenticated fragment path) does not.
- **File placement:** a new `tests/test_demo_overview_routes.py` keeps demo-mode coverage isolated and matches the `test_demo_head_to_head_routes.py` precedent. Appending to `tests/test_overview_routes.py` is acceptable if the Engineer prefers fewer files — either is fine.
- **Reference files:** `tests/test_demo_head_to_head_routes.py` (ticket 021) for overall shape; `tests/test_waiver_routes.py:158` for `test_demo_waiver_shell_returns_200` as a simpler single-route example.

## Verification
1. Run `pytest tests/test_demo_overview_routes.py -v` (or the relevant file) — all tests green.
2. Run the full suite (`pytest`) — no regressions in `test_overview_routes.py` or `test_overview_routes_qa.py`.
3. Confirm the three minimum test names are present: `test_demo_overview_shell_returns_200`, `test_demo_overview_table_returns_fragment`, `test_demo_overview_no_auth_required`.

## Dependencies
- None — routes and templates already exist from ticket 020.
