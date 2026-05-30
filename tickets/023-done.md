## Implementation complete — 023

**What I did:**
- Added `optional_user` dependency to `web/middleware/session.py` alongside `require_user`. Identical DB lookup and token refresh path; all failure conditions (missing cookie, row not found, refresh failure) return `None` instead of raising `RequiresLogin`. The stale-session DELETE path calls `db.commit()` as required.
- Changed `GET /` in `web/routes/home.py` to use `Depends(optional_user)` instead of `Depends(require_user)`. When `current_user is None`, skips `make_session` / `get_user_hockey_leagues` entirely and renders `home.html` with `leagues=None`. Authenticated path is unchanged.
- Updated `web/templates/home.html` to branch on `leagues is none` (Jinja `is none` check, not falsy) — unauthenticated visitors see a "Log in with Yahoo" CTA; authenticated visitors see the league list. The `?logged_out=1` banner block renders for both paths because it precedes the branch.
- Updated `tests/test_home_routes.py`: renamed TC5 from "redirects to /auth/login" to "returns 200 with login CTA" to match new behaviour; added TC14 (unauthenticated GET / shows CTA), TC15 (unauthenticated GET /?logged_out=1 shows banner + CTA), TC16 (authenticated GET / shows league list, not CTA).
- Fixed the TC9 improvement item from `docs/improvements.md`: `test_home_header_shows_selected_league_name` now extracts the `<header>…</header>` substring before asserting the league name. Marked closed in `docs/improvements.md`.

**Files changed:**
- `web/middleware/session.py` — added `optional_user` function (lines appended after `require_user`)
- `web/routes/home.py` — imported `optional_user`; changed `GET /` dependency and added unauthenticated branch
- `web/templates/home.html` — added `{% if leagues is none %}` unauthenticated branch with login CTA
- `tests/test_home_routes.py` — renamed TC5; added TC14/TC15/TC16; tightened TC9 header assertion
- `docs/improvements.md` — closed TC9 improvement item

**Acceptance criteria status (self-check):**
- [x] AC1: `GET /auth/logout` followed by redirect to `/?logged_out=1` renders `home.html` with "You have been logged out." banner — TC15 passes: unauthenticated GET /?logged_out=1 returns 200 with banner; the banner block is above the `leagues is none` branch and fires regardless of auth state.
- [x] AC2: `GET /` with no session cookie returns 200 and renders login prompt — TC14 and TC5 both pass: status 200, `href="/auth/login"` and "Log in with Yahoo" present in body.
- [x] AC3: `GET /` with a valid session still renders league list correctly — TC1, TC2, TC3, TC8, TC9, TC10, TC16 all pass with no regressions.
- [x] AC4: `POST /leagues/select` still requires authentication — TC6 passes: no cookie → 302 to /auth/login (unchanged, `require_user` still used on that route).

**How to verify (for QA):**
1. `uvicorn web.main:app --reload`
2. Without any session cookie, visit `http://localhost:8000/`. Confirm: 200, "Log in with Yahoo" button visible, no redirect to Yahoo OAuth.
3. Click "Log in with Yahoo", complete OAuth. You land on `/` showing your league list.
4. Click "Logout". Confirm: redirect to `/?logged_out=1`, green "You have been logged out." banner visible, "Log in with Yahoo" button visible.
5. Log in again, visit `/`. Confirm: league list renders, no login CTA, banner absent.
6. While logged out, POST to `/leagues/select` (e.g. via curl): confirm 302 to /auth/login.
7. `pytest tests/test_home_routes.py` — 16 passed.

**Scope notes:**
- `web/main.py` was not modified. The `RequiresLogin` global handler at lines 40–42 still exists and still fires for all other authenticated routes — only `GET /` uses `optional_user`.
- The base.html nav header still shows the "Logout" link for unauthenticated visitors (since `base.html` is outside the ticket's Touches list). A follow-up could conditionally show "Login" vs "Logout" in the nav based on auth state.

**Known limitations / things I couldn't fully test:**
- The `_try_refresh` → stale-session DELETE → `db.commit()` → `return None` path in `optional_user` was not exercised by the automated test suite (no test simulates a refresh failure in the optional path). The logic is a direct copy of the same path in `require_user` (which is tested in `tests/test_auth_routes.py`) with `raise RequiresLogin()` replaced by `return None` — the commit is present at the correct position.
- Browser walk of the logged-out banner was not performed (app run not possible in this environment). The template logic is verified by TC11 (authenticated) and TC15 (unauthenticated) both asserting the banner text.
