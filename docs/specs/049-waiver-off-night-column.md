> Written under the old ticket workflow (pre-2026-11-04). References to `tickets/`, `docs/ROADMAP.md`, `docs/backlog.md`, `docs/improvements.md` or persona roles point to files now removed; read them with `git show 409b7ab:<path>`. "Touches" is guidance, not a hard limit.

# 049 — Waiver wire: show off-night games per player

## Status
ready

## Type
feature

## Milestone
none

## Touches
- web/routes/waiver.py
- web/templates/waiver/_table.html
- tests/test_waiver.py

## Why
The waiver table already tells a manager how many games a player has left this week (the GR
column), but not how many of those land on nights when most of the league is idle. Those are the
nights he has empty active slots, so they are the games most likely to actually be played rather
than benched. Tickets 047 and 048 produced the slate and the off-night rule; this ticket surfaces
the result so the manager can see it while choosing a pickup.

## Acceptance criteria
- [ ] With period "Last 30 days", `POST /waiver/players` returns 200 and the table renders an
      "ON" column header (titled/tooltipped "games on off-nights this week") immediately after
      the existing "GR" column, with a per-player integer count.
- [ ] The value for a player is the number of his team's remaining games this week that fall on an
      off-night, computed via `analysis.off_nights` over the same `week_start`..`week_end` the
      route already resolves for GR, with the player's Yahoo `team_abbr` mapped through
      `data.schedule.to_nhl_abbr`.
- [ ] With period "Season", no "ON" column is rendered (matching how GR behaves today), and the
      page still returns 200.
- [ ] `POST /demo/waiver/players` with period "Last 30 days" returns 200 and renders the same "ON"
      column, populated from `data.demo.load_nightly_slate()`.
- [ ] When the slate is unavailable (the NHL fetch raises, or returns an empty slate), every row's
      ON cell renders the existing em-dash placeholder and the page still returns 200 — the same
      failure posture the GR column already has.

## Out of scope
- Sorting, filtering, or ranking by off-night count. Display only — see ticket 048's Out of scope
  and the two `docs/backlog.md` ranking entries that own that question.
- Any roster or "could I actually start him" conflict check. That is Part C of the backlog entry
  and is **not scoped** — it has two unanswered owner questions and needs a Tech Lead consult.
- Caching the NHL schedule (deferred to M2 by an active decision — see Notes).
- Restyling the waiver table. The M1 UI re-design is separate, per-page work.
- The Season-period branch generally. It has no games-remaining data today and gains none here.

## Notes for the Engineer
- **Read first:** `web/routes/waiver.py` around lines 200–300 — the entire "Last 30 days" branch,
  including the `try/except` that fetches `get_matchups` → `get_current_matchup` →
  `week_start`/`week_end` → `get_remaining_games`, and the `games_remaining_map` mapping onto
  `ranked_df` just below `rank_players`. `web/templates/waiver/_table.html` lines ~103–163 is the
  header/cell block; the GR cell at ~line 146 is the pattern to copy verbatim for ON.
- **Reuse the dates that are already resolved.** `from_date` / `to_date` are computed inside that
  existing try-block for GR. Fetch the slate once in the same block — do not open a second
  try-block, and do not call the NHL API twice (047 makes `get_remaining_games` and
  `get_nightly_slate` share one fetch path; keep both calls inside the one guarded section).
- **Demo branch:** the demo path takes `games_remaining_map` from `demo_module.get_games_remaining()`
  at `web/routes/waiver.py:~208`; take the slate from `demo_module.load_nightly_slate()` in the
  same place, and let both paths converge on one off-night computation below the assembly seam.
- **DECISIONS.md entries this ticket must conform to** (verified active in `docs/DECISIONS.md`;
  none are the superseded copies in `docs/archive/decisions-superseded.md`):
  - **2026-07-03 "Web routes: demo and live handlers share a single compute/render helper"** — the
    live and demo waiver handlers are *pre-pattern* (that entry says so explicitly and permits
    leaving them as-is). Do **not** refactor the waiver route to the `projection._render_matchup`
    shape in this ticket; that would blow the diff well past scope. Do keep the new off-night
    computation itself on a single shared code path so live and demo cannot drift.
  - **2026-05-30 "Web routes: demo route pairing policy"** — the demo counterpart ships in this
    ticket, not deferred.
  - **2026-05-30 "Feature pages: HTMX fragment pattern with shell + fragment template split"** —
    this is the live entry (it supersedes the same-titled 2026-04-19 one); `_table.html` is the
    fragment, and the new column goes there, not in the shell.
  - **2026-05-30 "Waiver and projection routes: per-stat bulk fetch, never per-player"** — the
    off-night count is derived per row from one already-fetched slate. No per-player lookup that
    triggers I/O.
  - **2026-07-23 "Cache: league-independent data gets a shared tier at M2; M1 only preserves the
    affordance"** — the NHL schedule stays uncached. Do not add a cache read/write on this path.
  - **2026-04-19 "Feature pages: rank → Tailwind class mapping lives in templates, not analysis"** —
    if you colour-code the ON column at all, the class mapping goes in the template.
- **LEARNINGS.md gotchas that apply:** "Tests must patch the importing module's namespace" — the
  existing waiver tests patch `web.routes.waiver.get_remaining_games`
  (`tests/test_waiver.py:460, 631`); a new slate call imported into the same namespace needs the
  same treatment. "Off-season → no live data; week-keyed feature pages only show empty states" —
  the empty-slate acceptance criterion above is the off-season path, so test it rather than
  assuming it cannot happen.
- **Open `docs/improvements.md` items on files in `Touches`:**
  - `tests/test_waiver.py` lines 168, 198, 214, 236, 271, 313, 345, 400, 464, 497, 529, 565, 601,
    635 — "Stale `position` form field in 14 `tests/test_waiver.py` call sites", **Type: quality**.
    Your input #6 obliges you to sweep this since you are modifying the file: replace the stale
    `"position": "All"` key with `"positions": ["All"]` (or delete it) at all 14 sites. It is a
    mechanical 14-line change and is **forecast here on purpose** — it will be in the diff.
    Close the item out per your DoD (move it to `docs/archive/improvements-closed.md`).
  - `web/routes/waiver.py` — the "League settings and stat categories re-fetched from Yahoo on
    every request" item lists `data/client.py`, `data/cache.py`, `data/matchups.py`,
    `web/routes/waiver.py` as affected. It is **out of scope**: it is an M2 rate-limit item, it
    touches `data/client.py` (an architectural surface needing its own Tech Lead consult), and
    `docs/ROADMAP.md` says explicitly not to fold it into other work. Mention it in your done
    note; do not fix it.
  - `web/templates/waiver/_table.html` — none.

## Verification
- `.venv/bin/python -m pytest tests/` — full suite green.
- Live walk: start uvicorn, sign in, open `/waiver`, choose "Last 30 days", submit. Confirm the ON
  column appears after GR, that ON ≤ GR for every row, and that a player whose team plays only on
  busy nights shows 0. Switch to "Season" and confirm the ON column disappears and the page still
  renders.
- Demo-mode walk (required — this ticket touches a data path): open `/demo/waiver` unauthenticated,
  select "Last 30 days", submit, and confirm the ON column renders with the same shape and that the
  values are consistent with the demo GR values.
- Failure posture: patch the slate call to raise, re-submit, and confirm the page still returns 200
  with em-dashes in the ON column rather than a 500.
- "Done" looks like: a manager scanning the Last-30-days waiver table can see, per player, how many
  of this week's remaining games land on off-nights, in both the authenticated and demo pages.

## Dependencies
- Tickets 047 and 048 must complete first, in that order.
