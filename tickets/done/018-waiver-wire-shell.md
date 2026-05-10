# 018 — Waiver Wire: shell and filter controls

## Summary
Add `GET /waiver` and `GET /demo/waiver` route handlers plus
`web/templates/waiver/index.html`. The shell renders the full filter
control panel — position pill buttons, a Season / Last 30 days radio,
and stat category chip buttons — with each control wired via HTMX to
`POST /api/waiver/players`. The shell does no player-pool data fetching;
it only fetches what is needed to populate the filter controls (matchup
stat columns + stat category abbreviations). The table area is initially
empty; the first POST, triggered when the user selects any stat chip,
fills it. Ticket 019 builds the POST handler and fragment. This ticket
follows the shell + fragment convention established in tickets 015/016
and adds the "Waiver" link to the nav shell.

## Acceptance criteria
- [ ] `GET /waiver` with a valid session and a selected `league_key`
  returns 200 HTML from `web/templates/waiver/index.html`. The page
  contains:
  - Page title "Waiver Wire" and the subtitle / instructions text (port
    from `pages/03_waiver_wire.py` lines 153–160).
  - Six position pill inputs (`<input type="radio" name="position">` with
    values All / C / LW / RW / D / G, styled as toggle pills). "All" is
    the default selected value.
  - A period radio (`<input type="radio" name="period">` with values
    "Season" / "Last 30 days"). "Season" is the default selected value.
  - One stat chip per entry in `stat_columns(matchups_df)` rendered as
    `<input type="checkbox" name="stats" value="{stat_name}">`, labelled
    with the abbreviation from `get_stat_categories()` (fallback to full
    stat name from `_STAT_FALLBACK_ABBREV` if not found in the API
    response — see `pages/03_waiver_wire.py` lines 78–109).
- [ ] All position pills, the period radio, and all stat chips are
  enclosed in a single `<form id="waiver-filters"
  hx-post="/api/waiver/players" hx-target="#waiver-table-container"
  hx-trigger="change">`. Any change to any control triggers a POST.
- [ ] A `<div id="waiver-table-container">` is rendered below the filters
  containing an instructional empty-state message: "Select one or more
  stat categories above to rank available players." (identical wording to
  the Streamlit prototype, line 240). This message is replaced by the
  `_table.html` fragment on the first POST.
- [ ] `GET /waiver` without a selected league redirects to `/` (302).
  Without a valid session, the `require_user` dependency redirects to
  `/auth/login` (302).
- [ ] `GET /demo/waiver` (no `require_user` dependency) renders the same
  shell template. Stat columns come from `data.demo.load_season_pool()`
  (call `stat_columns()` on the result). Stat categories / abbreviations
  come from `data.demo.get_stat_categories()`. The form action is
  `hx-post="/demo/api/waiver/players"`.
- [ ] `base.html` header gains a "Waiver" link (`href="/waiver"`)
  positioned after "Overview" and before any future "Projection" link,
  consistent with the convention from ticket 015 (append, don't
  restructure).
- [ ] Unit test: `GET /waiver` with a fixture session and a 3-team ×
  2-week × 3-stat matchups DataFrame returns HTML that contains all 6
  position radio input values and all 3 stat checkbox values from the
  fixture.

## Files likely affected
- `web/routes/waiver.py` (new — `GET /waiver` on the auth router, `GET
  /demo/waiver` on the public router)
- `web/templates/waiver/index.html` (new)
- `web/templates/base.html` (add "Waiver" nav link)
- `web/main.py` (register waiver router)

## Dependencies
- Requires 016 (nav shell convention in `base.html`; `_get_league_key`
  helper in `web/routes/overview.py` available as a reference).
- Consumes `data.matchups.get_matchups`, `analysis.team_scores.stat_columns`,
  `data.client.get_stat_categories` — no changes to `data/` or `analysis/`.
- Ticket 019 depends on this ticket: the template directory, router
  registration, and form shape must exist before the POST fragment route
  is wired up.

## Notes for the engineer

**Decision references (`docs/decisions.md` 2026-04-19):**
- Shell + fragment split: this ticket is the shell; 019 is the fragment.
  `index.html` contains the filter controls and the empty `<div
  id="waiver-table-container">`; `_table.html` (019) is swapped into
  that div by HTMX.
- League context: `league_key` resolved from session row via
  `_get_league_key`, same as `overview.py`. If NULL, redirect 302 to
  `/`.
- `selected_league_name` must be passed in every `TemplateResponse`
  context on the shell route (same pattern as tickets 015/016); the
  fragment route (019) omits it.
- Nav: append "Waiver" to `base.html` header — do not restructure.

**Route handler shape:**

```python
router = APIRouter()         # authenticated — require_user on each handler
public_router = APIRouter()  # demo — no require_user

@router.get("/waiver")
def waiver_shell(
    request: Request,
    current_user: CurrentUser = Depends(require_user),
    db=Depends(db_dep),
):
    league_key = _get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)
    session = make_session(current_user.access_token)
    leagues = get_user_hockey_leagues(session)
    selected_league_name = next(
        (lg["league_name"] for lg in leagues if lg["league_key"] == league_key),
        None,
    )
    df = get_matchups(session, league_key)
    stat_cols = stat_columns(df) if df is not None and not df.empty else []
    raw_cats = get_stat_categories(session, league_key)
    stat_abbrev = {c["stat_name"]: c["abbreviation"] for c in raw_cats if "abbreviation" in c}
    return templates.TemplateResponse(
        request, "waiver/index.html",
        {
            "stat_cols": stat_cols,
            "stat_abbrev": stat_abbrev,
            "selected_league_name": selected_league_name,
            "form_action": "/api/waiver/players",
        },
    )

@public_router.get("/demo/waiver")
def demo_waiver_shell(request: Request):
    from data import demo as demo_module
    df = demo_module.load_season_pool()
    stat_cols = stat_columns(df) if df is not None and not df.empty else []
    raw_cats = demo_module.get_stat_categories()
    stat_abbrev = {c["stat_name"]: c["abbreviation"] for c in raw_cats if "abbreviation" in c}
    return templates.TemplateResponse(
        request, "waiver/index.html",
        {
            "stat_cols": stat_cols,
            "stat_abbrev": stat_abbrev,
            "selected_league_name": "Demo League",
            "form_action": "/demo/api/waiver/players",
        },
    )
```

