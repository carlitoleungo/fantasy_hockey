# 004a — Refactor auth/oauth.py + DB layer

## Summary

Remove all Streamlit dependencies from `auth/oauth.py`: the `import streamlit` statement, all `st.secrets` credential reads, all `st.session_state` token reads/writes, and the flat-file nonce helpers (`_save_state`, `_load_states`, `_save_states`, `_STATE_FILE`). Credentials move to `os.environ`. Session-state functions (`get_session`, `try_restore_session`, `clear_session`) are removed — those responsibilities move to middleware in ticket 005. `get_auth_url()` is changed to return a `(url, state)` tuple so the caller can persist the nonce. Also create `db/schema.sql` and `db/connection.py` per the architecture spec. The 002 test suite must pass without modification after this refactor.

## Acceptance criteria

- [ ] `import streamlit` is gone from `auth/oauth.py`; `python -m py_compile auth/oauth.py` succeeds with Streamlit absent from the environment
- [ ] `_save_state`, `_load_states`, `_save_states`, and `_STATE_FILE` are removed from `auth/oauth.py`
- [ ] `_client_id()`, `_client_secret()`, and `_redirect_uri()` read from `os.environ["YAHOO_CLIENT_ID"]`, `os.environ["YAHOO_CLIENT_SECRET"]`, and `os.environ["YAHOO_REDIRECT_URI"]` respectively
- [ ] `get_auth_url()` returns a `(url: str, state: str)` tuple; caller is responsible for persisting the nonce
- [ ] `db/schema.sql` contains `CREATE TABLE IF NOT EXISTS oauth_states (state TEXT PRIMARY KEY, expires_at REAL);` and `CREATE TABLE IF NOT EXISTS user_sessions (session_id TEXT PRIMARY KEY, access_token TEXT, refresh_token TEXT, expires_at REAL, created_at REAL);`
- [ ] `db/connection.py` exports `get_db(path: str | None = None) -> sqlite3.Connection` opening the DB in WAL mode with `row_factory = sqlite3.Row`
- [ ] The four test cases in `tests/test_oauth_helpers.py` covering `validate_and_consume_state` are deleted as part of this ticket (the function is removed; DB lookup in ticket 004b replaces its behavior). All remaining tests in `tests/test_oauth_helpers.py` pass without modification.
- [ ] `_try_refresh` returns `None` on refresh failure with no other side effects; the `st.session_state.pop("tokens", None)` call at `auth/oauth.py:187` is removed

## Files likely affected

- `auth/oauth.py`
- `db/schema.sql` (new)
- `db/connection.py` (new)

## Dependencies

- Requires 002 to be merged (provides the test safety net for the `auth/oauth.py` refactor)

## Notes for the engineer

**Functions to preserve with logic unchanged:** `exchange_code`, `_stamp_expiry`, `_is_valid`, `_try_refresh`. `_try_refresh` currently calls `st.session_state.pop("tokens", None)` on refresh failure — remove that side effect; callers own session cleanup. `validate_and_consume_state` can be removed entirely; the route handler (004b) will do the DB lookup directly. `get_auth_url` should return `(url, state)` rather than void+side-effect so the caller can write the nonce to the DB.

**`db/connection.py` pattern** (from `docs/ARCHITECTURE.md`): `conn = sqlite3.connect(path, check_same_thread=False)`, `conn.execute("PRAGMA journal_mode=WAL")`, `conn.row_factory = sqlite3.Row`. Default path from `os.environ.get("DB_PATH", "/data/app.db")`.

**Do not implement token refresh changes here** — `_try_refresh` logic is preserved as-is (minus the `st.session_state` side effect); refresh middleware is ticket 005.

## Notes for QA

Run `pytest` before and after the refactor and confirm identical pass/fail counts. Verify no `import streamlit` remains: `grep -r "import streamlit" auth/`. Confirm `db/connection.py` can be imported in a clean venv without Streamlit installed.

## Tech Lead Review

**Conflict — AC and Notes contradict each other on `validate_and_consume_state`.** The Notes say "validate_and_consume_state can be removed entirely" but the AC says "002 test suite passes without modification." Four test cases in `tests/test_oauth_helpers.py` (written in ticket 002) directly import and test `validate_and_consume_state`. If the function is removed, those tests fail with `ImportError`, breaking the stated AC. **Resolution**: revise the last AC to read: "The four test cases in `tests/test_oauth_helpers.py` covering `validate_and_consume_state` are deleted as part of this ticket (the function is removed; the DB lookup in ticket 004b replaces its behavior). All remaining tests in `tests/test_oauth_helpers.py` pass without modification."

**Missing AC: `_try_refresh` side effect.** `auth/oauth.py` line 187 calls `st.session_state.pop("tokens", None)` inside `_try_refresh`'s `except` block. The Notes say to remove this, but there is no explicit AC for it. If left in, `py_compile` passes (Streamlit is MagicMocked at import time) but ticket 005's middleware will crash at runtime when it calls `_try_refresh` outside Streamlit. Add this AC: "`_try_refresh` returns `None` on refresh failure with no other side effects; the `st.session_state.pop` call at `auth/oauth.py:187` is removed."

**Files likely affected — complete.** `auth/oauth.py`, `db/schema.sql`, `db/connection.py`. The `db/__init__.py` stub from ticket 003 is already present; no additional files needed.

**Complexity: S** ✓ — confirmed. Bounded refactor with clear inputs and outputs. The two issues above are the entire risk surface; both have unambiguous resolutions.

**Ordering**: Requires 002 to be merged (test baseline must exist before refactoring the tested module). Parallelisable with 006 and any work not touching `auth/oauth.py`.
