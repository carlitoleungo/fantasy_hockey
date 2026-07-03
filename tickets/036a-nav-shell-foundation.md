# 036a — Nav shell foundation: shell_context helper + conditional base.html + home adoption

## Status
ready

## Type
feature

## Touches
- web/routes/common.py
- web/templates/base.html
- web/routes/home.py

## Why
After ticket 023 landed optional auth on `GET /`, an unauthenticated visitor on the home
page sees a "Log in with Yahoo" CTA in the content area **but also** sees the full header
nav — Overview, Waiver, Projection, Logout — rendered unconditionally by
`web/templates/base.html:21-26`. All four targets are auth-gated (or a no-op logout), so
every one of those links 302s the visitor to `/auth/login`. The home page is the public
entry point; presenting links that immediately bounce a logged-out visitor is broken. This
ticket builds the shared shell-context mechanism the Tech Lead chose (Option C) and applies
it to the home page as the reference adoption, fixing the logged-out-home nav. It is the
foundation the demo pages adopt in 036b.

## Acceptance criteria
- [ ] `GET /` with no session returns 200 and its header nav contains no auth-gated feature link — no `/overview`, `/waiver`, `/projection`, or `/auth/logout` href — so nothing in the logged-out home nav 302s to `/auth/login` when clicked; a "Log in with Yahoo" affordance is present instead.
- [ ] `GET /` with an authenticated session returns 200 with the full authenticated nav (`/overview`, `/waiver`, `/projection`, `/auth/logout`) in roadmap order, and the selected-league label renders (`selected_league_name` now threaded via the helper on the authenticated branch, fixing the pre-existing home-branch drift).
- [ ] A not-yet-migrated authenticated page (e.g. `GET /overview`) still renders the authenticated nav exactly as it does today — `base.html` defaults to the authenticated nav when `is_authenticated`/`demo_mode` are absent, so nothing 036b hasn't touched yet regresses.
- [ ] `python3 -m pytest tests/` is green, including a new assertion that the logged-out-home nav differs from the authenticated-home nav (logged-out body lacks a `/waiver` nav link and contains the login CTA; authenticated body contains `/waiver`).

## Out of scope
- Adopting the helper in `overview.py`, `waiver.py`, `projection.py` — that is 036b.
  `base.html` defaulting to the authenticated nav is what keeps those pages correct until
  036b migrates them.
- `web/templates.py` — untouched. The rejected Option B (context processor) was the only
  mechanism that touched it; Option C does not.
- Fragment templates (`_table.html`, `_matchup.html`) — untouched; they don't extend
  `base.html`.
- The "Try the demo" home-page entry point (the `docs/improvements.md` "Add demo mode entry
  point on home page" item) — deliberately a separate follow-up ticket. Do not fold it in.
- Any change to route auth requirements, `require_user`/`optional_user`, or route
  registration. This ticket only changes what the shared shell renders.
- Restyling the header beyond the conditional link set (no design pass).

## Notes for the Engineer
- **Mechanism is decided — do not re-derive.** `docs/DECISIONS.md` 2026-07-03 "Nav shell:
  conditional on auth/demo state via shared shell-context; no second auth-derivation path"
  (Option C; extends the 2026-04-19 nav-shell entry; applies the 2026-05-30 `optional_user`
  decision to template context). Option B (context processor) was rejected outright — do
  not add `context_processors` to `web/templates.py`.
- Add `shell_context(current_user_or_none, *, demo=False, league_name=None)` to
  `web/routes/common.py` (existing shared-helper home — see its `_get_league_key` helper and
  the module docstring citing `docs/DECISIONS.md` 2026-05-30 "Shared route helpers"). It
  returns `{"is_authenticated": ..., "demo_mode": ..., "selected_league_name": ...}`, deriving
  `is_authenticated` from whether the passed user is `None` — **reuse the user already
  resolved by the route's `optional_user`/`require_user` dependency; never do a second
  cookie/DB lookup.**
- `base.html` must branch on `is_authenticated` / `demo_mode` and **default to the
  authenticated nav when both flags are absent** (critical: this is what makes the split
  safe — every not-yet-migrated page keeps its current render). See the Tech Lead constraint
  in the DECISIONS entry.
- Feature-link ordering (Overview → Waiver → Projection) from `docs/DECISIONS.md`
  2026-04-19 must be preserved in the authenticated nav.
- `web/routes/home.py` uses `optional_user`; adopt `shell_context()` in **both** the
  authenticated and unauthenticated branches so the home page is the reference for 036b to
  copy. The unauthenticated branch passes the user as `None`.
- **DoD (audit 032 action 4):** this ticket resolves the `docs/improvements.md` item
  **"Nav header shows auth links to unauthenticated visitors"** (its Detail is explicitly the
  home page / `GET /` logged-out nav). On handoff, move that item to `## Closed` with a
  resolution note citing this ticket. Leave the "Add demo mode entry point on home page" item
  open — it is a separate follow-up ticket, not part of this work.

## Verification
- Manual logged-out home: `GET /` with no session → nav shows the login affordance and no
  link that 302s to `/auth/login` when clicked.
- Manual authenticated home: logged in, `GET /` → full nav in roadmap order, all links 200,
  league label present.
- Manual regression check: `GET /overview` while authenticated → nav unchanged from today
  (base.html default path).
- `python3 -m pytest tests/` green, including the new logged-out-vs-authenticated home nav
  assertion.

## Dependencies
- Tech Lead consult on the injection mechanism — RESOLVED 2026-07-03 (Option C; logged in
  `docs/DECISIONS.md`).
- None on other tickets.
