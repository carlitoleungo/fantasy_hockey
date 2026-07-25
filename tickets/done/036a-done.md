## Implementation complete — 036a

**What I did:**
- Added `shell_context(current_user, *, demo=False, league_name=None)` to
  `web/routes/common.py`. It returns `{"is_authenticated", "demo_mode",
  "selected_league_name"}` and derives `is_authenticated` from whether the passed user is
  `None`. It takes the user the route's `optional_user`/`require_user` dependency already
  resolved — no second cookie or DB lookup (DECISIONS 2026-07-03 Option C).
- Made the `base.html` nav conditional on `demo_mode` / `is_authenticated`, with the
  authenticated nav as the fallback when **both** flags are absent, so every page that has
  not yet adopted the helper renders exactly as it did before. Feature-link ordering
  Overview → Waiver → Projection is preserved in both link sets.
- Built the demo branch of the nav now (links to `/demo/overview`, `/demo/waiver`,
  `/demo/projection`, no Logout, a "Log in with Yahoo" affordance) because ticket 036b
  scopes `base.html` out and says a needed change there means 036a was incomplete. Nothing
  sets `demo_mode` yet, so the branch is dormant until 036b adopts the helper in the demo
  handlers.
- Adopted `shell_context()` in **both** branches of `GET /` in `web/routes/home.py`. The
  unauthenticated branch passes `None`; the authenticated branch passes `current_user` plus
  `league_name=selected_league_name`, which also closes the pre-existing drift where the
  logged-out home branch never passed `selected_league_name`.
- Added four tests (three home, one overview) covering AC1, AC2 and AC3, and the AC4
  logged-out-vs-authenticated nav-difference assertion.
- Moved the `docs/improvements.md` item "Nav header shows auth links to unauthenticated
  visitors" to the closed-items archive with a 036a resolution note.

**Files changed:**
- `web/routes/common.py` — new `shell_context()` helper; imports `CurrentUser` for the
  signature type only.
- `web/templates/base.html` — nav split into demo / logged-out / authenticated branches,
  defaulting to authenticated.
- `web/routes/home.py` — imports `shell_context` and spreads it into both `TemplateResponse`
  contexts on `GET /`.
- `tests/test_home_routes.py` — added TC17 (logged-out nav has no auth-gated href), TC18
  (authenticated nav in roadmap order + league label), TC19 (AC4 nav-difference assertion).
- `tests/test_overview_routes.py` — added TC9 (`/overview` still renders the authenticated
  nav via the `base.html` default path).
- `docs/improvements.md` / `docs/archive/improvements-closed.md` — DoD item move.

**Acceptance criteria status (self-check):**
- [x] AC1 — `GET /` with no session returns 200, header nav contains no `/overview`,
  `/waiver`, `/projection` or `/auth/logout` href, and shows a "Log in with Yahoo" link.
  Evidence: live uvicorn on port 8077 — `GET /` returned 200 and the nav rendered as a
  single `<a href="/auth/login" …>Log in with Yahoo</a>`. I then followed every href in
  that nav: the only one, `/auth/login`, 302s to `https://api.login.yahoo.com/oauth2/...`,
  i.e. straight into the OAuth flow, not a bounce back to `/auth/login`. Also asserted by
  TC17.
- [x] AC2 — `GET /` authenticated returns 200 with `/overview`, `/waiver`, `/projection`,
  `/auth/logout` in roadmap order and the selected-league label rendering. Evidence: TC18
  asserts the three feature hrefs appear in ascending source position, that
  `href="/auth/logout"` is present, that `href="/auth/login"` is absent, and that
  "Alpha League" renders. Existing TC9 (league name inside `<header>…</header>`) still
  passes, which is the label check. Verified through the real route handler and real Jinja
  render with Yahoo calls mocked — **not** through a live browser login (see limitations).
- [x] AC3 — `GET /overview` renders the authenticated nav unchanged via the `base.html`
  default path. Evidence: new TC9 in `tests/test_overview_routes.py` asserts the roadmap
  ordering and the logout link inside the `<nav>` element. Independently, against the live
  server, `GET /demo/overview` (also unmigrated) returned 200 with the byte-identical
  pre-change nav, and `GET /overview` with no session still 302s to `/auth/login`, so no
  route auth requirement moved.
