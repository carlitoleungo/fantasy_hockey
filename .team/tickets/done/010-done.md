## Implementation complete — 010

**What I did:**
- Added `make_session(access_token)` to `auth/oauth.py` (public API section, below `exchange_code`)
- Added `league_key TEXT` (nullable) column to `user_sessions` in `db/schema.sql`
- Added startup migration in `web/main.py` using the `lifespan` context manager (not the deprecated `on_event` handler): runs `ALTER TABLE user_sessions ADD COLUMN league_key TEXT`, wrapped in `try/except sqlite3.OperationalError` for idempotency
- Added `test_make_session_sets_authorization_header` to `tests/test_oauth_helpers.py`
- Closed the open `improvements.md` item for `test_oauth_helpers.py` — the test already used `TOKEN_EXPIRY_BUFFER_SECONDS - 1`; no code change was needed

**Files changed:**
- `auth/oauth.py` — added `make_session` function (4 lines)
- `db/schema.sql` — added `league_key TEXT` to `user_sessions` CREATE TABLE
- `web/main.py` — replaced `app = FastAPI()` with a lifespan-based factory that runs the `ALTER TABLE` migration at startup; added imports for `sqlite3`, `asynccontextmanager`, `get_db`
- `tests/test_oauth_helpers.py` — added `make_session` to import list, added one new test
- `docs/improvements.md` — closed the `test_oauth_helpers.py` improvement item (pre-existing fix confirmed)

**How to verify:**
- Run `python3 -m pytest tests/test_oauth_helpers.py -v` — all 6 tests including `test_make_session_sets_authorization_header` should pass
- Create a fresh DB: `sqlite3 /tmp/test.db < db/schema.sql`, then run `SELECT name FROM pragma_table_info('user_sessions')` — confirm `league_key` appears
- Verify migration idempotency: run the `ALTER TABLE user_sessions ADD COLUMN league_key TEXT` statement twice on the same DB and confirm no unhandled exception (the try/except swallows the `OperationalError`)
- Start the app with `uvicorn web.main:app --reload` against an existing DB that predates this column — it should start without error and `league_key` should appear in the table schema

**Scope notes:**
- None — both changes are exactly as specified in the ticket

**Known limitations:**
- The FastAPI test suite (`test_auth_routes.py`, `test_error_handling.py`, `test_session_middleware.py`) requires a virtual environment with `fastapi` installed and cannot run against the system Python. These failures are pre-existing and unrelated to this ticket. Verified 239 non-FastAPI tests all pass.
