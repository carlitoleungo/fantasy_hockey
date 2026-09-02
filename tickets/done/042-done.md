## Implementation complete — 042

Implements `docs/DECISIONS.md` **2026-07-25** "Nav shell: render sites that cannot resolve a
user declare the state unknown and render nav-free; exception handlers never derive auth"
(Option C), verbatim, in the four-step shape that entry prescribes. Test placement follows
`docs/DECISIONS.md` **2026-07-26** "Tests: one module per feature surface" — both new
assertion groups landed in `tests/test_nav_shell.py`.

**What I did:**
- Added `unknown_auth_shell_context()` to `web/routes/common.py` — a no-argument sibling to
  `shell_context()` returning `{"auth_state_unknown": True}`. No user parameter, no logic.
  `shell_context()` itself is untouched.
- Both exception handlers in `web/main.py` (`requests.HTTPError` → 502, and the 500 handler)
  now spread that helper into their `error.html` context. Neither handler reads a cookie,
  queries the DB, or touches `request.state`.
- `base.html`'s nav now branches on `auth_state_unknown` **first**, before `demo_mode`, and
  renders nothing inside `<nav>`. The header brand link, the shared `<head>`, and the
  `selected_league_name` span are all outside that branch and unchanged.
- `error.html`'s body gained `<a href="/">Back to home</a>`, the explicit recovery path the
  decision requires since authenticated users lose a nav they had before.
- Added 10 tests to `tests/test_nav_shell.py` (2 direct-template/unit, 8 parametrised over the
  two error pages) plus an `error_client` fixture.

**Files changed:**
- `web/routes/common.py` — new `unknown_auth_shell_context()` helper, docstring citing 2026-07-25.
- `web/main.py` — import the helper; spread it into both handlers' `error.html` contexts.
- `web/templates/base.html` — leading `{% if auth_state_unknown %}` branch (empty nav) with a
  comment explaining why it is first; the `demo_mode` and `is_authenticated` branches are
  byte-identical to before, only re-chained onto `{% elif %}`.
- `web/templates/error.html` — one "Back to home" anchor after the `detail` paragraph.
- `tests/test_nav_shell.py` — `error_client` fixture + 10 tests; module docstring gained a
  two-line 042 provenance note. The `test_base_html_nav_branches` parametrisation is unmodified.
- `docs/improvements.md` / `docs/archive/improvements-closed.md` — the mandated item move.

**Acceptance criteria status (self-check):**

- [x] **AC1 — 502 page is nav-free.** `test_error_pages_render_nav_free[/test/nav-http-error-502]`
  asserts `status_code == 502`, `_nav_links(...) == []` (scoped to the `<nav>` element), and that
  none of `href="/overview"`, `href="/waiver"`, `href="/projection"`, `href="/auth/logout"`,
  `href="/auth/login"` appear anywhere in the body. Confirmed live: `GET /test/http-error` on a
  running uvicorn returned 502 with `<nav class="flex items-center gap-4">` containing only
  whitespace.

- [x] **AC2 — 500 page is nav-free and byte-identical with/without a session cookie.**
  `test_error_pages_render_nav_free[/test/nav-unhandled-500]` covers the nav-free half.
  `test_error_pages_identical_with_and_without_session_cookie` asserts
  `authenticated.text == anonymous.text` for both pages; the fixture seeds a genuinely valid
  session row (`sid-test`, `expires_at = now + 3600`, `league_key` set), so a handler that *did*
  derive would resolve a real user. I proved the assertion is not vacuous with a throwaway probe
  route: `request.cookies.get("session_id")` returned `None` without the cookie and `'sid-test'`
  with it, so the cookie genuinely reaches the app. Confirmed live too: `diff` of the anon and
  cookie-bearing responses for both pages, against a seeded valid session in a scratchpad copy of
  the dev DB, reported no difference.

- [x] **AC3 — brand link, shared `<head>`, "Back to home".**
  `test_error_pages_keep_brand_link_and_shared_head` asserts `<title>Error</title>` and the
  Tailwind CDN tag are present, and that `<a href="/"` + `Fantasy Hockey` are in `_header_left(...)`
  (header-scoped, not whole-body). `test_error_pages_offer_back_to_home_in_the_body` asserts
  `<a href="/"` and `Back to home` in `response.text.split("</header>", 1)[1]`, so the link is
  proved to be in the body rather than the header. Seen live in the rendered HTML for both pages.

- [x] **AC4 — every `shell_context()` branch unchanged.** Full suite green with the pre-existing
  nav tests untouched: `test_logged_out_home_nav_is_login_only`,
  `test_authenticated_home_nav_and_league_label`,
  `test_authenticated_feature_pages_render_authenticated_nav[/overview|/waiver|/projection]`,
  `test_demo_pages_render_demo_nav[4 paths]`, the empty-state branch tests, and the unmodified
  `test_base_html_nav_branches` parametrisation. Confirmed live for the branches that need no
  Yahoo call: logged-out `/` renders `href="/auth/login"` only; `/demo/overview`, `/demo/waiver`
  and `/demo/projection` each render the four demo links.

- [x] **AC5 — suite green, parametrisation unmodified.** `.venv/bin/python -m pytest tests/` →
  **469 passed** in 2.07s (baseline 459 + 10 new). `git diff` on `tests/test_nav_shell.py` shows no
  change inside `test_base_html_nav_branches` or its `@pytest.mark.parametrize` list, and
  `tests/test_error_handling.py` is not in the diff.

**Mutation probes (proving the new tests are load-bearing, `__pycache__` purged between each):**

