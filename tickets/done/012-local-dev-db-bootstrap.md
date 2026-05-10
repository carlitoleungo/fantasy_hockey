# 012 — Local-dev DB bootstrap and env documentation

## Summary
Two paper cuts make a fresh local checkout fail to boot:
1. `db/connection.py` defaults `DB_PATH` to `/data/app.db` (the Fly.io volume mount path),
   which doesn't exist on a developer's machine. Running `uvicorn web.main:app --reload`
   crashes in the lifespan with `sqlite3.OperationalError: unable to open database file`.
2. Even with a valid `DB_PATH`, the schema is never applied automatically — only the
   `league_key` `ALTER TABLE` from ticket 010 runs in the lifespan. A fresh DB has no
   `oauth_states` or `user_sessions` tables, so the first `/auth/login` blows up.

This ticket makes a fresh `git clone` → `uvicorn` work without manual `sqlite3` invocations,
and documents the env vars new developers need to set.

## Acceptance criteria
- [ ] On a machine with no `DB_PATH` set and no existing `app.db`, running
  `uvicorn web.main:app --reload` from the repo root starts cleanly: the lifespan creates
  the SQLite file, runs `db/schema.sql`, and the server reaches "Application startup complete".
- [ ] `db/connection.py`'s `_DEFAULT_DB_PATH` is changed to a path that works locally without
  any env var (e.g. `./app.db` relative to the repo root). The new default file is added to
  `.gitignore`.
- [ ] A new `init_db(conn)` function in `db/connection.py` executes the contents of
  `db/schema.sql` against the given connection. It is idempotent (safe to call on every
  startup; relies on the existing `CREATE TABLE IF NOT EXISTS` statements in `schema.sql`).
- [ ] `web/main.py` lifespan calls `init_db(conn)` **before** the `ALTER TABLE` retry block,
  so a brand-new DB gets its tables created before the league_key migration runs.
- [ ] A new `.env.example` file at the repo root documents every env var the app reads:
  `DB_PATH`, `CACHE_DIR`, `HTTPS_ONLY`, `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`,
  `YAHOO_REDIRECT_URI`. Each entry includes a one-line comment on what it does and the
  default (or "required" if no default).

## Files likely affected
- `db/connection.py`
- `web/main.py`
- `.env.example` (new)
- `.gitignore` (one-line add for the local DB file)

## Dependencies
- None. Builds on tickets 004a (db/connection.py exists) and 010 (schema.sql includes the
  `league_key` column on `user_sessions`).

## Notes for the engineer
- **Default DB path:** Change `_DEFAULT_DB_PATH` from `/data/app.db` to `./app.db`. When the
  app is deployed (currently still in `docs/backlog.md`), `DB_PATH=/data/app.db` will be set
  via Fly.io env var — there is no `fly.toml` yet, so no deployment artifact needs updating.
  Update the `_DEFAULT_DB_PATH` docstring in `db/connection.py` to reflect the new default.

- **`init_db` shape:** The simplest implementation is:
  ```python
  from pathlib import Path
  _SCHEMA_PATH = Path(__file__).parent / "schema.sql"

  def init_db(conn: sqlite3.Connection) -> None:
      conn.executescript(_SCHEMA_PATH.read_text())
      conn.commit()
  ```
  `executescript` runs multiple statements in one call, which matches the structure of
  `schema.sql`. Idempotency comes from the `CREATE TABLE IF NOT EXISTS` clauses already
  in the schema file — do not add any extra "exists" checks in Python.

- **Parent-dir creation:** If `_DEFAULT_DB_PATH` is `./app.db` relative paths don't need
  `mkdir`, but a deployed `DB_PATH=/data/app.db` requires `/data/` to exist (Fly.io creates
  it via the volume mount, so this is already handled in production). To be safe for any
  future `DB_PATH=./var/app.db`-style values, call `Path(resolved).parent.mkdir(parents=True, exist_ok=True)`
  at the top of `get_db()` before `sqlite3.connect`. This is a one-liner and prevents a
  whole class of "you forgot to mkdir" bugs.

- **Lifespan ordering:** In `web/main.py`, the new flow is:
  ```python
  conn = get_db()
  try:
      init_db(conn)             # creates oauth_states, user_sessions on fresh DB
      try:
          conn.execute("ALTER TABLE user_sessions ADD COLUMN league_key TEXT")
          conn.commit()
      except sqlite3.OperationalError:
          pass
  finally:
      conn.close()
  ```
  The `ALTER` block stays — it migrates pre-ticket-010 local DBs. On fresh DBs the `ALTER`
  will fail (column already exists from `schema.sql`) and be swallowed by the existing
  `except`. That's correct.

