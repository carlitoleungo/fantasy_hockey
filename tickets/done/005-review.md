## Code Review — 005

**Files reviewed:**
- `web/middleware/session.py` (new) — `RequiresLogin` exception, `CurrentUser` dataclass, `EXEMPT_PREFIXES` constant, and `require_user` FastAPI dependency
- `web/main.py` — added `RequiresLogin` exception handler (302 redirect) and import
- `tests/test_session_middleware.py` (new) — 12 tests covering all ACs and boundary cases

---

### Scope: CLEAN

Changes match the ticket exactly. No bonus changes. `auth/oauth.py` was correctly left untouched (already clean after ticket 004); `web/routes/auth.py` was correctly left untouched (exemptions are implicit in the `Depends` approach). `web/main.py` change is minimal and required.

---

### Architecture: CLEAN

- No framework imports in `data/` or `analysis/`.
- No per-entity API loops introduced.
- No raw Yahoo stat values.
- No Yahoo API array responses accessed without normalization.
- No new live data functions, so no demo counterpart is required.
- `web/middleware/session.py` correctly lives in the `web/` layer; FastAPI imports are appropriate here.

---

### Issues

- **Must fix:** None.
- **Should fix:** None.
- **Nit:** The `EXEMPT_PREFIXES` frozenset is a dead constant at runtime (as documented). The module docstring explains this clearly. No action needed — the intent is documented and the QA report concurs.

---

### Verdict: APPROVED

Implementation is clean, minimal, and correct. The `Depends(require_user)` approach makes exemptions explicit rather than relying on path-prefix matching, which is the right call for this codebase. Error handling is correctly layered: `_try_refresh` catches `HTTPError`, the middleware wraps it in `except requests.RequestException` to catch network failures, and both failure paths delete the session row before raising `RequiresLogin`. DB commit order (delete/update before raise) is safe. All 12 tests pass; boundary cases at now+59 and now+61 are covered; the double-request no-refresh case is covered.
