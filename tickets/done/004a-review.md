## Code Review — 004a

**Files reviewed:**
- `auth/oauth.py` — Streamlit dependencies removed; credentials moved to `os.environ`; `get_auth_url()` now returns `(url, state)` tuple; flat-file nonce helpers and session-state functions removed; `_try_refresh` side effect cleaned up
- `db/schema.sql` — New file; DDL for `oauth_states` and `user_sessions` tables
- `db/connection.py` — New file; `get_db()` factory in WAL mode with `row_factory`
- `tests/test_oauth_helpers.py` — Four `validate_and_consume_state` tests removed; five remaining tests pass

### Scope: CLEAN

All changes are within the ticket boundary. Nothing was added beyond what was specified. `get_session`, `try_restore_session`, and `clear_session` are gone; `validate_and_consume_state` is gone; schema application is correctly deferred to a later ticket.

### Architecture: CLEAN

No framework imports in `auth/`. No per-entity API loops. No raw stat usage. No new data functions requiring demo counterparts.

### Issues

- **Must fix:** None
- **Should fix:** None
- **Nit:** `_try_refresh` catches only `requests.HTTPError`, so a network timeout or DNS failure will propagate uncaught to the caller. This is pre-existing behavior, explicitly preserved per the ticket spec — noting it only so ticket 005 (refresh middleware) is aware that callers need to handle `requests.RequestException` as well.

### Verdict: APPROVED

Clean, minimal refactor. All eight acceptance criteria are satisfied. The DB layer (`connection.py`, `schema.sql`) matches the architecture spec exactly. `auth/oauth.py` now has no Streamlit dependency and no session-state side effects — callers own both nonce persistence and session cleanup, which is the correct boundary for the middleware pattern ticket 005 will build on.
