# 015 — League overview: weekly leaderboard view

## Summary
First feature page migrated from the Streamlit prototype to the new stack.
Renders a weekly leaderboard table for a selected week: one row per team,
one column per scoring stat, with per-cell color coding (best/worst per
column) and a final `avg_rank` column. A week selector at the top uses the
HTMX fragment pattern — changing weeks swaps only the table, not the whole
page. This ticket establishes two first-time conventions the rest of the
migration will inherit: (a) the shell + fragment template split, and (b) the
`rank_color` Jinja filter for stat-cell coloring. Also adds the first
feature link ("Overview") to the nav shell from ticket 014.

## Acceptance criteria
- [ ] `GET /overview` with a valid session and a selected `league_key`
  returns 200 HTML rendered from `web/templates/overview/index.html`. The
  page contains a week-selector control and the leaderboard table for the
  latest available week.
- [ ] `GET /overview/table?week=<n>` (fragment route) returns the HTML
  `_table.html` fragment — the leaderboard table for the requested week,
  without the page shell. The week selector in the shell targets this
  endpoint via `hx-get` / `hx-target`.
- [ ] The leaderboard table has columns `team_name`, every stat column (in
  the order returned by `analysis/team_scores.stat_columns`), and
  `avg_rank`. Rows are sorted by `avg_rank` ascending (best team first).
- [ ] Each stat cell has a Tailwind background class derived from its rank
  within that column: rank 1 → `bg-green-100`; rank == team_count →
  `bg-red-100`; otherwise no background class. `team_name` and `avg_rank`
  cells are not color-coded.
- [ ] `GET /overview` without a selected league redirects to `/` (302).
- [ ] `GET /overview` without a valid session cookie redirects to
  `/auth/login` (302) via the existing `RequiresLogin` mechanism.
- [ ] The `base.html` header gains an "Overview" link (href `/overview`)
  between the app-name link and the logout link, visually consistent with
  the existing header elements.
- [ ] Unit test: a test fixture DataFrame (3 teams × 2 weeks × 3 stats)
  rendered via the fragment route produces HTML containing the expected
  team names, stat values, and at least one `bg-green-100` and one
  `bg-red-100` class.

## Files likely affected
- `web/routes/overview.py` (new)
- `web/templates/overview/index.html` (new)
- `web/templates/overview/_table.html` (new)
- `web/templates/base.html` (add "Overview" link)
- `web/templates.py` (register `rank_color` Jinja filter)
- `web/main.py` (include the new router)

## Dependencies
- Requires 014 (nav shell in `base.html`).
- Consumes `data.matchups.get_matchups`, `analysis.team_scores.weekly_scores_ranked`,
  `analysis.team_scores.stat_columns`, `analysis.team_scores.LOWER_IS_BETTER`
  — no changes required to `data/` or `analysis/`.

## Notes for the engineer

**Decision references (all logged in `docs/decisions.md` 2026-04-19):**
1. **HTMX fragment pattern.** The feature lives at `web/templates/overview/`
   with `index.html` (shell) and `_table.html` (fragment). The shell's week
   selector uses `hx-get="/overview/table"` with an `hx-target` pointing at
   the table's wrapping element. This is the first page using the
   convention — waiver wire and projection will follow the same structure.
2. **Rank → class mapping in the template.** `analysis/` stays
   framework-free; the mapping lives as a Jinja filter (`rank_color`) that
   receives `(rank, team_count)` and returns a Tailwind class string.
   Register it in `web/templates.py` (where `Jinja2Templates` is
   instantiated), not in a `__init__.py`.
3. **Session-state league context.** Look up `league_key` from the session
   row (same pattern as `web/routes/home.py` lines 28–31). If `league_key`
   is NULL, redirect 302 to `/` — do **not** render an error.
4. **Nav shell.** Append the "Overview" link inside the header in
   `base.html`. Do not replace or restructure the header.

**`_get_league_key` helper.** Define this as a named module-level private
function — ticket 016 imports it from this module:

```python
def _get_league_key(db, session_id: str) -> str | None:
    row = db.execute(
        "SELECT league_key FROM user_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["league_key"] if row and row["league_key"] else None
```

**`selected_league_name` for the shared header.** The base template shows
the selected league name; every feature page must pass it in the template
context or the header league label will disappear on `/overview`. Fetch
leagues and resolve the name using the helper from `home.py`:

```python
from data.leagues import get_user_hockey_leagues

leagues = get_user_hockey_leagues(session)
selected_league_name = next(
    (lg["league_name"] for lg in leagues if lg["league_key"] == league_key),
    None,
)
```

Pass `"selected_league_name": selected_league_name` in every
`TemplateResponse` context in this file (both the shell and empty-state
branches). The fragment route (`/overview/table`) returns a bare `<table>`
and should **not** include it.

**Route handler shape:**

