# 023 — Optional auth on GET /: fix logged-out banner and login prompt

## Status
done

## Type
bug

## Touches
- `web/middleware/session.py`
- `web/routes/home.py`
- `web/templates/home.html`
- `tests/test_home_routes.py`

## Why
After ticket 022 shipped logout confirmation, users who click "Log out" are redirected to
`/?logged_out=1` — but `GET /` requires a valid session via `Depends(require_user)`. The
unauthenticated request immediately raises `RequiresLogin`, which `main.py` catches and
redirects to `/auth/login`, silently discarding `?logged_out=1`. The "You have been logged
out." banner is never shown. Beyond the banner, any unauthenticated visit to `/` bounces
straight to Yahoo OAuth with no explanation — users have no way to see what the app is
before authenticating.

## Acceptance criteria
- [ ] `GET /auth/logout` followed by the resulting redirect to `/?logged_out=1` renders
  `home.html` with the "You have been logged out." banner visible — no Yahoo OAuth screen.
- [ ] `GET /` with no session cookie (or an expired/deleted session) returns 200 and
  renders a login prompt (not a redirect to `/auth/login`).
- [ ] `GET /` with a valid session still renders the league list correctly (no regression).
- [ ] `POST /leagues/select` still requires authentication and is unaffected by this change.

## Out of scope
- Any other authenticated route — only `GET /` changes to optional auth.
- A marketing or public landing page — a minimal "Log in with Yahoo" button is enough.
- Demo mode routes — unaffected.
- Styling polish on the unauthenticated state beyond a functional CTA.

## Notes for the Engineer

**Architectural surface — routing/middleware:** This ticket adds a new dependency variant to
`web/middleware/session.py`. The fix direction is specified below; no further Tech Lead
consult is needed because the approach is a pure addition that does not alter `require_user`
or any authenticated route.

**The optional dependency pattern:**

Add `optional_user` to `web/middleware/session.py` alongside (not replacing) `require_user`:

```python
def optional_user(
    session_id: str | None = Cookie(default=None),
    db=Depends(db_dep),
) -> CurrentUser | None:
    if not session_id:
        return None
    # same DB lookup as require_user ...
    if row is None:
        return None
    # same token validation / refresh path ...
    # if refresh fails: delete stale row, return None (do not raise RequiresLogin)
    return CurrentUser(...)
```

`require_user` is unchanged — every other authenticated route keeps working exactly as
before.

**`web/routes/home.py` changes:**

- Import `optional_user` alongside `require_user`.
- Change `GET /` signature to `current_user: CurrentUser | None = Depends(optional_user)`.
- When `current_user is None`: skip `make_session` / `get_user_hockey_leagues` entirely
  and render `home.html` with `leagues=None` (use `None`, not `[]`, so the template can
  distinguish "not logged in" from "logged in with no leagues").
- When `current_user` is set: existing code path unchanged.

**`web/templates/home.html` changes:**

- Add an unauthenticated branch: when `leagues is none` (Jinja checks `is none`, not
  `not leagues`, so an empty list doesn't trigger it), render a login CTA instead of the
  league list. The `?logged_out=1` banner block at line 7 already works — it just needs
  the template to actually be rendered for unauthenticated requests.
- Minimal CTA: an `<a href="/auth/login">` button; no full landing page content.

**Existing pattern reference:**

- `require_user` full implementation: `web/middleware/session.py:39–99`.
- `RequiresLogin` exception handler that must NOT fire for `GET /`: `web/main.py:40–42`.
- Existing banner markup that is already correct: `web/templates/home.html:7–10`.

**Test file:** `tests/test_home_routes.py` already exists. Add cases for: unauthenticated
request returns 200 with login CTA; unauthenticated request with `?logged_out=1` returns
200 with banner; authenticated request still renders league list.

**Tech Lead review (2026-05-30):**

`optional_user` belongs in `web/middleware/session.py`. It is a direct variant of the same
session-validation concern — same DB lookup, same token refresh path, different failure mode.
Splitting it to another module would obscure that relationship.

FastAPI-specific gotchas to be aware of:

- *`Cookie(default=None)` + `Depends(db_dep)` is safe.* `db_dep` opens and closes a DB
  connection on every request regardless of whether a cookie is present — the generator's
  `finally` block guarantees cleanup. Negligible cost for unauthenticated requests.
- *Return type `CurrentUser | None` via `Depends()` is safe.* FastAPI does not apply
  response-model validation to dependency return values; the `None` flows directly to the
  route handler with no serialization side effects.
- *The stale-session DELETE path needs `db.commit()`.* The PM's sketch shows "delete stale
  row, return None" but does not show the commit. `require_user` commits at line 78 of
  `web/middleware/session.py` — `optional_user` must do the same or the DELETE will be
  silently rolled back on connection close.
- *`RequiresLogin` must never be raised from `optional_user`.* The global handler at
  `web/main.py:40–42` catches it and issues a 302 redirect — which would silently break
  the unauthenticated render. All failure paths (missing cookie, row not found, refresh
  failure) must `return None`.

Roadmap conflicts: none. Near-term tickets 020/021 (demo routes) and the week projection
migration are unaffected. The per-user cache storage migration (multi-user deployment) is
a long-term "Watching" item; `GET /` being publicly accessible goes in the right direction
for that future state.

`ARCHITECTURE.md` key patterns #2 will need a one-line addition when this ticket lands
("`optional_user` exists as a variant for routes that serve both authenticated and
unauthenticated users"). That is a Tech Lead responsibility, not the engineer's — do not
add it as part of this ticket.

## Verification
1. Start the app: `uvicorn web.main:app --reload`.
2. Without logging in, visit `http://localhost:8000/`. Confirm: page loads (200), shows a
   "Log in with Yahoo" button, no redirect to Yahoo OAuth.
3. Log in, then click the logout link. Confirm: lands on `/` with the "You have been
   logged out." green banner visible.
4. Log in again and visit `/`. Confirm: league list renders as before.
5. Run `pytest tests/test_home_routes.py` — all tests pass.

## Dependencies
- Ticket 022 must be complete first (it introduced the `/?logged_out=1` redirect that
  this ticket fixes). **022 is done.**
