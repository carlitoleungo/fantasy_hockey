## Implementation complete — 004a

**What I did:**
- Removed all Streamlit dependencies from `auth/oauth.py`: `import streamlit`, all `st.secrets` reads, all `st.session_state` reads/writes
- Removed flat-file nonce helpers: `_save_state`, `_load_states`, `_save_states`, `_STATE_FILE`, `_STATE_TTL`
- Removed session-management functions: `get_session`, `try_restore_session`, `clear_session`
- Changed `_client_id()`, `_client_secret()`, `_redirect_uri()` to read from `os.environ["YAHOO_CLIENT_ID"]`, `os.environ["YAHOO_CLIENT_SECRET"]`, `os.environ["YAHOO_REDIRECT_URI"]`
- Changed `get_auth_url()` to return `(url: str, state: str)` tuple; caller is now responsible for persisting the nonce
- Removed `st.session_state.pop("tokens", None)` side effect from `_try_refresh`'s except block
- Created `db/schema.sql` with `oauth_states` and `user_sessions` table definitions
- Created `db/connection.py` with `get_db(path)` opening SQLite in WAL mode with `row_factory = sqlite3.Row`
- Deleted the 4 `validate_and_consume_state` test cases from `tests/test_oauth_helpers.py` and removed now-invalid imports (`MagicMock`, `sys.modules` mock, `_STATE_TTL`, `validate_and_consume_state`)

**Files changed:**
- `auth/oauth.py` — Streamlit removed; credentials from env vars; `get_auth_url` returns tuple; nonce/session functions removed; `_try_refresh` side effect removed
- `db/schema.sql` — new file with `oauth_states` and `user_sessions` DDL
- `db/connection.py` — new file with `get_db()` factory
- `tests/test_oauth_helpers.py` — removed 4 `validate_and_consume_state` tests and the `sys.modules` MagicMock preamble (no longer needed)

**How to verify:**
- `python3 -m py_compile auth/oauth.py` — should succeed with no output
- `grep -r "import streamlit" auth/` — should return nothing
- `python3 -m pytest tests/test_oauth_helpers.py -v` — 5 tests pass
- `python3 -m pytest` — all 237 tests pass (confirmed)
- `python3 -c "from db.connection import get_db; print('OK')"` — imports cleanly without Streamlit

**Scope notes:**
- `validate_and_consume_state` is gone; ticket 004b will implement DB-backed nonce lookup in the route handler
- `get_session`, `try_restore_session`, `clear_session` are gone; ticket 005 (session middleware) owns that responsibility

**Known limitations:**
- `db/connection.py` has not been exercised against a real SQLite file in this session — functional testing requires the `/data/` path to exist or a `DB_PATH` env override. The module itself compiles and imports cleanly.
