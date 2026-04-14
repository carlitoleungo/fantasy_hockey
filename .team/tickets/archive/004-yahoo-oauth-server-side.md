# 004 — Yahoo OAuth: initiate + callback (server-side)

## Summary

Replace the two Streamlit-specific parts of the OAuth flow — the flat-file CSRF nonce store and `st.session_state` token storage — with proper server-side equivalents. Two new route handlers are added: `GET /auth/login` (generates the Yahoo auth URL, stores a CSRF state nonce in the DB with a 300-second TTL, and redirects) and `GET /auth/callback` (validates the nonce, exchanges the code for tokens via Yahoo, stores tokens encrypted in the DB, and redirects to the app root). The existing pure logic in `auth/oauth.py` (`get_auth_url`, `exchange_code`, `_stamp_expiry`, `_is_valid`) is called directly from the new handlers — no logic is duplicated. Session middleware and token refresh are out of scope; those land in ticket 005.

## Acceptance criteria

- [ ] `GET /auth/login` returns HTTP 302 with a `Location` header containing `login.yahoo.com`, and a CSRF state nonce row exists in the DB with a TTL expiry ~300 seconds from now. Verify in a test by inspecting the `Location` header and querying the DB directly after calling the route.
- [ ] `GET /auth/callback?code=FAKE&state=INVALID` returns HTTP 400. Verify in a unit test that also confirms no outbound call to `api.login.yahoo.com/oauth2/get_token` was made (mock `requests.post` and assert `call_count == 0`).
- [ ] A valid round-trip can be simulated in a test: insert a state nonce into the DB (TTL not yet expired), call the callback handler with that nonce and a mocked `exchange_code` returning a fake token dict — the handler returns HTTP 302 to `/` and the fake tokens are retrievable from the DB for that session.
- [ ] A second request to `/auth/callback` with the same nonce (already consumed) returns HTTP 400, confirming one-time use.

## Files likely affected

- `web/routes/auth.py` (new — the two route handlers)
- `auth/oauth.py` (modified: remove `import streamlit`, `st.secrets` calls, and file-based nonce helpers `_save_state` / `_load_states` / `_save_states`; accept `client_id`, `client_secret`, `redirect_uri` as parameters or via a settings object)
- New DB migration or schema file for the `oauth_states` and `user_sessions` tables (path per `docs/ARCHITECTURE.md`)

## Dependencies

Requires 001 (ARCHITECTURE.md must name the DB technology and schema conventions) and 003 (the framework must be bootable before routes can be added).

## Notes for the engineer

**Removing the Streamlit dependency from `auth/oauth.py`**: The module currently does `import streamlit as st` and calls `st.secrets["yahoo"]["client_id"]` inside `get_auth_url` and `_redirect_uri`. Remove those calls and instead accept `client_id`, `client_secret`, and `redirect_uri` as explicit parameters (or read from `os.environ` / a settings object). The HTTP logic — `requests.post` to Yahoo, `_stamp_expiry`, `_is_valid` — is unchanged.

**Nonce store migration**: Remove `_save_state`, `_load_states`, `_save_states`, and the `_STATE_FILE` constant from `oauth.py`. The route handler is responsible for writing/reading the nonce to/from the DB. `validate_and_consume_state` can either be updated to accept a `states_dict` argument, or inlined directly into the callback handler — either approach is fine.

**Token storage**: After `exchange_code` succeeds, call `_stamp_expiry` on the returned token dict and write the access token, refresh token, and `expires_at` to the `user_sessions` table (encrypted at rest if the architecture doc specifies encryption). At the end of the callback handler, set a session cookie and redirect to `/`. Full session validation (checking that cookie on subsequent requests) is ticket 005's job — for this ticket, just set the cookie and redirect.

**`_redirect_uri` helper**: Currently reads `st.secrets`. After this ticket it should read from `os.environ["YAHOO_REDIRECT_URI"]` or equivalent.

**Do not implement token refresh here** — that is ticket 005.

## Notes for QA

Do not test against the live Yahoo API in CI. All acceptance criteria must be verifiable with mocked `requests.post`. Manual smoke test in a review environment: configure real Yahoo OAuth credentials (`YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REDIRECT_URI` env vars), navigate to `/auth/login`, complete Yahoo's consent screen, and confirm you land at the app root without a 500 error. Inspect the DB directly to verify the tokens row was written and the nonce row was deleted.

## Tech Lead Review

**Files likely affected — incomplete.** The ticket lists `web/routes/auth.py`, `auth/oauth.py`, and a DB schema file. Two additional files are missing and are required before the route handlers can run:
- `db/schema.sql` — `CREATE TABLE oauth_states (state TEXT PRIMARY KEY, expires_at REAL); CREATE TABLE user_sessions (session_id TEXT PRIMARY KEY, access_token TEXT, refresh_token TEXT, expires_at REAL, created_at REAL);`
- `db/connection.py` — `get_db()` factory with WAL mode and `row_factory = sqlite3.Row`

Without these, the route handler has nowhere to write nonces.

**Complexity: L** (> 30 min). Three concerns interact: refactoring `auth/oauth.py` (must not break 002's test suite), writing the DB layer, and implementing + testing two route handlers with mocked HTTP. Recommend splitting:

- **004a** — Refactor `auth/oauth.py` (remove `import streamlit`, parameterise `client_id`/`client_secret`/`redirect_uri`, remove `_save_state`/`_load_states`/`_save_states`/`_STATE_FILE`) + `db/schema.sql` + `db/connection.py`. Run 002's test suite to confirm no regressions. **Complexity: S.**
- **004b** — `web/routes/auth.py` (`/auth/login` + `/auth/callback`) with acceptance-criteria unit tests. **Complexity: M.**

**Hidden dependency:** 002 must be merged before 004a begins so the `auth/oauth.py` refactor has a test safety net. 003 must be merged before 004b so the FastAPI app exists to register the new router.

**Superseded by 004a and 004b.**
