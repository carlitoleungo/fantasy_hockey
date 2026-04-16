# 011 — Landing page and league selector

## Summary
The first real user-facing page. After a successful OAuth callback, the browser redirects
to `/` — which currently returns a 404. This ticket adds `GET /` (renders the user's
hockey leagues, filtered to the current season) and `POST /leagues/select` (stores the
chosen `league_key` in `user_sessions` and redirects back to `/`). Both routes require an
authenticated session via `Depends(require_user)`. This is the prerequisite for every
subsequent data page — nothing useful renders without a selected league.

## Acceptance criteria
- [ ] `GET /` with a valid session returns 200 HTML rendered from `home.html` that lists
  the user's current-season hockey leagues (each showing season year and league name)
- [ ] `POST /leagues/select` with a valid `league_key` form field updates the
  `league_key` column in the matching `user_sessions` row and redirects to `/` (302)
- [ ] `GET /` and `POST /leagues/select` without a valid session cookie redirect to
  `/auth/login` (302) via the existing `RequiresLogin` / `require_user` mechanism

## Files likely affected
- `web/routes/home.py` (new)
- `web/templates/home.html` (new)
- `web/main.py`

## Dependencies
- Requires 009 (base.html template and Jinja2Templates setup)
- Requires 010 (make_session, league_key column in user_sessions)

## Notes for the engineer
- Create `web/routes/home.py` with an `APIRouter`. Register it in `web/main.py` alongside
  the existing routers (`app.include_router(home_router)`).
- `GET /` handler signature:
  ```python
  @router.get("/")
  def home(request: Request, current_user: CurrentUser = Depends(require_user), db=Depends(db_dep)):
  ```
  Build a Yahoo session: `session = make_session(current_user.access_token)`.
  Call `get_user_hockey_leagues(session)` from `data/leagues.py`.
  Filter to the current season only: `max(lg["season"] for lg in all_leagues)` then keep
  only leagues matching that season — same logic as the Streamlit prototype in `app.py`
  lines 198–205. If the API call raises `requests.HTTPError`, let it propagate — the
  exception handler from ticket 009 will render the error page.
  Look up the currently-selected `league_key` from the session row to pre-select it in
  the template: `row = db.execute("SELECT league_key FROM user_sessions WHERE session_id = ?", (current_user.session_id,)).fetchone()`.
  Render: `templates.TemplateResponse("home.html", {"request": request, "leagues": leagues, "selected_key": row["league_key"] if row else None})`.

- `POST /leagues/select` handler: reads `league_key` from form data
  (`league_key: str = Form(...)`), runs
  `UPDATE user_sessions SET league_key = ? WHERE session_id = ?`, commits, redirects 302 to `/`.
  Import `Form` from `fastapi`. No re-validation of the league_key against the Yahoo API —
  trust the posted value; data pages will fail gracefully via the error handler if it is invalid.

- `home.html` should extend `base.html`. It needs:
  - A heading (e.g. "Your Leagues")
  - A list or table of leagues, each showing `{{ league.season }} — {{ league.league_name }}`
  - A form for each league with a hidden `league_key` input and a submit button ("Select")
  - Visually highlight the currently-selected league using `selected_key` (e.g. a checkmark
    or different button style when `league.league_key == selected_key`)
  - A note if `leagues` is empty ("No active NHL leagues found for your account.")
  - A link to `/auth/logout` for logout

- Imports needed in `home.py`: `make_session` from `auth.oauth`, `get_user_hockey_leagues`
  from `data.leagues`, `require_user` + `CurrentUser` from `web.middleware.session`,
  `db_dep` from `db.connection`, `templates` from `web.templates`.

- The `get_user_hockey_leagues` function makes two Yahoo API calls (games + leagues per
  game). Both are fast, but the combined latency is noticeable. For now, no caching — this
  matches the prototype behaviour. Caching the league list is a future optimisation.

## Notes for QA
- Test 1: mock `get_user_hockey_leagues` to return a fixture list with two leagues from
  season 2025 and one from 2024. Assert `GET /` renders only the 2025 leagues.
- Test 2: `POST /leagues/select` with a known league_key — assert the DB row is updated
  and the response is 302 to `/`.
- Test 3: `GET /` with no cookie → 302 to `/auth/login`.
- Manually (or via TestClient): confirm the selected league is visually distinguished in
  the rendered HTML after a `POST /leagues/select`.
- Edge case: user has zero NHL leagues — confirm the empty-state message renders without
  a 500.
