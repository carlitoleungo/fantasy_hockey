# 016 — League overview: head-to-head comparison view

## Summary
Second view on the league overview page. User picks two teams and a week
range; the page shows a category-by-category comparison of each team's
average stats, highlighting the winner per category and totalling a
win/loss/tie count at the bottom. Lives at `/overview/head-to-head` and
reuses the shell + fragment pattern established in ticket 015 — the team
and week-range selectors POST (or `hx-get`) to a fragment route that
re-renders only the comparison table. Adds no new conventions.

## Acceptance criteria
- [ ] `GET /overview/head-to-head` with a valid session and a selected
  `league_key` returns 200 HTML rendered from
  `web/templates/overview/head_to_head.html`. The page contains: two team
  selectors (dropdowns populated with the league's team names), a
  from-week / to-week selector (dropdowns populated from available weeks),
  and an initial comparison rendered for a sensible default pair (first
  two alphabetical teams) across all available weeks.
- [ ] `GET /overview/head-to-head/table?team_a=<name>&team_b=<name>&from_week=<n>&to_week=<n>`
  returns the HTML `_head_to_head_table.html` fragment: the
  category-by-category comparison and the tally row, without the page shell.
  The page's selectors target this fragment via `hx-get` / `hx-target`.
- [ ] The comparison table has columns `Category`, `<team_a name>`,
  `<team_b name>`, `Winner`. Cells showing the winning team's value are
  highlighted with `bg-green-100`; the losing team's value has no
  background; tied categories have `bg-gray-100` on both. The final
  `Winner` column shows the winner's team name (or `Tie`).
- [ ] Below the table, a tally row shows `{team_a}: X wins · {team_b}: Y
  wins · Z ties` — values from `analysis.matchup_sim.tally`.
- [ ] `GET /overview/head-to-head` without a selected league redirects to
  `/` (302); without a session cookie, redirects to `/auth/login` (302).
- [ ] The `base.html` header is unchanged — head-to-head is not a new
  top-level feature; users reach it from the Overview link (see note below
  on in-page navigation).
- [ ] Unit test: fixture DataFrame (3 teams × 3 weeks × 3 stats) rendered
  via the fragment route produces HTML with the correct winner per
  category and a tally row matching `matchup_sim.tally` output.

## Files likely affected
- `web/routes/overview.py` (extend — add two handlers alongside ticket 015's)
- `web/templates/overview/head_to_head.html` (new)
- `web/templates/overview/_head_to_head_table.html` (new)
- `web/templates/overview/index.html` (add an in-page link to `/overview/head-to-head`)

## Dependencies
- Requires 015 (weekly leaderboard view) — inherits its shell + fragment
  convention, its `rank_color` filter registration path, and the
  `_get_league_key` helper from `web/routes/overview.py`.
- Consumes `data.matchups.get_matchups`, `analysis.matchup_sim.simulate`,
  `analysis.matchup_sim.tally` — no changes to `data/` or `analysis/`.

## Notes for the engineer

**Decision references.** Same four decisions from `docs/decisions.md`
2026-04-19 apply. This ticket adds no new cross-cutting conventions; it
reuses everything 015 established:
- Shell + fragment template split → `head_to_head.html` shell + `_head_to_head_table.html` fragment
- Selectors use `hx-get` targeting the fragment route
- League context resolved via the shared `_get_league_key` helper
- `selected_league_name` resolved and passed in every shell `TemplateResponse`
  context (same pattern as ticket 015; fragment route omits it)
- Nav shell unchanged — head-to-head is reached from an in-page link

**Route handler shape.** Extend `web/routes/overview.py`:

```python
@router.get("/overview/head-to-head")
def head_to_head(...):
    league_key = _get_league_key(db, current_user.session_id)
    if not league_key:
        return RedirectResponse("/", status_code=302)
    session = make_session(current_user.access_token)
    leagues = get_user_hockey_leagues(session)
    selected_league_name = next(
        (lg["league_name"] for lg in leagues if lg["league_key"] == league_key), None
    )
    df = get_matchups(session, league_key)
    # Render shell with defaults: first two teams alphabetical, full week range.
    # Empty-state (df is None or < 2 teams) → render shell with message, no 500.
    # Always pass selected_league_name in the shell context.

@router.get("/overview/head-to-head/table")
def head_to_head_table(team_a: str, team_b: str, from_week: int, to_week: int, ...):
    # Fetch matchups, run simulate() and tally(), render _head_to_head_table.html.
```

**In-page link from the leaderboard.** Add a small link on
`web/templates/overview/index.html` (ticket 015's shell) pointing to
`/overview/head-to-head`, e.g. "Compare two teams →" — positioned near the
week selector or below the leaderboard table. Symmetrically, add a back
link on `head_to_head.html` pointing to `/overview`. Keep these visually
subdued; they are not main nav.

**Default selections when the shell first renders.**
- `team_a`, `team_b`: first two teams alphabetical from `df["team_name"].unique()`.
- `from_week`: `min(weeks)`; `to_week`: `max(weeks)`.
- If `df` has fewer than 2 teams (edge case, usually empty), render the
  shell with a `"Not enough team data yet"` message and no selectors.

**Winner cell highlighting.** `simulate()` returns rows with `category`,
`team_a`, `team_b`, `winner` (string: team_a name, team_b name, or `"Tie"`).
In the template:
```jinja
{% for row in sim.itertuples() %}
  <tr>
    <td>{{ row.category }}</td>
    <td class="{% if row.winner == team_a_name %}bg-green-100{% elif row.winner == 'Tie' %}bg-gray-100{% endif %}">
      {{ "%.2f" | format(row.team_a) }}
    </td>
    <td class="{% if row.winner == team_b_name %}bg-green-100{% elif row.winner == 'Tie' %}bg-gray-100{% endif %}">
      {{ "%.2f" | format(row.team_b) }}
    </td>
    <td>{{ row.winner }}</td>
  </tr>
{% endfor %}
```
Do **not** reuse the `rank_color` filter here — the coloring semantics are
different (winner-loser, not rank-within-column). Inline conditionals are
fine.

**Tally rendering.** `matchup_sim.tally(sim_df, team_a, team_b)` returns
`{team_a_name: int, team_b_name: int, "Tie": int}`. Render as one line
below the table. Include in the same `_head_to_head_table.html` fragment
so the full comparison re-renders atomically on selector changes.

**Gotchas**
- `simulate()` signature takes `from_week` / `to_week` as optional; always
  pass them explicitly from the query params so the fragment URL is
  self-describing and shareable (even though we've deferred path-based
  URLs — the *fragment* route takes query params and that's fine; see
  decision "League context" in `docs/decisions.md`).
- Team name comparisons in `simulate()` are exact string matches. The
  dropdowns must submit the exact `team_name` values from the DataFrame —
  no trimming, no case-folding.
- `LOWER_IS_BETTER` handling inside `simulate()` is already correct — do
  not reimplement it in the route.
- Week range validation: if `from_week > to_week`, `simulate()` returns
  NaN averages. Either swap them in the route handler before calling, or
  disable the "submit" until the range is valid. Swap-then-call is simpler
  for v1.
- `get_matchups` returns `None` or empty if the season hasn't started —
  handle identically to ticket 015's empty-state branch.

## Notes for QA
- Test 1: `GET /overview/head-to-head` with a selected league and matchups
  data → 200, HTML contains two team dropdowns with every team_name,
  from/to week dropdowns, and an initial comparison table.
- Test 2: `GET /overview/head-to-head/table?team_a=...&team_b=...&from_week=1&to_week=3`
  → HTML fragment (no `<html>`) with one row per stat category, a `Winner`
  column, and a tally line.
- Test 3: inspect `bg-green-100` appears on the correct winner-side cells
  for a known fixture; `bg-gray-100` appears on ties.
- Test 4: `GET /overview/head-to-head` with NULL `league_key` → 302 to `/`.
- Test 5: `GET /overview/head-to-head` with no session → 302 to
  `/auth/login`.
- Edge case: `team_a == team_b` (user picks the same team twice) — tally
  returns 0 wins for each side and all ties. Not a crash, but looks odd;
  acceptable for v1.
- Edge case: `from_week > to_week` — route swaps them before calling
  simulate; comparison still renders.
- Edge case: team name round-tripping — `simulate()` uses exact string
  equality on team names. Test with at least one team name containing a
  space and, if any exist in the fixture, a special character (apostrophe,
  ampersand, etc.). Confirm the value submitted from the `<select>` option
  reaches the route handler unmodified and matches the DataFrame string. A
  mismatch produces silently empty results, not an error.
- Manual: change team dropdowns in the browser → table updates without a
  full page reload.
- Manual: confirm in-page "Compare two teams →" link on the leaderboard
  page and the back link on the head-to-head page both work.
