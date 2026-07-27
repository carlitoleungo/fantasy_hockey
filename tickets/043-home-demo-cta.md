# 043 — "Try the demo" CTA on the logged-out home page

## Status
ready

## Type
feature

## Process
light

## Milestone
m2

## Touches
- web/templates/home.html
- tests/test_home_routes.py

## Why
Demo mode is fully built (`/demo/overview`, `/demo/waiver`, `/demo/projection`) and is the
only way to evaluate the app without handing over a Yahoo account, but nothing on the site
links to it. A visitor who lands on `/` sees exactly one option: "Log in with Yahoo". Anyone
unwilling to authorise an OAuth app before seeing what it does has no path forward and
leaves. One link on the logged-out home page turns demo mode from a hidden URL into the
front door it was built to be.

## Acceptance criteria
- [ ] `GET /` without a session cookie returns 200 and the body contains a link with `href="/demo/overview"` whose visible text reads "Try the demo".
- [ ] That link renders alongside (not instead of) the existing "Log in with Yahoo" CTA, and is visually secondary to it (e.g. a bordered/text link next to the filled purple button).
- [ ] `GET /` with a valid session cookie contains no `href="/demo/"` link — the CTA appears only in the unauthenticated branch.
- [ ] The logged-out nav is unchanged: `<nav>` still contains only `("/auth/login", "Log in with Yahoo")`.
- [ ] `.venv/bin/python -m pytest tests/` is green.

## Out of scope
- **`web/routes/home.py`.** No route change is needed — `home.html` already receives
  `leagues is none` on the unauthenticated branch, which is the condition to render inside.
  Do not add a context key for this.
- Linking `/demo/waiver` or `/demo/projection` from the home page. One entry point is enough;
  the demo nav (shipped in 036b) carries visitors between the three demo pages once they are
  in. A second link here is design sprawl, not a fix.
- A dedicated login/landing page. That is a separate `docs/backlog.md` entry
  ("Migration: Login page") and is deliberately not in play here.
- Any copy rewrite of the existing headline or sign-in paragraph.
- Explaining what demo mode is in prose. The link text carries it.

## Notes for the Engineer
- The insertion point is `web/templates/home.html` lines 13-16 — the `{% if leagues is none %}`
  branch, immediately after the existing `<a href="/auth/login">` button. Follow that anchor's
  Tailwind shape for the new link; make the demo link the secondary of the two.
- Demo route paths are confirmed live: `web/routes/overview.py:225` (`/demo/overview`),
  `web/routes/waiver.py:91`, `web/routes/projection.py:287`. All three are on `public_router`
  and take no user dependency.
- **Don't trip the existing nav guard.** `tests/test_nav_shell.py::test_logged_out_home_nav_is_login_only`
  asserts `href="/overview"` (with the closing quote) appears nowhere in the logged-out home
  body. `href="/demo/overview"` does not contain that string, so the assertion still holds —
  but keep the `/demo/` prefix, don't build the URL any other way.
- Add the new test next to TC14 (`test_home_unauthenticated_shows_login_cta`,
  `tests/test_home_routes.py:358`) and its authenticated counterpart wherever the
  authenticated-branch tests live in that module.
- **Open `docs/improvements.md` items on files in `Touches`:**
  - "Add demo mode entry point on home page" (`Type: quality`, `web/templates/home.html`) —
    **this is the item this ticket resolves.** Move it to
    `docs/archive/improvements-closed.md` with a `**Resolved:**` note on handoff.
  - "Simplify redundant assertion in TC14 of `test_home_routes.py`" (`Type: quality`, line
    367) — **in scope as a sweep.** Replace
    `assert "<h1" in body and "Your Leagues" not in body.split("</head>", 1)[1]` with
    `assert "Your Leagues" not in body`. You are editing that test anyway.
  - "TC18's league-label assertion in `test_home_routes.py` does not discriminate"
    (`Type: quality`, lines 450-451) — **in scope as a sweep.** Delete the trailing
    `assert "Alpha League" in body` and the comment above it; the comment is the riskier
    half, since it could lead someone to delete TC9 as a duplicate. TC9 and
    `tests/test_nav_shell.py::test_authenticated_home_nav_and_league_label` already guard
    that behaviour properly.
  - "Projection route test scaffolding duplicated across three test files" (`Type: quality`,
    audit-041 update names `tests/test_home_routes.py` among 13 files) — **out of scope**;
    audit 041 recommends the `tests/conftest.py` consolidation as its own ticket. Do not
    start it here.
- Expected diff: roughly 3 lines of template, one new test, and the two sweep edits above.
  If it grows past that, stop and flag rather than absorbing it.

## Verification
- `uvicorn web.main:app`, visit `/` logged out: both CTAs visible, "Try the demo" clearly
  secondary. Click it and land on `/demo/overview` with the demo nav rendered.
- From `/demo/overview`, confirm the demo nav still moves between the three demo pages and
  offers "Log in with Yahoo" (036b behaviour, unchanged).
- Log in, revisit `/`: league picker renders and no demo link is present anywhere on the page.
- `.venv/bin/python -m pytest tests/` green.
- Confirm the improvements item "Add demo mode entry point on home page" has been moved to
  `docs/archive/improvements-closed.md`.

## Dependencies
- None. No file overlap with 042 or 044 (they touch `base.html`; this touches `home.html`'s
  content block only), so this may run in parallel with either.
- **Let ticket 039 (`fly.toml`, the M1 gate) finish before the 042/043/044 batch.** As of
  2026-07-26 it is already implemented and sits at `Status: qa`, so this means completing its
  QA and review. No file overlap; the only interaction is the audit counter.
  `scripts/audit_due.py` reads 2.0 / 5.0 today and 039 is architectural, so orchestrator
  pre-flight blocks it once the counter reaches 5.0 (relevant if 039 needs a fix round or a
  re-run). This ticket is `Process: light` and counts 0.5, which is what keeps the batch total
  at 4.5 / 5.0 instead of exactly 5.0 — **if it is ever promoted to full process, 039 must
  clear first.**
