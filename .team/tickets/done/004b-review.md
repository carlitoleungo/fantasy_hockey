## Code Review — 004b

**Files reviewed:**
- `web/routes/auth.py` — new file; login and callback route handlers
- `tests/test_auth_routes.py` — new file; four tests covering all acceptance criteria
- `web/main.py` — registers auth router

---

### Scope: CLEAN

Changes match the ticket exactly. Session middleware and token refresh are explicitly deferred to ticket 005, and the done.md notes this correctly.

---

### Architecture: CLEAN

No framework imports in `data/` or `analysis/`. No per-entity API loops. No raw stat values or unnormalized array responses (not applicable to this ticket). No missing demo counterpart — `/auth/*` routes are public by design and demo mode does not use them.

---

### Issues

**Should fix:**

**`_db_dep` defined in the route file — move to `db/connection.py` before ticket 005.**
`_db_dep` is the FastAPI generator dependency that wraps `get_db()` with a `try/finally` close. It's defined locally in `web/routes/auth.py` and then imported by the test to wire up the dependency override. This creates a coupling between the test module and `auth.py`'s internals, and it means every future route file will need its own copy or an odd cross-route import.

The ARCHITECTURE.md describes `db/connection.py` as the home for the DB dependency pattern ("a FastAPI dependency `Depends(get_db)` provides it to route handlers and closes it after the response"). Ticket 005 will add session middleware that also needs a DB connection — this pattern needs to be in a shared location before that work starts.

Fix: move `_db_dep` (rename to `db_dep` to make it public) to `db/connection.py`; update `web/routes/auth.py` and `tests/test_auth_routes.py` to import it from there.

---

**Nit:**

`import sqlite3` inside `_db_dep` (line 36 of `auth.py`) is dead code — `sqlite3` is never referenced in that function body. `get_db()` handles the connection. Delete it.

---

### Verdict: APPROVED

All four acceptance criteria pass. Cookie security attributes are correctly conditioned on `HTTPS_ONLY`. Nonce consumption is atomic (DELETE before token exchange). The one deferred should-fix (`_db_dep` placement) is pre-existing technical debt that needs to land before ticket 005 to avoid the coupling spreading to session middleware. It does not block this ticket.
