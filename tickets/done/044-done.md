# Implementation complete — 044

**What I did:**
- Flipped `base.html`'s absent-flag default to fail-safe, implementing the "Forward
  commitment (sequenced after 036b, not part of this fix)" paragraph of
  `docs/DECISIONS.md` **"Nav shell: render sites that cannot resolve a user declare the
  state unknown and render nav-free; exception handlers never derive auth" (2026-07-25)**.
  `{% elif is_authenticated is undefined or is_authenticated %}` became two branches:
  an empty `{% elif is_authenticated is undefined %}` (nav-free) followed by
  `{% elif is_authenticated %}`. The "undefined" and "false" rows stay distinguishable —
  an explicit `is_authenticated=False` still falls to the `{% else %}` login link.
- Left the `auth_state_unknown` branch first and explicit, untouched (ticket 042 /
  DECISIONS 2026-07-25 name it for its cause, not its effect).
- Updated the `tests/test_nav_shell.py` branch matrix (the two cases that asserted the old
  default now expect `[]`), its inline comments, and the module docstring's fourth bullet.
  Added one test asserting the brand link survives the nav-free default.
- Retired both stale comments (AC5) and renamed the misleading test in
  `tests/test_overview_routes.py`.
- Appended the mutation-probe `.pyc` staleness trap to `docs/LEARNINGS.md`.
- Moved all three resolved `docs/improvements.md` items to
  `docs/archive/improvements-closed.md`.

**Files changed:**
- `web/templates/base.html` — split the combined `undefined or is_authenticated` condition;
  deleted the stale lines 21-22 comment; added a short comment citing DECISIONS 2026-07-25
  on the new empty branch so it isn't mistaken for dead code.
- `tests/test_nav_shell.py` — branch matrix expectations for `{}` and `{"demo_mode": False}`
  flipped to `[]` with new comments; docstring bullet 4 rewritten; new
  `test_base_html_absent_flags_keep_the_brand_link`.
- `tests/test_overview_routes.py` — TC9's comment rewritten (since 036b `/overview` does
  pass `shell_context()`, so the test proves the explicit `is_authenticated=True` branch);
  test renamed `test_overview_renders_authenticated_nav` (dropped `_by_default`).
  Assertions unchanged.
- `docs/LEARNINGS.md` — new entry "Purge `__pycache__` between mutation probes, or CPython
  replays the previous result", placed directly after the patch-target gotcha.
- `docs/improvements.md` / `docs/archive/improvements-closed.md` — three items moved.

**Acceptance criteria status (self-check):**
- [x] **AC1** — empty context renders the brand link and a nav with zero `<a>` elements.
  Evidence: `test_base_html_absent_flags_keep_the_brand_link` (asserts the exact
  `<a href="/" …>Fantasy Hockey</a>` inside `_header_left`, and `_nav_links(html) == []`),
  plus the `({}, [])` matrix row.
- [x] **AC2** — `{"demo_mode": False}` with no `is_authenticated` key renders nav-free.
  Evidence: the `({"demo_mode": False}, [])` matrix row, previously `AUTHENTICATED_NAV`.
- [x] **AC3** — every explicit branch unchanged. Evidence: the three remaining matrix rows
  (`is_authenticated=True` → `AUTHENTICATED_NAV` in Overview/Waiver/Projection/Logout
  order; `{False, demo_mode: False}` → login link only; `{False, demo_mode: True}` →
  `DEMO_NAV`) plus `test_base_html_auth_state_unknown_renders_nav_free`, which still passes
  unmodified and still covers `auth_state_unknown` combined with each other flag. The
  `auth_state_unknown` branch is still the first `{% if %}`.
- [x] **AC4** — mutation probe recorded below; all four authenticated full-page branches
  now fail at least one `tests/test_nav_shell.py` test. File restored byte-identical
  (md5 `53e0ec6ee9ad6a77e03e66a122b939bf` before and after; `git status` shows
  `web/routes/overview.py` unmodified). Suite green afterwards.
- [x] **AC5** — both stale comments retired (see Files changed).

**AC4 mutation probe — per-branch results**

`__pycache__` was purged before every single mutation with
`find . -name __pycache__ -type d -not -path "./.venv/*" -exec rm -rf {} +`, and the
original file was restored from a copy after each run. Command per iteration:
`.venv/bin/python -m pytest tests/test_nav_shell.py -q`.

