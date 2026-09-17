## Implementation complete — 050

**What I did:**
- Added `px-4` to `error.html`'s content container, matching the class shape used by every
  other page shell (`home.html:6` et al.), so the heading, detail text, and "Back to home"
  link no longer sit flush against the viewport edge at phone width.
- Swept the forecast input #6 improvements item: added `scope="module"` to the `client`
  fixture in `tests/test_error_handling.py` so the two test-only routes register once per
  module instead of once per test.
- Closed that swept item in `docs/archive/improvements-closed.md` with a ticket-050
  resolution note, and removed it from `docs/improvements.md`.
- Left the "Error page 'Back to home' link does not read as clickable" item open (per the
  ticket's explicit instruction) but added an `Update (Ticket 050)` note to it recording
  that the 375 px clip half is now fixed and the entry stays open for the link-affordance
  half, reserved for the M1 UI re-design.

**Files changed:**
- `web/templates/error.html` — content container class changed from
  `max-w-xl mx-auto mt-16 text-center` to `max-w-xl mx-auto mt-16 px-4 text-center`.
- `tests/test_error_handling.py` — `client` fixture decorator changed from `@pytest.fixture`
  to `@pytest.fixture(scope="module")`.
- `docs/improvements.md` — removed the now-closed "Scope `client` fixture..." item; appended
  an `Update (Ticket 050)` note to the "Back to home link does not read as clickable" item.
- `docs/archive/improvements-closed.md` — added the closed "Scope `client` fixture..." entry
  with a ticket-050 resolution note.

**Acceptance criteria status (self-check):**
- [x] AC1: "`web/templates/error.html`'s content container carries horizontal padding
  matching the other page shells (`px-4`)." — evidence: `git diff web/templates/error.html`
  shows `px-4` added; confirmed present in rendered output via a TestClient request to a
  route that raises an unhandled exception (`max-w-xl mx-auto mt-16 px-4 text-center` found
  in the response body).
- [x] AC2: "Rendering the error page at 375 px viewport width shows the heading, the detail
  text and the 'Back to home' link fully inside the viewport, with no horizontal page
  scroll." — evidence is structural, not a rendered screenshot: no browser or Playwright is
  available in this sandbox (checked; `playwright` not installed, no `chromium` on PATH).
  I verified instead that the class change is byte-identical in shape to the four other page
  shells named in the ticket's Why (`home.html:6`, `overview/index.html:6`,
  `overview/head_to_head.html:6`, `projection/index.html:6`, `waiver/index.html:6`), all of
  which use `px-4` and are treated in this repo as already correct at phone width. `px-4`
  insets the container 16px from each side regardless of viewport width, at any width
  including 375px, which removes the flush-to-edge condition the ticket's Why section
  describes. See "Known limitations" below — flag this for a manual/QA visual check in an
  actual browser if one is available to QA.
- [x] AC3: "The existing error-handling tests still pass unchanged
  (`.venv/bin/python -m pytest tests/test_error_handling.py`)." — ran it: `7 passed`.

**How to verify (for QA):**
- `.venv/bin/python -m pytest tests/` — full suite, expect 477 passed (baseline unchanged;
  no test count change, since the fixture-scope change doesn't add or remove tests).
- `.venv/bin/python -m pytest tests/test_error_handling.py -q` — expect `7 passed`.
- If a browser is available: `uvicorn web.main:app --reload`, hit a route that triggers the
  500/502 handler, and view it at 375px device emulation width. Confirm the heading, detail
  text, and "Back to home" link sit fully inside the viewport with a visible left/right
  gutter and no horizontal page scroll.
- Confirm the "Back to home" link markup is byte-identical to before this ticket
  (`class="mt-6 inline-block text-sm text-gray-600 hover:text-gray-800"`, still anchored to
  `/`) — this ticket changed only the container, not the link.
- Confirm the header still renders nav-free (no Overview/Waiver/Projection/Logout links) —
  unaffected by this change, `base.html`'s `auth_state_unknown` branch was not touched.

**Scope notes:**
- None beyond what the ticket already flagged. No change to `base.html`, no change to the
  "Back to home" link's styling.

**Improvements items closed:**
- "Scope `client` fixture in `test_error_handling.py` to module level" (Code review 009) —
  moved to `docs/archive/improvements-closed.md` with a ticket-050 resolution note.
- Named but NOT closed (per ticket instruction): "Error page 'Back to home' link does not
  read as clickable" (Code review 042) — stays open in `docs/improvements.md` for the
  link-affordance half, reserved for the M1 UI re-design. Added an `Update (Ticket 050)`
  note recording that the 375 px clip half it also referenced is now fixed.

**Known limitations / things I couldn't fully test:**
- AC2 (the 375 px visual check) was not verified in an actual rendered browser — no
  Playwright/browser tooling is available in this sandbox. Verification was structural
  (class-shape match to four other already-trusted page shells, confirmed present in the
  actual rendered response body via TestClient). QA should do the real 375 px device-emulation
  check called for in the ticket's "Verification" section if browser tooling is available to
  them.