```python
@router.get("/overview")
def overview(request, current_user=Depends(require_user), db=Depends(db_dep)):
    league_key = _get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)
    session = make_session(current_user.access_token)
    leagues = get_user_hockey_leagues(session)
    selected_league_name = next(
        (lg["league_name"] for lg in leagues if lg["league_key"] == league_key), None
    )
    df = get_matchups(session, league_key)
    if df is None or df.empty:
        # Season hasn't started; render the shell with an empty-state message.
        return templates.TemplateResponse(
            request, "overview/index.html",
            {
                "weeks": [], "selected_week": None, "ranked": None, "stat_cols": [],
                "selected_league_name": selected_league_name,
            },
        )
    weeks = sorted(df["week"].unique().tolist())
    selected_week = weeks[-1]
    ranked = weekly_scores_ranked(df, selected_week)
    cell_ranks = _compute_cell_ranks(ranked, stat_columns(df))
    return templates.TemplateResponse(
        request, "overview/index.html",
        {
            "weeks": weeks, "selected_week": selected_week,
            "ranked": ranked, "cell_ranks": cell_ranks,
            "stat_cols": stat_columns(df),
            "team_count": len(ranked),
            "selected_league_name": selected_league_name,
        },
    )

@router.get("/overview/table")
def overview_table(week: int, request, current_user=..., db=...):
    # Same data fetch; render overview/_table.html instead of index.html.
```

**Per-cell rank computation** (integration glue in the route, 4 lines of
pandas — do **not** add this to `analysis/team_scores.py`; the existing
`weekly_scores_ranked` computes these internally but only returns the
averaged `avg_rank`, and a route-layer re-computation using the module's
existing primitives is intentional to preserve the single-responsibility
shape of `weekly_scores_ranked`):

```python
def _compute_cell_ranks(ranked_df, stat_cols):
    import pandas as pd
    from analysis.team_scores import LOWER_IS_BETTER
    ranks = pd.DataFrame(index=ranked_df.index)
    for col in stat_cols:
        ranks[col] = ranked_df[col].rank(
            method="min", ascending=(col in LOWER_IS_BETTER),
        )
    return ranks
```

Pass `cell_ranks` as a DataFrame-like mapping into the template, indexed
the same as `ranked` so `{% for row in ranked.itertuples() %}` and a lookup
by `(row.Index, col)` stays simple.

**`rank_color` Jinja filter.** Register in `web/templates/__init__.py`
(where `templates = Jinja2Templates(...)` lives). Implementation:

```python
def rank_color(rank, team_count):
    if rank is None or team_count is None:
        return ""
    if rank == 1:
        return "bg-green-100"
    if rank == team_count:
        return "bg-red-100"
    return ""

templates.env.filters["rank_color"] = rank_color
```

Template usage inside `_table.html`:
```jinja
<td class="px-2 py-1 {{ cell_ranks[col][row.Index] | rank_color(team_count) }}">
  {{ row[col] }}
</td>
```

**Gotchas**
- `weekly_scores_ranked` returns the `avg_rank` column alongside raw stats.
  Do **not** pass `"avg_rank"` into `stat_cols` for cell coloring — colour
  only stat columns. Render `avg_rank` as its own final column with no
  background class.
- Ties on method='min' can leave the "worst" rank at less than
  `team_count` (e.g. two teams tied for second-worst in a 12-team league
  produce ranks 11, 11 with no 12). Those tied cells won't get `bg-red-100`.
  Acceptable for v1; document in `docs/improvements.md` if it looks off in QA.
- `get_matchups` returns `None` or empty if the season hasn't started.
  Render the shell with an empty-state message — do not 500.
- The "Overview" header link must be inserted in `base.html` *between* the
  app-name link and the logout link so ordering stays Overview → (future
  Waiver) → (future Projection) → Logout.

**Fetch stat_categories?** No. `weekly_scores_ranked` defaults to the
module-level `LOWER_IS_BETTER` set, which covers goalie GA/GAA. Matches
prototype behaviour. A future ticket can switch to per-league
`lower_is_better_from_categories(...)` if needed.

## Notes for QA
- Use fixtures under `tests/fixtures/` modelled on the existing matchups
  shape (see `data/matchups.py` docstring). A 3-team × 2-week × 3-stat
  DataFrame is enough to exercise ranking + coloring.
- Test 1: `GET /overview` with a selected league and matchups data returns
  200 and HTML containing all team names, all stat columns, and `avg_rank`.
- Test 2: `GET /overview/table?week=1` returns HTML that is *not* wrapped
  in `<html>` (confirm it's a fragment, not the shell).
- Test 3: inspect rendered HTML for `bg-green-100` and `bg-red-100` classes
  in expected cell positions for a known fixture.
- Test 4: `GET /overview` with NULL `league_key` in the session row → 302
  to `/`.
- Test 5: `GET /overview` with no session cookie → 302 to `/auth/login`.
- Edge case: mock `get_matchups` to return `None` — page renders the shell
  with the empty-state message, no 500.
- Manual: change the week selector in the browser → table updates without a
  full page reload (confirm via devtools network tab: XHR, not a navigation).
- Manual: confirm the "Overview" link appears in the header on every page
  (home, overview, error) and that the app-name / logout links still work.
