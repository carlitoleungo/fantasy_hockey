# 005 — Session middleware + transparent token refresh

## Summary

Add a middleware layer (or per-route decorator, depending on the framework chosen in ticket 001) that runs on every incoming request to a protected route. It validates that a session cookie exists and that the Yahoo access token is not expired within a 60-second buffer, transparently refreshes the token if needed using the existing `_try_refresh` logic in `auth/oauth.py`, and exposes a `current_user` object (containing valid tokens and session identity) to route handlers. Routes that do not require authentication — `/auth/login`, `/auth/callback`, and any demo routes — are explicitly exempted. An expired refresh token results in a redirect to `/auth/login` and deletion of the stale session row, not a 500 error.

## Acceptance criteria

- [ ] A request to any protected route (e.g. `GET /api/leagues`) with no session cookie returns HTTP 302 to `/auth/login`. Verify with a test client request asserting `response.status_code == 302` and `response.headers["Location"].endswith("/auth/login")`.
- [ ] A request with a valid session cookie and a non-expired access token (`expires_at = time.time() + 120`) returns HTTP 200 without calling the Yahoo token endpoint. Verify in a unit test by mocking `requests.post` and asserting `call_count == 0` after the request.
- [ ] A request with a valid session cookie and an access token expiring in 30 seconds (`expires_at = time.time() + 30`, within the 60-second buffer) triggers a token refresh: `requests.post` is called exactly once, the new tokens are written to the DB, and the response is HTTP 200. Verify in a unit test that mocks `requests.post` to return a fresh token payload with `expires_in=3600`.
- [ ] A request with a valid session cookie but a refresh token that Yahoo rejects (mock `requests.post` to return HTTP 401) results in HTTP 302 to `/auth/login` and the session row is deleted from the DB.
- [ ] The routes `/auth/login`, `/auth/callback`, and `/demo` (or their equivalents per `docs/ARCHITECTURE.md`) are exempt from the middleware: a request to any of them without a session cookie returns that route's normal response, not a redirect to `/auth/login`.

## Files likely affected

- `web/middleware/session.py` (new — the middleware or decorator implementation)
- `auth/oauth.py` (minor: ensure `_try_refresh` and `_is_valid` accept a tokens dict and config directly rather than reading from `st.session_state` or `st.secrets` — this change should already be complete from ticket 004)
- `web/routes/auth.py` (from ticket 004 — add exemption annotation if the framework uses decorators, or register the path prefix in the exemption config)

## Dependencies

Requires 004 — the OAuth callback must be writing tokens to the DB before the middleware can read them.

## Notes for the engineer

The core logic already exists in `auth/oauth.py`. `_is_valid(tokens)` checks `time.time() < tokens["expires_at"] - TOKEN_EXPIRY_BUFFER_SECONDS` (60-second buffer). `_try_refresh(tokens, client_id, client_secret)` posts to Yahoo with `grant_type=refresh_token` and returns a new stamped token dict or `None` on failure. Both functions should be callable from the middleware without modification after ticket 004's refactor removes the Streamlit dependency.

**Framework-specific patterns**:
- **FastAPI**: implement as a `Middleware` class or a `Depends` dependency injected into protected routes. A `Depends` approach makes exemptions explicit (unauthenticated routes simply don't declare the dependency).
- **Flask**: implement as a `before_request` hook registered on protected blueprints; unprotected routes live in a separate blueprint that doesn't register the hook.
- Follow whatever pattern `docs/ARCHITECTURE.md` specifies.

**`current_user` object**: pass to route handlers as a simple dataclass or dict containing at minimum `session_id: str`, `access_token: str`, `expires_at: float`. Route handlers must not call `_is_valid` themselves — the middleware guarantees the token is valid by the time the handler runs.

**Exemption list**: store exempt path prefixes as a `frozenset` constant or configuration value, not as inline string comparisons. This makes it easy to add new public routes later without hunting through middleware logic.

**`_try_refresh` exception scope**: `_try_refresh` catches only `requests.HTTPError`. Network-level failures (timeout, DNS) will propagate uncaught. The middleware must wrap its `_try_refresh` call in a `except requests.RequestException` block and treat any failure the same as a `None` return — redirect to login and delete the session row.

**Key edge case**: token with `expires_at = time.time() + 59` must trigger refresh; `expires_at = time.time() + 61` must not. Write a parameterised test covering both boundaries. Also verify the middleware does not refresh on every request for a healthy session — two sequential requests with the same session cookie and a healthy token should result in zero `requests.post` calls total.

## Notes for QA

Run two sequential requests with the same session to confirm the middleware is not refreshing on every hit. Also test the boundary values explicitly: `expires_at = now + 59` (refresh expected) and `expires_at = now + 61` (no refresh). Verify the DB state after each scenario: after a successful refresh the old token row is replaced with new values; after a refresh failure the session row is gone.

## Tech Lead Review

**Files likely affected — correct.** `web/middleware/session.py`, `auth/oauth.py` (already clean after 004a), `web/routes/auth.py` (exemption registration). No missing files.

**Complexity: M** (15–30 min). The core logic (`_is_valid`, `_try_refresh`) already exists in `auth/oauth.py` and will be Streamlit-free after 004a. The work is wiring: implement `require_user` as a FastAPI `Depends`, read session cookie, query DB, call existing helpers, update or delete the row, inject `CurrentUser`. Parameterised boundary tests (now+59 / now+61) and the double-request no-refresh test add modest but important test scope.

**Hidden dependencies:**
- Requires 004b to be merged (tokens written to DB by the callback handler).
- Requires 002 to be merged (so `_is_valid` and `_try_refresh` have test coverage before middleware relies on them).
- `_try_refresh` in the current `auth/oauth.py` reads `st.session_state` to clear tokens on failure — that call must be removed in 004a before this middleware can call `_try_refresh` safely outside Streamlit.

**No split needed** — M is within target.
