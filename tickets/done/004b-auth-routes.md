# 004b — Auth routes: /auth/login + /auth/callback

## Summary

Create `web/routes/auth.py` with two route handlers. `GET /auth/login` calls the refactored `get_auth_url()` (which returns a `(url, state)` tuple), writes the CSRF state nonce to the `oauth_states` DB table with a 300-second TTL, and returns HTTP 302 to Yahoo. `GET /auth/callback` reads `?code` and `?state`, validates and consumes the nonce from the DB (one-time use), calls `exchange_code`, stamps expiry, writes tokens to `user_sessions`, sets a `session_id` cookie, and redirects to `/`. Unit tests cover all four acceptance criteria using a mocked `requests.post` and an in-memory SQLite DB. Session middleware and token refresh are out of scope — those are ticket 005.

## Acceptance criteria

- [ ] `GET /auth/login` returns HTTP 302 with a `Location` header containing `login.yahoo.com`; a row in `oauth_states` with `expires_at ≈ now + 300` exists immediately after the call (verified in a test by querying the in-memory DB directly)
- [ ] `GET /auth/callback?code=FAKE&state=INVALID` returns HTTP 400; `requests.post` is mocked and `call_count == 0` confirms no outbound call to Yahoo was made
- [ ] Round-trip test: insert a state nonce into the test DB (TTL not expired), call the callback with that nonce and a mocked `exchange_code` returning a fake token dict; handler returns HTTP 302 to `/`; fake tokens are retrievable from the `user_sessions` table for that session
- [ ] A second call to `/auth/callback` with the same already-consumed nonce returns HTTP 400, confirming one-time use

## Files likely affected

- `web/routes/auth.py` (new)
- `tests/test_auth_routes.py` (new)
- `web/main.py` (modified — register auth router)

## Dependencies

- Requires 004a (`auth/oauth.py` refactored, `db/schema.sql`, `db/connection.py` in place)
- Requires 003 (FastAPI app must exist to register the router)

## Notes for the engineer

Route handlers receive a DB connection via `Depends(get_db)` from `db/connection.py`.

**Login handler:** call `get_auth_url()` → `(url, state)`; `INSERT INTO oauth_states VALUES (state, time.time() + 300)`; return `RedirectResponse(url, status_code=302)`.

**Callback handler:** `SELECT * FROM oauth_states WHERE state = ?`; if no row or `expires_at < time.time()`, return 400; `DELETE FROM oauth_states WHERE state = ?` (consume it); call `exchange_code(code)` (raises `requests.HTTPError` on failure — return 400); `session_id = secrets.token_urlsafe(32)`; `INSERT INTO user_sessions (session_id, access_token, refresh_token, expires_at, created_at) VALUES (...)`; return `RedirectResponse("/", status_code=302)` with `Set-Cookie: session_id=<value>; HttpOnly; SameSite=Lax; Max-Age=2592000` — include the `Secure` attribute only when `os.environ.get("HTTPS_ONLY") == "true"` (i.e. production). Omitting it locally allows the cookie to attach over plain HTTP during smoke testing.

**Tests:** use FastAPI's `TestClient` with an in-memory SQLite DB (`:memory:`) injected via a dependency override on `get_db`. Mock `requests.post` with `unittest.mock.patch`. Do not make live Yahoo API calls in tests.

**Do not implement token refresh** — that is ticket 005.

## Notes for QA

All four acceptance criteria must be covered by automated tests — no live API calls in CI. Manual smoke test: configure `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REDIRECT_URI` env vars with real credentials; start uvicorn; navigate to `/auth/login`; complete Yahoo's consent screen; confirm redirect to `/` with no 500 error; inspect the DB to verify the `user_sessions` row was written and the `oauth_states` row was deleted.

## Tech Lead Review

**Missing file: `web/main.py`.** The auth router must be registered with `app.include_router(auth_router)` in `web/main.py`. That file is not listed under "files likely affected." Without it, `/auth/login` and `/auth/callback` return 404. Add to the files list: `web/main.py` (modified — register auth router).

**Cookie `Secure` flag and local dev.** The Notes specify `Set-Cookie: ...; Secure; ...`. The `Secure` flag prevents browsers from sending the cookie over plain HTTP. Local uvicorn runs on HTTP (`http://localhost:8000`), so the OAuth round-trip will succeed but the session cookie will silently not attach on subsequent requests — every protected route returns 302 to `/auth/login`, making local smoke testing broken in a non-obvious way. Recommendation: set `secure=True` only when an `HTTPS_ONLY=true` (or `ENVIRONMENT=production`) env var is set; default to `secure=False` locally. Add a note for the engineer and a check in the manual smoke test instructions.

**`exchange_code` signature: no change needed.** After 004a, `_redirect_uri()`, `_client_id()`, and `_client_secret()` all read from `os.environ`. The call `exchange_code(code)` in the callback handler is correct as-is — no explicit credential params required.

**Files likely affected — corrected:**
- `web/routes/auth.py` (new)
- `tests/test_auth_routes.py` (new)
- `web/main.py` (modified — register auth router) ← **add this**

**Complexity: M** ✓ — confirmed. Four well-defined unit tests and two route handlers with clear pseudocode already in the Notes.

**Ordering**: Requires 004a (`auth/oauth.py` refactored, `db/schema.sql`, `db/connection.py` in place) and 003 (`web/main.py` must exist to register the router). Cannot start until both are merged; no parallelism available for this ticket.