| Mutation | Result |
|---|---|
| Drop the spread from the 502 handler | `test_error_pages_render_nav_free[...-502]` fails |
| Drop the spread from the 500 handler | `test_error_pages_render_nav_free[...-500]` fails |
| Remove the `auth_state_unknown` branch from `base.html` | 3 tests fail (both route cases + the direct-template case) |
| Remove the "Back to home" anchor from `error.html` | both `test_error_pages_offer_back_to_home_in_the_body` cases fail |

**How to verify (for QA):**
1. `.venv/bin/python -m pytest tests/` — expect 469 passed.
2. `.venv/bin/python -m pytest tests/test_nav_shell.py -q` — 42 tests, includes the 10 new ones.
3. Live walk. The two raising routes exist only in test fixtures, so drive them without editing
   the repo: create a throwaway module outside the repo that does `from web.main import app` and
   registers `@app.get("/test/http-error")` raising `requests.HTTPError` and
   `@app.get("/test/unhandled")` raising `Exception`, then
   `PYTHONPATH=<that dir>:. .venv/bin/uvicorn <module>:app --port 8931`.
   - `curl -s -w '%{http_code}' http://127.0.0.1:8931/test/http-error` → 502;
     `/test/unhandled` → 500.
   - In both, `<nav …>` contains no `<a>`; the header shows only
     `<a href="/" …>Fantasy Hockey</a>`; the body shows the detail string and
     `<a href="/" …>Back to home</a>`, which resolves to the home page.
   - Cookie identity: seed a session row with a future `expires_at` into a **copy** of `app.db`,
     point `DB_PATH` at the copy, then `diff` the response with `--cookie "session_id=<that id>"`
     against the response without it. Must be identical.
4. Unaffected navs: logged-out `/` → `href="/auth/login"` only; `/demo/overview`, `/demo/waiver`,
   `/demo/projection` → the four demo links; authenticated `/` and `/overview` → Overview → Waiver
   → Projection → Logout (needs a live Yahoo session, or rely on the mocked tests in step 2).
5. Confirm the improvements item moved: `grep -n "^### .*Error pages" docs/improvements.md`
   returns nothing, and the entry is under `## Closed` in `docs/archive/improvements-closed.md`
   with a `**Resolved:** Ticket 042` note.
6. No demo-mode data work in this ticket — no `data/` function was added, so no `data/demo.py`
   counterpart is owed.

**Scope notes:**
- **Dangling cross-reference in `docs/improvements.md`.** The still-open entry "Post-036b stale
  comments about pages 'not yet' passing `shell_context()`" (line 213) says the `base.html` comment
  "has one remaining beneficiary, `error.html`, which is the defect tracked in 'Error pages show the
  authenticated nav to logged-out visitors' **above**". That item is now in the archive, and its
  premise is also now false — `error.html` no longer falls through to the authenticated-nav default,
  so the `base.html` comment has **zero** remaining beneficiaries. I left the text untouched because
  the ticket puts that entry explicitly out of scope; ticket 044 owns it and should correct both the
  pointer and the "one remaining beneficiary" claim when it retires the comment.
- The `base.html` default-flip (ticket 044) is now genuinely unblocked from this side: the leading
  `{% if auth_state_unknown %}` branch does not collide with it, and 044's edit is confined to the
  `{% elif is_authenticated is undefined or is_authenticated %}` condition I did not touch.
- `docs/LEARNINGS.md` still lacks the mutation-probe `.pyc` staleness entry tracked in
  `docs/improvements.md` ("Mutation-probe `.pyc` staleness trap is recorded only in a QA report").
  `docs/LEARNINGS.md` is not in my `Touches` and the ticket does not scope it, so I did not append.
  Noting that I purged `__pycache__` between every probe above precisely because of that trap, which
  is a third independent confirmation that the entry is worth writing.

**Improvements items closed:**
- "Error pages show the authenticated nav to logged-out visitors" (`Type: quality`,
  `web/templates/error.html`, `web/main.py`) — the item this ticket was scoped from. Moved from
  `docs/improvements.md` `## Open` to `docs/archive/improvements-closed.md` `## Closed` with a
  `**Resolved:** Ticket 042 — …` note. No `## Closed` section was created in the active tracker.
- No other item was closed. The three other open items the ticket lists on `Touches` files
  (the 044 default flip, the 044 stale comment, and audit-041's `conftest.py` consolidation naming
  `tests/test_nav_shell.py`) are all explicitly out of scope and were left under `## Open`.

**Known limitations / things I couldn't fully test:**
- **No real browser.** I walked both error pages, logged-out `/`, and the three demo pages against a
  live uvicorn with `curl` and inspected the rendered HTML. That verifies markup, status codes, and
  byte-identity, but not visual rendering: I did not confirm in a browser that the empty `<nav>`
  leaves no odd gap in the flex header, or that the "Back to home" link's `mt-6 inline-block` spacing
  looks right below the detail paragraph. Those are the two purely visual checks left for QA.
- **Authenticated live nav not walked.** The local dev `app.db` holds only expired sessions and I
  cannot complete a Yahoo OAuth round trip from here, so authenticated `/` and `/overview` were
  verified only by the mocked tests in `tests/test_nav_shell.py`. Incidentally, `GET /` with a seeded
  session carrying a fake access token returned 502 — a real route failing on Yahoo does land on the
  new nav-free error page, which is the end-to-end path this ticket exists for.
- **`error_client` registers routes on the shared module-level `app`**, the same pattern
  `tests/test_error_handling.py` uses, so the routes accumulate across tests in a session. I gave
  them distinct paths (`/test/nav-http-error`, `/test/nav-unhandled`) so the two modules never
  register the same path. This is pre-existing test-harness shape, not something 042 introduced, and
  the `tests/conftest.py` consolidation ticket is the right place to address it.