Register both routers in `web/main.py`. The `public_router` does not
include the `require_user` dependency (consistent with `/auth/*` and
`/demo/*` in `docs/ARCHITECTURE.md` Key patterns #3).

**`_STAT_FALLBACK_ABBREV` usage.** The template should prefer
`stat_abbrev[stat_name]` (from the API response) and fall back to a
hardcoded dict if the abbreviation is missing — port the dict from
`pages/03_waiver_wire.py` lines 78–104 into the template context (or a
Jinja global) so abbreviations display correctly even if the API omits
them. Pass the merged dict (`{**_STAT_FALLBACK_ABBREV, **api_abbrev}`)
as `stat_abbrev` to keep the template logic simple.

**HTMX trigger.** Using `hx-trigger="change"` on the `<form>` means
any input change (checkbox toggle, radio change) fires a POST. This
works cleanly for radios and checkboxes without needing per-element
triggers. The form includes a hidden `<input type="hidden" name="page"
id="page-input" value="0">` that pagination buttons (in the 019
fragment) will override via `hx-vals`. Reset `page` to 0 when any
filter changes: add `hx-on:change="document.getElementById('page-input').value='0'"` to the form, or handle in the POST handler by resetting page to 0 when the filter state differs from the previous request (simplest: always pass page=0 on filter changes; the Prev/Next buttons in 019 explicitly set the page value).

**Gotchas**
- `stat_columns(df)` returns the stat names as they appear in the
  matchups DataFrame (full `stat_name` strings, e.g. "Goals Against
  Average"). These are the `value` attributes on checkbox inputs and
  must exactly match what the POST handler receives in `stats[]` —
  no transformation.
- `get_matchups` returns `None` or empty if the season hasn't started.
  Render the shell with `stat_cols = []` and an "No league data
  available yet — the season may not have started." notice above the
  filter panel. Still render the filters (empty) so the page doesn't
  break.
- The `public_router` for `/demo/*` must be included in `web/main.py`
  *before* the authenticated `router` if both share a prefix. In
  practice, `/demo/waiver` and `/waiver` don't share a prefix, so
  ordering is not critical here.

## Tech Lead Review

**Complexity: M**

Feasibility is high. Route shape is nearly identical to `overview.py` and all referenced
functions exist and are already battle-tested.

**Flags for the engineer:**

1. **`stat_columns` import path** — the ticket calls it without a module prefix. The function
   lives in `analysis.team_scores`, not `data/`. Add `from analysis.team_scores import stat_columns`
   to `web/routes/waiver.py`.

2. **`_STAT_FALLBACK_ABBREV` must be ported** — copy the dict from `pages/03_waiver_wire.py`
   lines 78–104 into `web/routes/waiver.py`. Build the merged abbrev dict once before calling
   `TemplateResponse`: `stat_abbrev = {**_STAT_FALLBACK_ABBREV, **{c["stat_name"]: c["abbreviation"] for c in raw_cats if c["is_enabled"]}}`. Do not pass the unmerged dicts.

3. **`is_enabled` filter** — `get_stat_categories()` returns Python bools for `is_enabled`
   (not strings). `if c["is_enabled"]` works as-is; no need to compare to `"1"`.

4. **Template directory** — `web/templates/waiver/` does not exist yet. Create it as part
   of this ticket; 019 depends on it.

5. **`get_user_hockey_leagues` call on every GET** — this makes one live Yahoo API call to
   resolve `selected_league_name`. It's a small call but not cached. Acceptable for v1;
   note it as a future candidate for session-level caching.

No dependencies are missing. 018 must ship before 019.

## Notes for QA
- Test 1: `GET /waiver` with selected league and matchups data → 200,
  HTML contains 6 position radio inputs with values All/C/LW/RW/D/G,
  a period radio with values "Season"/"Last 30 days", and one checkbox
  per stat column from the matchups fixture.
- Test 2: `GET /waiver` with NULL `league_key` → 302 to `/`.
- Test 3: `GET /waiver` without session cookie → 302 to `/auth/login`.
- Test 4: `GET /demo/waiver` (no session) → 200, HTML contains filter
  controls populated from demo data; `<form>` action points to
  `/demo/api/waiver/players`.
- Test 5: inspect HTML — the `<form>` element has `hx-post`,
  `hx-target="#waiver-table-container"`, and `hx-trigger="change"`.
- Test 6: the `<div id="waiver-table-container">` exists and contains
  the empty-state instructional text.
- Manual: confirm "Waiver" nav link appears in the header on all pages
  and routes to `/waiver`.
- Edge case: `get_matchups` returns None (mock it) → shell renders with
  an empty stat chips area and a notice; no 500.