- **`.env.example`** lives at the repo root (sibling to `requirements-web.txt`). Use
  `KEY=value` lines with `#` comments. Example:
  ```
  # Path to the SQLite session DB. Defaults to ./app.db locally.
  DB_PATH=./app.db

  # Yahoo OAuth credentials — required. Register at https://developer.yahoo.com/apps/
  YAHOO_CLIENT_ID=
  YAHOO_CLIENT_SECRET=
  YAHOO_REDIRECT_URI=http://localhost:8000/auth/callback
  ```
  Do not commit a real `.env` file (none exists today; `.gitignore` already covers
  `.streamlit/secrets.toml` for prototype secrets but `.env` should be added too if the
  engineer plans to use python-dotenv). For this ticket, `.env.example` is documentation
  only — no auto-loading.

- **`.gitignore` add:** Append `app.db`, `app.db-wal`, `app.db-shm` (the WAL-mode sidecar
  files SQLite creates).

- **Do not** introduce `python-dotenv` or any auto-load of `.env`. Engineers can `export`
  vars or use direnv. Adding a dependency is out of scope for this ticket.

## Notes for QA
- Test 1 (the regression that motivated this ticket): in a fresh checkout with no `DB_PATH`
  set and no `app.db` file present, `uvicorn web.main:app --reload` reaches "Application
  startup complete" and serves `GET /health` → 200.
- Test 2: after Test 1, `sqlite3 ./app.db ".schema"` shows both `oauth_states` and
  `user_sessions` tables, and `user_sessions` has the `league_key` column.
- Test 3: delete `app.db` and restart — schema is re-created identically; no errors.
- Test 4: with an existing pre-ticket-010 `app.db` (no `league_key` column), restarting
  applies both the new `init_db` (no-op for existing tables) and the `ALTER TABLE`
  successfully. Simulate by manually creating a DB from the pre-010 schema if needed.
- Test 5: `DB_PATH=./var/test.db uvicorn …` — the `var/` directory does not exist beforehand;
  the app creates it via the new `mkdir(parents=True, exist_ok=True)` call and starts
  cleanly.
- Test 6: `.env.example` is checked in; no real `.env` is checked in; `.gitignore` includes
  `app.db` and its WAL sidecars.

---

## Tech Lead review

**Complexity: S** (<15 min). Four small files touched, no new logic branches, no deps
added. Single ticket, no split needed.

**Feasibility:** Clean. The prescribed `init_db` → `ALTER TABLE` ordering in the lifespan
is correct. `CREATE TABLE IF NOT EXISTS` makes `init_db` safely idempotent on both fresh
and pre-010 DBs, and the existing `OperationalError` swallow handles the "column exists"
case on fresh DBs as described. The env-var list in `.env.example` matches every
`os.environ` read in the codebase (verified: `DB_PATH`, `CACHE_DIR`, `HTTPS_ONLY`,
`YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REDIRECT_URI` — nothing else).

**Risks / additions to acceptance criteria:**

1. **Add `.env` to `.gitignore` unconditionally.** The ticket leaves this as "if the
   engineer plans to use python-dotenv," but a real `.env` is the obvious place a dev
   will drop `YAHOO_CLIENT_SECRET` regardless of whether dotenv is installed. The
   risk of accidentally committing secrets is asymmetric — gitignore it now. Append
   `.env` alongside the `app.db*` entries.

2. **Test lifespan side effect (latent).** Current tests use
   `TestClient(app, follow_redirects=False)` without a `with` block, so Starlette's
   TestClient does not fire the lifespan — tests will be unaffected by this ticket.
   However, if anyone later wraps a test in `with TestClient(app) as client:`, the
   new `init_db` will write `./app.db` into the repo root as a side effect. Not a
   blocker for this ticket, but worth a one-line comment in `web/main.py`'s lifespan
   or a `conftest.py` `monkeypatch.setenv("DB_PATH", ...)` added proactively. Call
   this out to QA so Test 1 isn't run from a shell where a stale `./app.db` is
   already present.

3. **`mkdir` in `get_db` runs on every request.** Cheap (stat call on an existing
   dir), but semantically it belongs in `init_db` or a one-time startup path rather
   than per-connection. Acceptable as-is for simplicity; flagging for awareness.

4. **`_DEFAULT_DB_PATH` docstring.** Ticket calls this out; the current docstring on
   line 31 of `db/connection.py` says "falling back to /data/app.db" — make sure
   that string is updated, not just the constant.

**Dependencies:** None beyond those stated (004a, 010 — both landed). Can land
standalone; no ordering concerns with other in-flight work.

**Implementation order for the engineer:**
1. `db/connection.py` — change `_DEFAULT_DB_PATH`, update docstring, add `init_db`,
   add `mkdir(parents=True, exist_ok=True)` in `get_db`.
2. `web/main.py` — insert `init_db(conn)` above the `ALTER TABLE` block in the
   lifespan.
3. `.gitignore` — append `app.db`, `app.db-wal`, `app.db-shm`, `.env`.
4. `.env.example` — create at repo root with the six env vars.
5. Smoke test: delete any local `app.db`, unset `DB_PATH`, run
   `uvicorn web.main:app --reload`, hit `/health`.
