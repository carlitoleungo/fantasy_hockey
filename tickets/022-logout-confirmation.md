# 022 — Logout: confirmation banner and correct redirect

## Status
ready

## Type
bug

## Touches
- web/routes/auth.py
- web/templates/home.html

## Why
Clicking "Logout" in the nav currently redirects the browser to `/auth/login`, which immediately starts a Yahoo OAuth round-trip. From the user's perspective, logging out looks identical to clicking "Overview" — the Yahoo consent screen appears with no indication that logout occurred. There is also no post-logout confirmation: after the OAuth round-trip completes the user lands on `/` looking at their league list, unable to tell whether they were just logged out and back in, or whether anything happened at all. This is confusing enough that users may click Logout repeatedly, generating multiple OAuth round-trips.

## Acceptance criteria
- [ ] After clicking Logout, the browser lands on `/?logged_out=1` (not `/auth/login`); no OAuth round-trip is triggered.
- [ ] A visible banner or notice on the home screen reads "You have been logged out" (or equivalent) when `?logged_out=1` is present in the query string.
- [ ] The banner is not shown on a normal `/` visit (no query param).
- [ ] The `session_id` cookie is deleted on logout (already true — verify it remains correct after the redirect change).
- [ ] `GET /auth/logout` with no session cookie still redirects to `/?logged_out=1` without error.

## Out of scope
- Persistent flash message infrastructure (server-side sessions, flash cookies) — a query-param approach is sufficient here
- Logout from the `/demo/...` routes (demo mode has no session)
- Styling beyond a simple inline notice (colour and layout polish is a separate pass)

## Notes for the Engineer
- In `web/routes/auth.py:101`, change the redirect target from `/auth/login` to `/?logged_out=1`. The `delete_cookie` call on line 102 is already correct — do not touch it.
- In `web/templates/home.html`, the home route passes `request` to the template (it extends `base.html`). Read `request.query_params.get("logged_out")` in the template (Jinja2: `{{ request.query_params.get("logged_out") }}`), or pass a `logged_out` boolean from the route handler — either is fine. A simple `{% if logged_out %}<p ...>You have been logged out.</p>{% endif %}` above the league list is sufficient.
- The home route is in `web/routes/home.py` (or wherever `/` is handled). If passing `logged_out` as a context variable is cleaner, read `request.query_params.get("logged_out") == "1"` in the handler and pass `logged_out=True/False` to the template.
- Do not redirect to `/auth/login` under any condition from the logout handler — that is the root cause.
- Check `tests/test_auth_routes.py` for the existing logout tests; update any assertion that expects a redirect to `/auth/login`.

## Verification
1. Start the server. Log in with a real Yahoo account.
2. Click "Logout" in the nav. Confirm: browser lands on `/?logged_out=1`; no Yahoo OAuth screen appears.
3. Confirm a "you have been logged out" notice is visible on the page.
4. Click the home link or navigate to `/`. Confirm: the banner is gone (no query param).
5. While logged out, click "Overview". Confirm: redirects to login (Yahoo OAuth), then back to `/` after auth completes — the normal re-auth flow still works.
6. Call `GET /auth/logout` with no cookie (curl or browser private window). Confirm: 302 to `/?logged_out=1`, no 500.

## Dependencies
- None
