## Implementation complete — 007

**What I did:**
- Added `GET /auth/logout` handler to the existing `router` in `web/routes/auth.py`
- Added `Cookie` to the FastAPI imports (needed for `session_id: str | None = Cookie(default=None)`)
- Added two tests to `tests/test_auth_routes.py` covering the valid-session and no-cookie cases

**Files changed:**
- `web/routes/auth.py` — added `Cookie` import and `logout()` route handler; reads `session_id` cookie, deletes the matching `user_sessions` row if present, clears the cookie with `delete_cookie` (respects `HTTPS_ONLY` env var same as `callback`), redirects 302 to `/auth/login`
- `tests/test_auth_routes.py` — added Test 5 (valid session: row deleted, 302, `max-age=0` in Set-Cookie) and Test 6 (no cookie: still 302, no error)

**How to verify:**
- Run `source .venv/bin/activate && python -m pytest tests/test_auth_routes.py -v` — all 6 tests should pass
- Manually: log in, confirm you land on the app, visit `/auth/logout`, confirm you're redirected to `/auth/login` and a second visit to a protected route also redirects to login (session gone)
- Check `Set-Cookie` response header from `/auth/logout` includes `Max-Age=0` so the browser removes the cookie

**Scope notes:**
- None — implementation matches the ticket spec exactly

**Known limitations:**
- The deprecation warning in the test (`Setting per-request cookies=<...> is being deprecated`) is from Starlette's TestClient, not our code. It does not affect correctness. A future ticket could update the test to set the cookie on the client instance instead of per-request.
