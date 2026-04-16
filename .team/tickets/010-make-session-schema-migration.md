# 010 — make_session helper and league_key schema migration

## Summary
Two small prerequisites for the landing page (ticket 011). First: `auth/oauth.py` needs a
`make_session(access_token)` function that returns a `requests.Session` with the correct
`Authorization` header — this is the bridge between the SQLite-stored token and the Yahoo
API client. Second: `user_sessions` needs a `league_key TEXT` column so the app can
remember which league the user last selected across requests (since there is no in-process
session state in FastAPI).

## Acceptance criteria
- [ ] `make_session(access_token)` returns a `requests.Session` whose `Authorization`
  header is `Bearer {access_token}`
- [ ] The `user_sessions` table includes a `league_key TEXT` column (nullable) — verifiable
  by inspecting `db/schema.sql` and by querying a freshly initialised test DB
- [ ] All existing tests continue to pass unmodified

## Files likely affected
- `auth/oauth.py`
- `db/schema.sql`
- `tests/test_oauth_helpers.py`

## Dependencies
- None

## Notes for the engineer
- Add to `auth/oauth.py` (public API section, below `exchange_code`):
  ```python
  def make_session(access_token: str) -> requests.Session:
      """Return a requests.Session pre-configured with the Yahoo OAuth Bearer token."""
      session = requests.Session()
      session.headers.update({"Authorization": f"Bearer {access_token}"})
      return session
  ```
  `requests` is already imported. No new imports needed.
- Update `db/schema.sql`: add `league_key TEXT` to the `user_sessions` CREATE TABLE
  statement. The column should be nullable (no `NOT NULL` constraint) — newly logged-in
  users have not selected a league yet.
- Schema migration for existing DBs: the app must handle a DB that was created before this
  column existed. Add a startup migration in `web/main.py` (or a new `db/migrate.py` called
  from `main.py`'s startup event). The migration is one line:
  ```sql
  ALTER TABLE user_sessions ADD COLUMN league_key TEXT
  ```
  Wrap it in a try/except for `sqlite3.OperationalError` (raised when the column already
  exists — SQLite does not support `ADD COLUMN IF NOT EXISTS`). Run this before the app
  starts serving requests using FastAPI's `lifespan` context manager or an
  `@app.on_event("startup")` handler.
- Write one test in `test_oauth_helpers.py`: call `make_session("test_token")` and assert
  `session.headers["Authorization"] == "Bearer test_token"`.

## Notes for QA
- Run the full test suite.
- Verify the new `make_session` test passes.
- Manually verify: create a fresh test DB using `db/schema.sql`, then `SELECT * FROM
  pragma_table_info('user_sessions')` — confirm `league_key` appears in the column list.
- Verify the migration is idempotent: running it twice (column already exists) must not
  raise an unhandled exception.
