## Implementation complete — 004d

**What I did:**
- Added `db_dep()` generator to `db/connection.py` (public, no `import sqlite3` inside the body)
- Added `from typing import Generator` import to `db/connection.py`
- Removed `_db_dep` from `web/routes/auth.py`
- Replaced `from db.connection import get_db` with `from db.connection import db_dep` in `auth.py`
- Updated both `Depends(_db_dep)` calls in `auth.py` to `Depends(db_dep)`
- Updated `tests/test_auth_routes.py` to import `db_dep` from `db.connection` instead of `_db_dep` from `web.routes.auth`
- Updated `app.dependency_overrides[_db_dep]` to `app.dependency_overrides[db_dep]` in the test fixture

**Files changed:**
- `db/connection.py` — added `Generator` import and `db_dep()` function above `get_db()`
- `web/routes/auth.py` — removed `_db_dep`; updated import and both `Depends()` calls
- `tests/test_auth_routes.py` — updated import and dependency override key to use `db_dep` from `db.connection`

**How to verify:**
- Run `.venv/bin/python -m pytest tests/test_auth_routes.py -v` — all four tests should pass

**Scope notes:**
- None. The change is purely mechanical — no logic was altered.

**Known limitations:**
- None.
