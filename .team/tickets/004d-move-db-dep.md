# 004d — Move `_db_dep` to `db/connection.py`

## Summary

`_db_dep`, the FastAPI generator dependency that wraps `get_db()` with a
`try/finally` close, is currently defined privately inside
`web/routes/auth.py`. Ticket 005 will add session middleware that also needs
a DB connection — leaving `_db_dep` in `auth.py` would force the middleware
to either duplicate the generator or import from an unrelated route module.
Move it to `db/connection.py` (renamed to `db_dep`, public) and update all
import sites. Also remove the dead `import sqlite3` that currently lives
inside the `_db_dep` body (the function never uses `sqlite3` directly).

## Acceptance criteria

- [ ] `db/connection.py` exports a public generator `db_dep()` that opens a
  connection via `get_db()`, yields it, and closes it in a `finally` block;
  the function contains no `import sqlite3` statement.
- [ ] `web/routes/auth.py` no longer defines `_db_dep`; both `login` and
  `callback` use `Depends(db_dep)` imported from `db.connection`.
- [ ] `tests/test_auth_routes.py` imports `db_dep` from `db.connection` (not
  `_db_dep` from `web.routes.auth`) for the `app.dependency_overrides` key;
  all four existing auth-route tests pass without modification to test logic.

## Files likely affected

- `db/connection.py`
- `web/routes/auth.py`
- `tests/test_auth_routes.py`

## Dependencies

Requires 004b to be completed first (`_db_dep` was introduced in that ticket).

## Notes for the engineer

**What to add to `db/connection.py`:**
```python
from typing import Generator

def db_dep() -> Generator:
    """FastAPI dependency: open a DB connection and close it after the response."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()
```

**What to remove from `web/routes/auth.py`:**
Delete the entire `_db_dep` function (lines 33–39 in the current file). Replace
the `from db.connection import get_db` import with
`from db.connection import db_dep`. Update both `Depends(_db_dep)` calls to
`Depends(db_dep)`.

**What to change in `tests/test_auth_routes.py`:**
Line 19 currently reads:
```python
from web.routes.auth import _db_dep
```
Change it to:
```python
from db.connection import db_dep
```
Update line 57's `app.dependency_overrides[_db_dep]` to
`app.dependency_overrides[db_dep]`. No other test logic changes.

**Why `import sqlite3` is dead:** The current `_db_dep` body in `auth.py`
contains `import sqlite3` at the top of the function, but `sqlite3` is never
referenced inside the function — `get_db()` handles the connection setup.
Do not carry this import into `db/connection.py`.

## Notes for QA

Run `pytest tests/test_auth_routes.py -v` and confirm all four tests pass.
Also verify that importing `db_dep` from `db.connection` in a Python REPL
(or a scratch test) works without circular imports.
