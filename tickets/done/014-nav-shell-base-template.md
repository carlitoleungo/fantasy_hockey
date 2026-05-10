# 014 — Nav shell in base.html

## Summary
Adds a minimal site header to `web/templates/base.html` that every page
inheriting from `base.html` will render automatically. The header shows the
app name (linking to `/`) and a logout link; if the session has a selected
league, it also shows the league name as a secondary label on the left. This
is a prep ticket that establishes the shared header before the first feature
page (ticket 015) lands. No new routes, no new data access.

## Acceptance criteria
- [ ] `web/templates/base.html` renders a `<header>` element inside `<body>`,
  before the `{% block content %}` block, containing (a) an app-name link to
  `/`, (b) an optional selected-league label when `selected_league_name` is
  truthy, and (c) a logout link to `/auth/logout`.
- [ ] The existing logout link in `web/templates/home.html` is removed
  (now rendered by the shared header); the "Your Leagues" heading remains.
- [ ] `web/routes/home.py` passes `selected_league_name` into the
  `home.html` render context — resolved from the user's selected
  `league_key` by looking it up in the `leagues` list already fetched for
  the page (no extra Yahoo API calls).
- [ ] `GET /` with a selected league renders the league name in the header;
  `GET /` with no selected league renders the header without a league label
  (no layout break).
- [ ] A unit test asserts the header contains the app-name anchor and the
  logout link on a rendered `home.html` response.

## Files likely affected
- `web/templates/base.html`
- `web/templates/home.html`
- `web/routes/home.py`

## Dependencies
- Requires 011 (landing page + league selector) — already complete.

## Notes for the engineer

**Decision reference.** Logged in `docs/decisions.md` 2026-04-19 ("Nav shell:
minimal league label + logout in base.html; feature links added per ticket").
This ticket establishes the shared header. **Do not add feature navigation
links** (Overview / Waiver / Projection) — those get added per feature-page
ticket in roadmap order, starting with ticket 015.

**What goes in the header, visually:**
- Left: `<a href="/">Fantasy Hockey</a>` (app name, Tailwind utility classes
  for a subtle but tappable text link). If `selected_league_name` is set,
  render it as a muted secondary label right of the app name, e.g. a
  `·` separator and `text-gray-500`.
- Right: `<a href="/auth/logout">Logout</a>`, small, muted.
- Use Tailwind utilities consistent with `home.html` (e.g. `border-b`,
  `px-4 py-3`, `flex items-center justify-between`).

**`selected_league_name` resolution.** `web/routes/home.py` already fetches
`leagues` (a list of dicts with `league_key` and `league_name`) and queries
`selected_key` from the session row. Derive the name in Python:
```python
selected_league_name = next(
    (lg["league_name"] for lg in leagues if lg["league_key"] == row["league_key"]),
    None,
) if row and row["league_key"] else None
```
Pass it into the template context. Do **not** add another Yahoo API call.

**Make `selected_league_name` a template variable, not a block.** Feature
pages built in ticket 015+ will call a small helper (added in ticket 015) to
resolve the same value from the session row + a freshly-fetched league list.
Keeping it a plain template variable (default `None` when not set) means
pages that haven't been updated yet don't error — the `{% if %}` guard in
`base.html` handles it.

**Gotchas**
- `home.html` currently has its own `flex items-center justify-between` row
  containing the "Your Leagues" heading and a logout link. Only remove the
  logout link; keep the heading in place (re-use the existing row or
  simplify to just `<h1>`).
- Do not modify `auth/oauth.py` logout flow — the existing `/auth/logout`
  route is the target.

## Notes for QA
- Manual: load `/` without a selected league → header renders "Fantasy
  Hockey" + "Logout", no separator, no crash.
- Manual: select a league via the form → refresh `/` → header now shows the
  league name as a muted secondary label.
- Manual: visit `/error` or any page that extends `base.html` → header
  renders (though `selected_league_name` may be absent — that's fine).
- Verify the login page (`/auth/login`) is unaffected — it likely doesn't
  extend `base.html`, but if it does, the header should still render without
  a league label.
- Regression: the existing "Select" buttons on `/` still work.
