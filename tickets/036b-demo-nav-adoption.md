# 036b — Demo nav: adopt shell_context in overview/waiver/projection

## Status
ready

## Type
feature

## Milestone
m2

(Demo mode is the stranger-evaluation path — M2 ("evaluate it via demo mode without signing
in"), not M1's authenticated Overview/Waiver/Projection journey. **Blocked by: ticket 036a**
(m1), which provides `shell_context()` + the conditional `base.html`; see Dependencies below.
A later-milestone ticket depending on an earlier-milestone one is fine. Judgment call, owner
may veto to m1; see the PM scoping report.)

## Touches
- web/routes/overview.py
- web/routes/waiver.py
- web/routes/projection.py

## Why
Demo mode has three fully-functional feature pages (`/demo/overview`, `/demo/waiver`,
`/demo/projection`) but **zero working header navigation**. `web/templates/base.html`
renders the authenticated nav — Overview, Waiver, Projection, Logout — on every page,
including every `/demo/*` route. All four targets are auth-gated (or a no-op logout), so a
demo visitor who clicks any header link is bounced to `/auth/login`: demo mode is internally
functional but has no coherent way to move between its pages or exit. 036a built the
`shell_context()` mechanism and made `base.html` conditional (defaulting to the authenticated
nav). This ticket adopts the helper in the auth **and** demo shells of the three feature
route files so the demo pages render demo-mode nav and the authenticated pages stay unchanged.

## Acceptance criteria
- [ ] On each demo page (`GET /demo/overview`, `/demo/waiver`, `/demo/projection`), the header nav links point at the demo counterparts (`/demo/overview`, `/demo/waiver`, `/demo/projection`), and clicking any of them stays within demo mode — returns 200, never 302→`/auth/login`.
- [ ] On a `/demo/*` page the nav shows no "Logout" link (there is no session to end); it presents an "Exit demo" / "Log in with Yahoo" affordance instead.
- [ ] On the authenticated feature pages (`GET /overview`, `/waiver`, `/projection`), the nav is unchanged — Overview, Waiver, Projection, Logout in roadmap order, all pointing at the authenticated routes and returning 200.
- [ ] `python3 -m pytest tests/` is green, including an assertion of the demo-vs-authenticated nav difference (a `/demo/overview` response body contains a `/demo/waiver` nav link and no bare `/waiver` nav link; an authenticated `/overview` response body contains `/waiver`).

## Out of scope
- The `shell_context()` helper itself and `base.html` — both landed in 036a. This ticket
  only calls the helper from the three feature route files. If `base.html` needs a change,
  something in 036a was incomplete — escalate rather than edit it here.
- `web/routes/home.py` — already migrated in 036a.
- `web/templates.py` and fragment templates — untouched (see 036a and the 2026-07-03
  DECISIONS entry).
- The "Try the demo" home-page entry point — separate follow-up ticket.
- Any change to route auth requirements, `require_user`/`optional_user`, demo-route
  registration, or introducing new routes. Demo nav links point only at demo counterparts
  that already exist.
- Restyling the header beyond the conditional link set (no design pass).

## Notes for the Engineer
- **Mechanism is decided.** `docs/DECISIONS.md` 2026-07-03 "Nav shell: conditional on
  auth/demo state via shared shell-context; no second auth-derivation path" (Option C).
  Follow the home-page adoption from 036a as the reference pattern.
- For each of `overview.py`, `waiver.py`, `projection.py`: the authenticated full-page
  handler(s) call `shell_context(current_user, league_name=...)` (reusing the user already
  resolved by `require_user`); the demo full-page handler calls
  `shell_context(None, demo=True)`. Spread the returned keys into each `TemplateResponse`
  context. Several handlers have empty-state / no-league branches — cover each full-page
  branch that extends `base.html`.
- Demo routes take no user dependency (auth state is implicit) — pass `None` for the user
  and `demo=True`. See `docs/DECISIONS.md` 2026-05-30 "optional_user dependency".
- Demo-route pairing policy (`docs/DECISIONS.md` 2026-05-30): demo nav links must point at
  the demo counterparts that already exist; do not introduce new routes.
- Feature-link ordering (Overview → Waiver → Projection) from `docs/DECISIONS.md`
  2026-04-19 must be preserved in both nav variants.
- Fragment handlers (waiver `_table`, projection `_matchup`, overview `_table`) render
  fragments that do **not** extend `base.html` — do not add shell context to them.

## Verification
- Manual demo walk: from `/demo/overview`, click each header nav link → lands on the
  corresponding `/demo/*` page (200), never `/auth/login`; no Logout link; an exit/login
  affordance is present.
- Manual auth walk: logged in, header nav on `/overview`, `/waiver`, `/projection` is
  unchanged and all links 200.
- `python3 -m pytest tests/` green, including the demo-vs-authenticated nav-difference
  assertions.

## Dependencies
- **036a must complete first** — it provides `shell_context()` and the conditional
  `base.html` this ticket depends on.
