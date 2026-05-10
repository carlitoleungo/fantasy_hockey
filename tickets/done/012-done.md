## Implementation complete — 012

**What I did:**
- Changed `_DEFAULT_DB_PATH` from `/data/app.db` to `./app.db` in `db/connection.py`
- Updated the `get_db` docstring to document the new default and production override
- Added `mkdir(parents=True, exist_ok=True)` in `get_db` so any nested `DB_PATH` dirs are created automatically
- Added `init_db(conn)` function to `db/connection.py` that runs `db/schema.sql` via `executescript` (idempotent via `CREATE TABLE IF NOT EXISTS`)
- Updated `web/main.py` lifespan to call `init_db(conn)` before the `ALTER TABLE` retry block
- Added `app.db`, `app.db-wal`, `app.db-shm`, and `.env` to `.gitignore`
- Created `.env.example` at repo root documenting all six env vars with comments

**Files changed:**
- `db/connection.py` — new `_DEFAULT_DB_PATH`, new `init_db`, `mkdir` in `get_db`, updated docstring
- `web/main.py` — import `init_db`, call it in lifespan before `ALTER TABLE`
- `.gitignore` — appended `app.db`, `app.db-wal`, `app.db-shm`, `.env`
- `.env.example` — new file; documents `DB_PATH`, `CACHE_DIR`, `HTTPS_ONLY`, `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REDIRECT_URI`

**How to verify:**
- Test 1: Delete any `./app.db`, unset `DB_PATH`, run `uvicorn web.main:app --reload` — server should reach "Application startup complete" with no errors.
- Test 2: After Test 1, run `sqlite3 ./app.db ".schema"` — both `oauth_states` and `user_sessions` tables present; `user_sessions` includes `league_key` column.
- Test 3: Delete `app.db` and restart — schema re-created identically; no errors.
- Test 4: `DB_PATH=./var/test.db uvicorn web.main:app --reload` with no pre-existing `var/` dir — app creates the directory and starts cleanly.
- Test 5: Confirm `app.db` is not tracked by git (`git status` should not list it).
- Test 6: `.env.example` is present in git; `.env` is gitignored.

**Scope notes:**
- The Tech Lead noted that `mkdir` in `get_db` runs on every request (cheap but semantically belongs in startup). This is acceptable per the ticket spec; flagging for awareness if it becomes a concern.
- If a future test wraps `TestClient(app)` in a `with` block, the lifespan will fire and write `./app.db` into the repo root. A `conftest.py` fixture that sets `DB_PATH` to a temp path would prevent this — worth a follow-up ticket when integration-style lifespan tests are needed.

**Known limitations:**
- No smoke test was run manually (no live Yahoo credentials in this environment), but the logic changes are straightforward and match the prescribed implementation in the ticket spec exactly.
