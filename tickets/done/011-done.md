## Implementation complete — 011

**What I did:**
- Created `web/routes/home.py` with `GET /` (renders user's current-season leagues) and `POST /leagues/select` (updates `league_key` in session row and redirects)
- Created `web/templates/home.html` extending `base.html` with league list, selected-league highlight (blue background + checkmark), empty-state message, and logout link
- Registered `home_router` in `web/main.py`

**Files changed:**
- `web/routes/home.py` (new) — two route handlers; season filter uses `max(lg["season"])` pattern from `app.py:198–205`
- `web/templates/home.html` (new) — Tailwind-styled league list; visually highlights selected league via `selected_key` comparison
- `web/main.py` — imported and registered `home_router`

**How to verify:**
- Run `uvicorn web.main:app --reload` and navigate to `http://localhost:8000/` without a session cookie — should redirect 302 to `/auth/login`
- Complete OAuth flow; after callback redirects to `/`, the home page should list your current-season hockey leagues
- Click "Select" on a league — should POST to `/leagues/select`, update the DB row, redirect 302 to `/`, and show the selected league highlighted with a checkmark
- Manually confirm: `SELECT league_key FROM user_sessions` in `app.db` reflects the chosen league key after selection
- Edge case: if your Yahoo account has no NHL leagues, the page should render "No active NHL leagues found for your account." without a 500

**Scope notes:**
- No caching of the league list — matches prototype behaviour; caching is a future optimisation as noted in the ticket
- `demo.py` has no counterpart needed here — the home/league-selector flow is auth-gated by design; demo mode has its own `/demo/*` prefix that bypasses auth

**Known limitations:**
- The `GET /` handler makes two Yahoo API calls on every page load (games + leagues per game) with no caching — noticeable latency; flagged in ticket as a future optimisation
