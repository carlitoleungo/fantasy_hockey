# 042 — Error pages declare auth state unknown and render nav-free

## Status
ready

## Type
bug

## Milestone
m1

## Touches
- web/routes/common.py
- web/main.py
- web/templates/base.html
- web/templates/error.html
- tests/test_nav_shell.py

## Why
A visitor who hits a 500 or a Yahoo 502 today is shown the authenticated nav —
Overview / Waiver / Projection / Logout — regardless of who they are. For a logged-out or
demo visitor every one of those links bounces them to `/auth/login`, so the error page
compounds the error with a dead end. This is the same defect ticket 036a fixed on the home
page, still live on the two exception handlers because they have no resolved user in scope.
The fix is not to guess who the visitor is: the error page stops claiming to know, renders
the brand link only, and offers an explicit way back to `/`, which is public and renders the
correct nav for whoever follows it.

## Acceptance criteria
- [ ] The 502 page (a route raising `requests.HTTPError`) returns status 502 and its `<nav>` element contains zero `<a>` elements; the response body contains none of `href="/overview"`, `href="/waiver"`, `href="/projection"`, `href="/auth/logout"`, `href="/auth/login"`.
- [ ] The 500 page (a route raising a bare `Exception`) returns status 500 and satisfies the same nav-free condition, and renders byte-identically whether or not a valid `session_id` cookie is sent — the handlers derive nothing about the visitor.
- [ ] Both error pages still render the header brand link (`<a href="/">Fantasy Hockey</a>`) and the shared `<head>` from `base.html`; the body contains a visible "Back to home" link with `href="/"`.
- [ ] Every branch that passes `shell_context()` is unchanged: logged-out `/` still renders the login-only nav, authenticated `/` and the feature pages still render the authenticated nav, demo pages still render the demo nav.
- [ ] `.venv/bin/python -m pytest tests/` is green, with the existing `test_base_html_nav_branches` parametrisation unmodified.

## Out of scope
- **The `base.html` default flip.** Absent flags still fall through to the authenticated nav
  after this ticket. That flip is ticket **044**, which depends on this one. Do not touch the
  `{% elif is_authenticated is undefined or is_authenticated %}` condition here.
