## Implementation complete — 005

**What I did:**
- Created `web/middleware/session.py` with `RequiresLogin` exception, `CurrentUser` dataclass, `EXEMPT_PREFIXES` constant, and `require_user` FastAPI dependency
- Updated `web/main.py` to register a `RequiresLogin` exception handler that returns `RedirectResponse("/auth/login", 302)`
- Created `tests/test_session_middleware.py` with 12 tests covering all acceptance criteria and boundary cases

**Files changed:**
- `web/middleware/session.py` (new) — `require_user` Depends dependency: reads session cookie, looks up row in `user_sessions`, calls `_is_valid`; if stale calls `_try_refresh` (wrapped in `except requests.RequestException`); on refresh success updates row; on any failure deletes row and raises `RequiresLogin`
- `web/main.py` — added `@app.exception_handler(RequiresLogin)` that returns a 302 redirect; added import of `RequiresLogin`
- `tests/test_session_middleware.py` (new) — full test suite; each test builds a fresh in-memory DB and minimal FastAPI app to stay fully isolated

**How to verify:**
- Run `PYTHONPATH=/Users/carlin/dev/fantasy_hockey python3.11 -m pytest tests/test_session_middleware.py -v` — all 12 tests should pass
- Add `Depends(require_user)` to any route handler; request it without a session cookie and confirm a 302 to `/auth/login`
- Routes that omit the dependency (e.g. `/auth/login`, `/auth/callback`, `/demo`) should be accessible without a cookie — confirmed by `test_exempt_routes_no_cookie`

**Scope notes:**
- Existing routes (`/health`, `/auth/login`, `/auth/callback`) are already public because they don't declare `Depends(require_user)` — no route changes were needed for exemptions
- The `EXEMPT_PREFIXES` frozenset is present as a config constant but not evaluated at runtime in the `Depends` approach; it's there for documentation and to make future additions easy

**Known limitations:**
- `_try_refresh` in `auth/oauth.py` only catches `requests.HTTPError` internally; the middleware adds a broader `except requests.RequestException` guard to also catch network-level failures (timeout, DNS), as specified in the ticket
- Tests set `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, and `YAHOO_REDIRECT_URI` env vars via `monkeypatch` because `_try_refresh` reads those before calling `requests.post` — this is the correct pattern and matches how `test_oauth_helpers.py` already handles it
