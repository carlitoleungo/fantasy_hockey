# 007 — Logout route

## Summary
Add `GET /auth/logout` to the auth router. The route deletes the caller's row from
`user_sessions`, clears the `session_id` cookie, and redirects to `/auth/login`. Without
this route users have no way to disconnect their Yahoo account — it is a go-live blocker.

## Acceptance criteria
- [ ] `GET /auth/logout` with a valid `session_id` cookie deletes the matching row from
  `user_sessions` and returns a 302 redirect to `/auth/login`
- [ ] `GET /auth/logout` with an unknown or missing `session_id` cookie still redirects
  to `/auth/login` with a 302 (no error — idempotent logout is the right UX)
- [ ] The `Set-Cookie` response header clears the `session_id` cookie (max_age=0 or
  expires in the past) so the browser removes it

## Files likely affected
- `web/routes/auth.py`
- `tests/test_auth_routes.py`

## Dependencies
- None (builds on the existing auth router and db_dep pattern)

## Notes for the engineer
- Add the logout handler to the existing `router` in `web/routes/auth.py`. No new file needed.
- Pattern to follow: read `session_id` from the cookie (same `Cookie(default=None)` pattern
  the session middleware uses in `web/middleware/session.py`), DELETE from `user_sessions`
  WHERE session_id = ?, commit, then return a `RedirectResponse("/auth/login", 302)` with
  the cookie cleared.
- To clear a cookie in FastAPI: `response.delete_cookie("session_id")`. Unlike `set_cookie`,
  `delete_cookie` does not need `httponly`/`samesite` flags — it just sets max_age=0.
- If `session_id` is None (no cookie), skip the DELETE and redirect anyway — idempotent.
- The `secure` flag on `set_cookie` in `callback` reads `HTTPS_ONLY` from env; use the same
  check on `delete_cookie` so the cookie is cleared on HTTPS deployments too.
- Tests should use the existing in-memory DB fixture pattern from `test_auth_routes.py`.
  Add: (1) logout with a valid session — row gone, 302; (2) logout with no cookie — still 302.

## Notes for QA
- Verify the row is actually gone from `user_sessions` after logout (not just that the
  redirect happened).
- Verify a second call to `GET /auth/logout` with the now-cleared cookie still returns 302
  (no 404 or 500).
- Verify the `Set-Cookie` response header is present and sets `max_age=0` (or equivalent
  expiry) so the browser removes the cookie.

---

## Tech Lead Review

**Complexity: S** — implemented and done. `web/routes/auth.py` has the handler; `tests/test_auth_routes.py` has Tests 5 and 6. No further action needed.

**Risks / notes:** None. One minor future cleanup: the per-request `cookies=` pattern in the TestClient produces a Starlette deprecation warning; harmless now, fix when touching the test file next.
