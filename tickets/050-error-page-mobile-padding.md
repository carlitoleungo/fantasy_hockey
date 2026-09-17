# 050 — Error page body clips at phone width

## Status
ready

## Type
bug

## Process
light

## Milestone
m1

## Touches
- web/templates/error.html
- tests/test_error_handling.py

## Why
At 375 px (a common phone width) the error page's content container is
`max-w-xl mx-auto` with no horizontal padding, so the heading, the detail message
and the "Back to home" recovery link run flush into the right edge of the viewport
and clip. Confirmed pre-existing by QA 042 (it rendered the pre-042 templates at the
same width). A 500/502 is already the worst moment in the app; the one page whose
entire job is "explain and offer a way out" should not cut off the way out. Every
other page container in `web/templates/` already carries `px-4`
(`home.html:6`, `overview/index.html:6`, `overview/head_to_head.html:6`,
`projection/index.html:6`, `waiver/index.html:6`) — `error.html` is the only
outlier, so this is a consistency fix, not a design decision.

## Acceptance criteria
- [ ] `web/templates/error.html`'s content container carries horizontal padding matching the other page shells (`px-4`).
- [ ] Rendering the error page at 375 px viewport width shows the heading, the detail text and the "Back to home" link fully inside the viewport, with no horizontal page scroll.
- [ ] The existing error-handling tests still pass unchanged (`.venv/bin/python -m pytest tests/test_error_handling.py`).

## Out of scope
- **Restyling the "Back to home" link so it reads as clickable.** That is the open
  `docs/improvements.md` item "Error page 'Back to home' link does not read as clickable",
  and Code Review 042 deliberately assigned it to the M1 UI re-design so that one shared
  link/control style is settled once and applied to the nav and this link together. Do not
  add an underline or a link colour here — a one-off restyle is exactly what that item
  says not to do.
- Any other change to `error.html`'s copy, layout, or the `base.html` header.

## Notes for the Engineer
- This is a one-line class change. Follow `web/templates/home.html:6` verbatim for the
  container class shape.
- `error.html` extends `base.html` and renders nav-free via `auth_state_unknown`
  (ticket 042, DECISIONS 2026-07-25). Do not touch that branch — ticket **044** is
  actively editing the same `base.html` branch block.
- Open `docs/improvements.md` items on files in `Touches`:
  - `error.html` — **"Error page 'Back to home' link does not read as clickable"**
    (`Type: quality`). **Explicitly OUT of scope**, see above; it is reserved for the M1
    UI re-design. Mention it in handoff, do not fix it. The 375 px clip this ticket fixes
    is the "related observation" recorded in that same entry, so name that entry in the
    handoff note but do **not** move it to the closed archive — it stays open for the
    link-affordance half.
  - `tests/test_error_handling.py` — **"Scope `client` fixture in `test_error_handling.py`
    to module level"** (`Type: quality`, line 8). This one the Engineer **will** sweep under
    their input #6: add `scope="module"` to the fixture decorator so the two test routes are
    registered once instead of seven times. It is forecast here so the extra hunk is expected,
    not a surprise, and **it does close** — move it to
    `docs/archive/improvements-closed.md` on handoff.
- No architectural surface. No `data/` or `analysis/` change. No Yahoo API involvement.

## Verification
- Run `uvicorn web.main:app --reload`, trigger the error page, and view it in a 375 px
  device emulation. Confirm no content touches the viewport edge and the page body does
  not scroll horizontally.
- Confirm the "Back to home" link is still present, still anchored to `/`, and still
  styled exactly as before (this ticket changes the container, not the link).
- Confirm the header still renders nav-free (no Overview/Waiver/Projection/Logout links).
- `.venv/bin/python -m pytest tests/test_error_handling.py`

## Dependencies
- None. Independent of 044 (different template file).