- **The stale `base.html` comment** at lines 21-22 ("pages that do not yet pass
  `shell_context()` render exactly as before"). It is still accurate until 044 flips the
  default, and `docs/improvements.md` explicitly assigns it to that ticket. Leave it.
- **Any auth derivation in the exception handlers** — no cookie read, no DB lookup, no
  `request.state`. This is the whole point of the decision below; a handler that resolves a
  user fails review even if the page looks right.
- Restyling the error page, adding error codes/IDs, or changing the `detail` strings.
- `tests/conftest.py` consolidation. `tests/test_nav_shell.py` is named in that
  `docs/improvements.md` item, but audit 041 reserves it for its own ticket.

## Notes for the Engineer
- **Architectural surface (`web/main.py` routing + template structure) — the Tech Lead
  consult is already done. Implement `docs/DECISIONS.md` "Nav shell: render sites that
  cannot resolve a user declare the state unknown and render nav-free; exception handlers
  never derive auth" (2026-07-25) verbatim, and cite that entry by date in your done note.**
  The prescribed shape, from that entry:
  1. `web/routes/common.py` gains a small sibling to `shell_context()` returning
     `{"auth_state_unknown": True}`. It takes no user and contains no logic.
  2. Both handlers in `web/main.py` (`http_error_handler` at lines 48-55 and
     `internal_error_handler` at lines 58-65) spread it into their `error.html` context.
  3. `base.html` branches on that key **first**, before the `demo_mode` branch, and renders
     the header with the brand link only — no feature links, no Logout, no login prompt.
  4. `error.html`'s body gains an explicit "Back to home" link to `/`.
- The key is named for its cause (auth state cannot be resolved), not its effect (hide the
  nav), per the decision. Do not rename it to something like `hide_nav` — that invites a page
  that *does* know its visitor to use it as a styling switch.
- Why authenticated users lose their nav here and that is correct: `/` is public and uses
  `optional_user`, so the brand link and the "Back to home" link both render the right nav for
  whoever follows them. That recovery path is why no derivation is needed.
- `shell_context()` (`web/routes/common.py:12`) is untouched — the new helper is a sibling,
  not a parameter on it. The 2026-07-03 entry's single-auth-derivation-path rule is reaffirmed
  by the 2026-07-25 entry, not relaxed.
- **Where the tests go:** `tests/test_nav_shell.py` is the canonical home for every nav/header
  assertion (`docs/DECISIONS.md` 2026-07-26 "Tests: one module per feature surface"). Put both
  the nav-free assertions and the "Back to home" assertion there, alongside the existing
  `_nav_links` / `_header_left` helpers — they give you the scoped matching these ACs need.
  `tests/test_error_handling.py` already registers `/test/http-error` and `/test/unhandled`
  on the app in its `client` fixture (lines 8-21); mirror that pattern rather than importing
  from it, and leave that file alone.
- Use `TestClient(app, raise_server_exceptions=False)` or the 500 handler will not fire.
- **Open `docs/improvements.md` items on files in `Touches`:**
  - "Error pages show the authenticated nav to logged-out visitors" (`Type: quality`,
    `web/templates/error.html`, `web/main.py`) — **this is the item this ticket resolves.**
    Move it to `docs/archive/improvements-closed.md` with a `**Resolved:**` note on handoff.
  - "`base.html`'s authenticated-nav default is now unblocked, and 040 measured what it
    costs" (`Type: quality`, `web/templates/base.html`) — **out of scope**, it is ticket 044.
  - "Post-036b stale comments about pages 'not yet' passing `shell_context()`"
    (`Type: quality`, `web/templates/base.html` lines 21-22) — **out of scope**, the entry
    itself assigns the `base.html` half to the 044 default flip.
  - "Projection route test scaffolding duplicated across three test files" (`Type: quality`,
    audit-041 update names `tests/test_nav_shell.py` among 13 files) — **out of scope**;
    audit 041 recommends it as its own ticket.
  - `web/routes/common.py`: none open.

## Verification
- Start `uvicorn web.main:app`, then hit the two test routes the `tests/test_error_handling.py`
  fixture registers (or temporarily raise from a real route). Confirm in the browser: header
  shows "Fantasy Hockey" and nothing else on the right; body shows the message and a working
  "Back to home" link.
- Repeat both while logged in with a real session cookie. The page must look identical — that
  is the observable proof the handlers derive nothing.
- Walk the unaffected navs: logged-out `/` (login-only), authenticated `/` and `/overview`
  (Overview → Waiver → Projection → Logout), `/demo/overview` (demo nav + "Log in with
  Yahoo"). None of these may change.
- `.venv/bin/python -m pytest tests/` green.
- Confirm the improvements item "Error pages show the authenticated nav to logged-out
  visitors" has been moved to `docs/archive/improvements-closed.md`.

## Dependencies
- Tech Lead ruling — RESOLVED 2026-07-25 (`docs/DECISIONS.md` "Nav shell: render sites that
  cannot resolve a user declare the state unknown and render nav-free"). No dependency on
  036b (that ruling says so explicitly), and none on 037/038/040.
- **Ticket 044 depends on this one** — both edit the same `base.html` branch block, so they
  cannot run in parallel. Land 042 first.
- **Let ticket 039 (`fly.toml`, the M1 gate) finish first.** As of 2026-07-26 it is already
  implemented and sits at `Status: qa` with `tickets/039-done.md` written, so "first" means
  completing its QA and review, not scheduling an Engineer session. No file overlap with this
  ticket; the only interaction is the audit counter. `scripts/audit_due.py` reads 2.0 / 5.0
  today; this ticket is full-process (1.0) and 039 is an architectural-surface ticket, which
  orchestrator pre-flight blocks once the counter reaches 5.0 (relevant if 039 needs a fix
  round or a re-run). 042 + 043 (light, 0.5) + 044 leaves it at 4.5 / 5.0, so 039 stays
  runnable either way — but it is the M1 gate and should clear regardless.
