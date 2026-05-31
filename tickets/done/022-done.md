## Implementation complete — 022

**What I did:**
- Changed the logout redirect target from `/auth/login` to `/?logged_out=1` in `web/routes/auth.py`
- Added a "You have been logged out." banner to `web/templates/home.html` that renders only when `?logged_out=1` is present in the query string
- Updated three test assertions in `tests/test_auth_routes.py` (Tests 5, 6, 7) that expected `/auth/login` as the redirect location — all now assert `/?logged_out=1`
- Closed the "Logout provides no confirmation and re-auth is invisible" improvement item in `docs/improvements.md`

**Files changed:**
- `web/routes/auth.py` — line 101: `RedirectResponse("/auth/login", ...)` → `RedirectResponse("/?logged_out=1", ...)`; cookie deletion on line 102 is unchanged
- `web/templates/home.html` — added `{% if request.query_params.get("logged_out") == "1" %}` banner above the league list heading
- `tests/test_auth_routes.py` — updated location assertions in `test_logout_valid_session_deletes_row_and_redirects`, `test_logout_no_cookie_redirects`, and `test_logout_unknown_session_id_redirects`

**Note on Touches:** `tests/test_auth_routes.py` is not listed in the ticket's `Touches` list, but the ticket notes explicitly say to update assertions that expect `/auth/login`. Leaving those assertions unmodified would cause the entire test suite to fail on the route change. Updated them as directed; flagging for the PM to add `tests/test_auth_routes.py` to the Touches list retroactively if the process requires it.

**Acceptance criteria status (self-check):**
- [x] AC1: After clicking Logout, browser lands on `/?logged_out=1`; no OAuth round-trip — verified via `test_logout_valid_session_deletes_row_and_redirects` asserting `location == "/?logged_out=1"`, and by inspecting `auth.py` line 101 directly.
- [x] AC2: Visible banner reads "You have been logged out" when `?logged_out=1` present — template renders `<p>You have been logged out.</p>` inside `{% if request.query_params.get("logged_out") == "1" %}`. Confirmed template edit is correct.
- [x] AC3: Banner not shown on normal `/` visit — banner is conditional on the query param equalling `"1"`; absent param returns `None`, which is falsy, so the block is skipped.
- [x] AC4: `session_id` cookie deleted on logout — `delete_cookie` call on line 102 was already correct and was not touched; `test_logout_valid_session_deletes_row_and_redirects` asserts `max-age=0` in `Set-Cookie`.
- [x] AC5: `GET /auth/logout` with no session cookie redirects to `/?logged_out=1` without error — `test_logout_no_cookie_redirects` and `test_logout_no_cookie_still_clears_set_cookie_header` both pass.

**How to verify (for QA):**
1. Start server: `source .venv/bin/activate && uvicorn web.main:app --reload`
2. Log in with a real Yahoo account. Confirm you land on `/`.
3. Click "Logout" in the nav. Confirm: browser URL is `/?logged_out=1`; no Yahoo OAuth screen appears; the banner "You have been logged out." is visible on the page.
4. Navigate to `/` (remove the query param). Confirm: banner is gone.
5. Click "Overview" (while logged out). Confirm: redirects to Yahoo OAuth, then back to `/` after auth completes — normal re-auth flow still works.
6. In a private window (no cookie): `curl -I http://localhost:8000/auth/logout`. Confirm: `HTTP/1.1 302` with `Location: /?logged_out=1` and no 500 error.
7. Run the automated suite: `.venv/bin/python3.11 -m pytest tests/test_auth_routes.py -v` — all 8 tests pass (verified locally).

**Scope notes:**
- Flash message infrastructure (server-side sessions, flash cookies) remains out of scope as the ticket specifies.
- The logout link in `base.html` was not inspected — it was already pointing to `/auth/logout` and does not need to change.

**Known limitations / things I couldn't fully test:**
- The banner rendering was verified by code inspection only. Browser rendering (correct styling, visibility in different viewport sizes) was not verified — the app was not started because OAuth credentials are not available in this environment. The template change is a single conditional `{% if %}` block with no logic beyond a string comparison, so browser verification is low risk.
- The `delete_cookie` `secure` flag behaviour on localhost (where `HTTPS_ONLY` is unset) was not tested in a live browser. The unit tests confirm the `max-age=0` header is present regardless.