- [x] AC4 — `python3 -m pytest tests/` green, including the nav-difference assertion.
  Evidence: `407 passed` (baseline before my change was `403 passed`). TC19 asserts the
  logged-out body lacks `href="/waiver"` and contains "Log in with Yahoo" while the
  authenticated body contains `href="/waiver"`.

**How to verify (for QA):**
- `cd /Users/carlinleung/personal_dev/fantasy_hockey && .venv/bin/python -m pytest tests/ -q`
  → expect `407 passed`. (Note: the repo `python3` on PATH has no pytest; use `.venv/bin/python`.)
- Targeted: `.venv/bin/python -m pytest tests/test_home_routes.py tests/test_overview_routes.py -q`
- Logged-out walk: `.venv/bin/python -m uvicorn web.main:app --port 8077`, then
  `curl -s http://127.0.0.1:8077/` and inspect the `<nav>` block — one link only,
  `/auth/login`. Clicking it should leave for Yahoo, not return to the app.
- Authenticated walk (needs a real Yahoo login, which I could not do): log in, load `/`,
  confirm four nav links in Overview → Waiver → Projection → Logout order, all 200, and the
  selected league name beside "Fantasy Hockey" in the header.
- Regression: while authenticated, `/overview`, `/waiver`, `/projection` navs must look
  exactly as before. `/demo/*` navs are also unchanged by design — 036b changes those.
- No demo-data steps: this ticket touches no `data/` code.

**Scope notes:**
- The improvements item "Add demo mode entry point on home page" is a `quality` item on
  `web/routes/home.py`, a file I modified, so the Engineer persona's input-#6 rule would
  normally have me fix it. The ticket explicitly says to leave it open as a separate
  follow-up, so I left it untouched. Flagging the rule conflict rather than resolving it
  silently.
- The improvements item "Simplify redundant assertion in TC14 of `test_home_routes.py`"
  sits on a file I modified, but **its prescribed fix is wrong** and I did not apply it. It
  says to simplify TC14's last line to `assert "Your Leagues" not in body`. That would fail:
  `home.html` line 3 is `{% block title %}Your Leagues{% endblock %}`, which is outside the
  `leagues is none` conditional, so the string is always present in the `<title>` of both
  branches — the `body.split("</head>", 1)[1]` idiom the item calls "unusual" is the reason
  the test works. The item's other half (that the `"<h1" in body` guard is always true and
  adds no signal) is correct. I left TC14 byte-identical and left the item open for the
  Reviewer to re-word; applying it as written would have broken the suite.
- The DoD move went to `docs/archive/improvements-closed.md`, not to a `## Closed` list
  inside `docs/improvements.md`. The ticket says "move to `## Closed`", and the `## Closed`
  section of `docs/improvements.md` is a pointer that instructs exactly this. This matches
  the Engineer persona's standing rule against recreating an inline closed section.
- `web/templates.py` untouched, as required. No `context_processors` added.
- No new dependency, env var, or config knob.

**Improvements items closed:**
- "Nav header shows auth links to unauthenticated visitors" (Type: quality, Source: Audit
  024, File: `web/templates/base.html`) — moved to `docs/archive/improvements-closed.md`
  with a ticket-036a resolution note.

**Known limitations / things I couldn't fully test:**
- I did **not** exercise the authenticated home page in a browser against live Yahoo. All
  three session rows in the local `app.db` have expired `expires_at` values, and the only
  way to use them is to let the session middleware attempt a token refresh — which, on
  failure, deletes the stale row and would cost the owner their saved sessions. I judged
  that side effect not worth taking on the owner's local DB. The authenticated branch is
  covered by TC18/TC9/TC8 (real handler, real template, Yahoo mocked) and its rendered nav
  markup is byte-identical to the pre-change nav, but a live-session visual confirmation is
  outstanding and QA should do it if they have a working login.
- The demo branch of `base.html` has no route setting `demo_mode=True` yet, so it is
  verified only by direct template render
  (`templates.env.get_template("base.html").render(demo_mode=True)` → the three `/demo/*`
  links plus the login affordance, no Logout) and not through an HTTP request. 036b's ACs
  cover it end-to-end.
- No visual/CSS check beyond link set and ordering — the header styling classes are
  unchanged from the original markup, and the ticket forbids a design pass.