Note: the ticket's Notes cite lines 174, 241 and 311 as the 77-byte collision example, but
241 and 311 are **demo** branches. The authenticated full-page `**shell_context(...)`
spreads in `web/routes/overview.py` are lines **56, 77, 146, 174**, so the probe covers
those four.

| Deleted line | Branch | Result |
|---|---|---|
| 56 | `/overview` empty state | `1 failed, 42 passed` — FAILED `test_authenticated_empty_state_renders_authenticated_nav[/overview]` |
| 77 | `/overview` populated full page | `2 failed, 41 passed` — FAILED `test_authenticated_feature_pages_render_authenticated_nav[/overview]`, `test_demo_nav_differs_from_authenticated_nav` |
| 146 | `/overview/head-to-head` empty state | `1 failed, 42 passed` — FAILED `test_authenticated_empty_state_renders_authenticated_nav[/overview/head-to-head]` |
| 174 | `/overview/head-to-head` populated full page | `1 failed, 42 passed` — FAILED `test_authenticated_head_to_head_renders_authenticated_nav` |

Before this ticket all four of these were silent on nav assertions (QA 040 measured
`32 passed` every time once the header-label assertion was ablated).

**Test suite:** `.venv/bin/python -m pytest tests/` → **479 passed** (baseline 478; the
one added test is `test_base_html_absent_flags_keep_the_brand_link`).

**How to verify (for QA):**
1. `.venv/bin/python -m pytest tests/` → 479 passed.
2. Render matrix directly: `templates.env.get_template("base.html").render(**ctx)` for the
   five contexts in `tests/test_nav_shell.py::test_base_html_nav_branches` plus
   `auth_state_unknown=True`, asserting on `_nav_links`.
3. Re-run the AC4 probe if you want it independently: copy `web/routes/overview.py` aside,
   `sed -i '' "<L>d"` for L in 56 77 146 174, purging `__pycache__` before each run and
   restoring the copy after each. Confirm `md5 web/routes/overview.py` is
   `53e0ec6ee9ad6a77e03e66a122b939bf` at the end.
4. App walk: `uvicorn web.main:app --reload`. See limitations below for what I could and
   could not walk.

**Scope notes:**
- `tests/test_nav_shell.py` still carries one further stale comment in the matrix ("Demo
  branch shipped in 036a, dormant until 036b adopts it"). It is not named in AC5 and 036b
  has landed, so it is now inaccurate. I left it alone rather than widen scope — worth a
  line on `docs/improvements.md` or sweeping into the next ticket that opens the file.
- `tests/conftest.py` consolidation remains open and out of scope per audit 041.

**Improvements items closed:**
- "`base.html`'s authenticated-nav default is now unblocked, and 040 measured what it
  costs" — the item this ticket was scoped from.
- "Post-036b stale comments about pages 'not yet' passing `shell_context()`" — both halves.
- "Mutation-probe `.pyc` staleness trap is recorded only in a QA report".

All three moved to `docs/archive/improvements-closed.md` with `**Resolved:** Ticket 044 …`
notes. No `## Closed` section was created in the active tracker.

**Known limitations / things I couldn't fully test:**
- **Authenticated pages were not walked in a browser.** I ran the app on port 8077 and
  confirmed by nav-scoped scrape: logged-out `/` → login link only; `/demo/overview`,
  `/demo/waiver`, `/demo/projection` → the demo nav, all unchanged. `/overview`, `/waiver`
  and `/projection` redirect to `/auth/login` without a Yahoo session and returned 429 from
  Yahoo, so I could not see the authenticated nav in the running app. Those branches are
  covered by the `tests/test_nav_shell.py` authenticated cases (real TestClient requests
  against inserted sessions with Yahoo calls mocked), which are green and which the AC4
  probe proves are load-bearing.
- **The error page was not exercised in the running app.** I could not trigger the
  `requests.HTTPError` → 502 or the 500 handler by hand. Its nav-free header is covered by
  the 042 exception-handler tests in `tests/test_nav_shell.py`, which pass unchanged; the
  `auth_state_unknown` branch I did not touch.
- A plain 404 (`/nope`) returns FastAPI's JSON default, not `error.html`, so it renders no
  header at all. That is pre-existing and unrelated to this change.
