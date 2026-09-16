## Implementation complete — 043

**What I did:**
- Added a secondary "Try the demo" link to `home.html`'s unauthenticated branch,
  linking to `/demo/overview`, rendered next to the existing "Log in with Yahoo" button.
- Applied the two in-scope test sweeps from the ticket's Notes: simplified TC14's
  redundant `<h1>` guard, and deleted TC18's non-discriminating trailing
  `"Alpha League" in body` assertion + its comment.
- Added two new tests: `test_home_unauthenticated_shows_demo_cta` (next to TC14) and
  `test_home_authenticated_no_demo_cta` (next to TC16, the authenticated counterpart).
- Moved three `docs/improvements.md` items to `docs/archive/improvements-closed.md`
  with ticket-043 resolution notes: the scoped-from item ("Add demo mode entry point
  on home page") and the two sweep items (TC14, TC18), both on
  `tests/test_home_routes.py`, a file this ticket modified.

**Files changed:**
- `web/templates/home.html` — added one `<a href="/demo/overview">Try the demo</a>`
  line, styled as a bordered/text secondary link, immediately after the existing
  login button inside the `{% if leagues is none %}` branch. No other lines touched.
- `tests/test_home_routes.py` — TC14 simplified, TC18 sweep applied, two new tests
  added (TC20 `test_home_unauthenticated_shows_demo_cta`, TC21
  `test_home_authenticated_no_demo_cta`).
- `docs/improvements.md` — removed the three resolved items (see above).
- `docs/archive/improvements-closed.md` — appended the three closed items with
  ticket-043 resolution notes.

**Acceptance criteria status (self-check):**
- [x] `GET /` without a session cookie returns 200 and the body contains
  `href="/demo/overview"` with visible text "Try the demo" — evidence:
  `test_home_unauthenticated_shows_demo_cta` (green), plus a manual curl against a
  running `uvicorn` instance showing the rendered `<a href="/demo/overview" ...>Try
  the demo</a>` tag.
- [x] The demo link renders alongside (not instead of) the login CTA and is visually
  secondary — evidence: same manual curl output shows both anchors present; the demo
  link uses `border border-gray-300 text-gray-700 ... hover:bg-gray-50` (bordered/text
  style) versus the login button's `bg-purple-600 text-white` (filled). This is a
  visual criterion the test suite can't fully judge on its own, so I ran the app and
  inspected the rendered markup directly rather than relying only on string-presence
  assertions.
- [x] `GET /` with a valid session cookie contains no `href="/demo/"` link — evidence:
  `test_home_authenticated_no_demo_cta` (green), asserting `'href="/demo/'` is absent
  from an authenticated response body.
- [x] The logged-out nav is unchanged (`<nav>` still only has
  `("/auth/login", "Log in with Yahoo")`) — evidence: existing
  `tests/test_nav_shell.py::test_logged_out_home_nav_is_login_only` and
  `tests/test_home_routes.py::test_home_unauthenticated_nav_has_no_auth_gated_links`
  both still pass unmodified; the new link's `/demo/overview` href does not contain
  the guarded `href="/overview"` substring.
- [x] `.venv/bin/python -m pytest tests/` is green — 471 passed, 0 failed (see below).

**How to verify (for QA):**
- `cd /Users/carlinleung/personal_dev/fantasy_hockey && .venv/bin/python -m pytest tests/`
  — expect `471 passed`.
- `uvicorn web.main:app --reload`, visit `/` logged out: both CTAs visible, "Log in
  with Yahoo" filled purple, "Try the demo" bordered/secondary next to it. Click it,
  confirm landing on `/demo/overview` with the demo nav.
- Log in (or set a valid `session_id` cookie against a seeded session), revisit `/`:
  confirm no "Try the demo" link or any `/demo/` href appears anywhere on the page.
- Confirm `docs/improvements.md` no longer lists "Add demo mode entry point on home
  page", the TC14 item, or the TC18 item, and that all three now appear in
  `docs/archive/improvements-closed.md` with `**Resolved:** Ticket 043` notes.

**Scope notes:**
- None beyond what's flagged below. `web/routes/home.py` was correctly left
  untouched per the ticket's Out of scope — `leagues is none` already gates the
  branch, no new context key was needed.
- The `docs/ui-brief.md` file showing as untracked in `git status` predates this
  ticket and was not created or touched by me.

**Improvements items closed:**
- "Add demo mode entry point on home page" (`Type: quality`, scoped-from item this
  ticket resolves) — moved to `docs/archive/improvements-closed.md`.
- "Simplify redundant assertion in TC14 of `test_home_routes.py`" (`Type: quality`,
  in-scope sweep) — moved to `docs/archive/improvements-closed.md`.
- "TC18's league-label assertion in `test_home_routes.py` does not discriminate"
  (`Type: quality`, in-scope sweep) — moved to `docs/archive/improvements-closed.md`.
- Left open (explicitly out of scope per ticket Notes): "Projection route test
  scaffolding duplicated across three test files" (audit-041 `conftest.py`
  consolidation) — not started.

**Known limitations / things I couldn't fully test:**
- One deviation from the ticket's literal TC14 sweep instruction, flagged here
  explicitly: the ticket and the improvements.md item both specify replacing TC14's
  assertion with the literal `assert "Your Leagues" not in body`. Running that
  verbatim **fails** — `home.html`'s `{% block title %}Your Leagues{% endblock %}`
  is a fixed string rendered on every branch, so `<title>Your Leagues</title>` is
  always in the body regardless of auth state, and a plain `not in body` check
  always trips on it. I kept the redundant-guard removal (the actual defect the
  improvements item identified) but scoped the check to content after `<body>`
  (`body.split("<body>", 1)[1]`) instead of dropping the split entirely, so the test
  stays correct and green. Noted in the closed-item's resolution note in
  `docs/archive/improvements-closed.md` as well, in case the PM/Reviewer wants to
  double check my read of this.
- No other known gaps. All five ACs are covered by automated tests plus one manual
  render check for the visual-secondary styling criterion (AC2), per the light-ticket
  exception in the Engineer persona.
