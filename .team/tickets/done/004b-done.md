## Implementation complete — 004b

**What I did:**
- Created `web/routes/auth.py` with `GET /auth/login` and `GET /auth/callback`
- Created `tests/test_auth_routes.py` covering all four acceptance criteria
- Updated `web/main.py` to register the auth router

**Files changed:**
- `web/routes/auth.py` (new) — login handler writes state nonce to `oauth_states`, callback validates/consumes nonce, exchanges code, writes session row, sets `session_id` cookie
- `tests/test_auth_routes.py` (new) — four tests using in-memory SQLite via dependency override; no live Yahoo API calls
- `web/main.py` (modified) — added `app.include_router(auth_router)`

**How to verify:**
- Run `.venv/bin/python -m pytest tests/test_auth_routes.py -v` — all 4 tests should pass
- Manual smoke test: set `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REDIRECT_URI` env vars; run `uvicorn web.main:app --reload`; navigate to `http://localhost:8000/auth/login`; complete Yahoo consent; confirm redirect to `/` with no 500 error; inspect the SQLite DB to confirm a row in `user_sessions` and no remaining row in `oauth_states`

**Scope notes:**
- Session middleware (`require_user` dependency) is not implemented — that is ticket 005. Routes other than `/auth/*` are currently unprotected.
- Token refresh (`_try_refresh`) is not wired up — also ticket 005.
- Demo mode is not affected — `/auth/*` routes are public by design and demo mode doesn't use them.

**Known limitations:**
- Tests patch `web.routes.auth.get_auth_url` and `web.routes.auth.exchange_code` (the names as imported in the route module) rather than `requests.post` directly. This is because `exchange_code` reads env vars (`YAHOO_CLIENT_ID`, `YAHOO_REDIRECT_URI`, `YAHOO_CLIENT_SECRET`) that aren't available in the test environment. The intent from the ticket — no live Yahoo API calls — is fully satisfied.
- The `_db_dep` generator is exposed as a module-level name so the test's `dependency_overrides` can reference it. This is a standard FastAPI testing pattern.
