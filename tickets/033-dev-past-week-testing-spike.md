# 033 — Scoping brief / spike: develop & test week-keyed pages against a specific past week

> **Status:** Scoping brief + feasibility spike, **not** a ready implementation ticket.
> Hand this to the Tech Lead *before* the PM finalises any implementation ticket. It
> touches two items on WORKFLOW.md's architectural-surface escalation list (parquet cache
> layer; Yahoo API client conventions), so the PM must not finalise a real ticket until
> the Tech Lead has resolved the open questions below. Output of the spike is: (a) a
> feasibility verdict, (b) a chosen option (or "not worth it"), and (c) a DECISIONS.md
> entry if the call is significant. The PM then scopes the actual implementation ticket(s).

## Status
blocked  <!-- pending Tech Lead consult; cannot become `ready` until the open questions are resolved -->

## Type
feature  <!-- spike/exploratory; may resolve into a refactor or "wontfix" -->

## Why this brief exists

We develop during the NHL off-season, so there is **no live Yahoo data** for week-keyed
features — matchups, weekly scoreboards, `type=lastmonth` rates, and remaining-games
schedules all come back empty or stale (see `docs/LEARNINGS.md` "Off-season → no live
data"). This just bit ticket 029 (Week Projection shell): neither QA nor a live visual
test could exercise it against real matchup/projection data — everything only rendered
the empty/placeholder state. The same will block meaningful testing of tickets 030
(projection matchup fragment) and 031 (demo parity), and any future week-keyed feature.

Demo mode (`data/demo.py`, snapshotted at `snapshot_week=14`) already gives us a
**visual** check of the rendered page, and ticket 031 wires `/demo/projection` to it. But
demo mode does **not** exercise the *authenticated* live-fetch code paths in
`data/client.py` / `data/cache.py` / `data/scoreboard.py` — the exact paths that were
untestable for 029. The gap this spike explores: **can we point the live-fetch paths at a
specific past week so we can develop and QA them with real data, and if so, how — without
straining the live-snapshot-by-default design?** The owner is explicitly unsure this is
feasible; feasibility exploration is in scope.

## Context the Tech Lead should re-read before deciding

- `data/client.py:73,145` — `current_week` is a single integer read live from
  `league["current_week"]`. This is the one value that pins "which week is now."
- `data/scoreboard.py:9` — `get_current_matchup(session, league_key, week)` **already
  takes an explicit `week` param**. Scoreboard is week-parameterizable today.
- `data/client.py` `get_all_teams_week_stats(session, league_key, week, stat_categories)`
  — also already takes a `week` param.
- `data/matchups.py:16-46` — delta-fetch always appends `current_week` to
  `weeks_to_fetch` and always re-fetches it (`docs/DECISIONS.md` 2026-05-31 "current_week
  always re-fetched"). A past-week override must not fight this guard.
- `data/players.py` — `type=lastmonth` returns the last 30 days **as of now** and cannot
  be asked for a historical 30-day window (`docs/DECISIONS.md` 2026-03-23). GAA is
  recomputed for lastmonth inside `players.py`.
- `data/schedule.py` `get_remaining_games(...)` — counts NHL games **from today
  forward**. For a past week, "remaining" games is zero, so projection math degenerates.
- Available (waiver) players are **never cached and always fetched live**, and Yahoo only
  serves the *current* available pool — a past week's waiver pool is not retrievable at
  all. (So this spike helps Projection, not the waiver available-pool.)
- `data/demo.py:50,116,130` — `get_current_week()`, `get_projection_context()`,
  `get_projection_pair_data()`: a full week-14 snapshot already exists as fixture data.
- `data/cache.py` — parquet keyed by `(league_key)` with a `week` column (matchups) and
  by `(league_key, position, stat)` (player pool); `CACHE_DIR` env var, layout under
  `/data/cache/`.

## The feasibility crux (why this is a spike, not a ticket)

Overriding "which week is now" is more than swapping one integer. Several live-fetch paths
carry **"as of today" assumptions** that a `week` override alone does not satisfy:

1. `type=lastmonth` gives current-30-day rates only — during off-season these are empty,
   and there is no API to request a historical window. Projections would use *today's*
   (empty) rates against a *past* week.
2. `get_remaining_games` counts from today; for a past week it returns ~0, collapsing the
   projection to "0 games left."

So the honest question isn't just "can we set `current_week` to a past value" — it's
"which of the live-fetch inputs can actually be sourced for a past week, and does the
subset that can't (lastmonth rates, remaining games) make the exercise pointless unless we
*also* seed those from a snapshot?" The Tech Lead needs to rule on this before we commit.

## Options (each: implementation cost · what it locks in · good if)

### Option A — `week` / dev-mode override threaded through the week-keyed fetches
Introduce a dev-only override (env var like `DEV_WEEK_OVERRIDE`, or a query param gated to
non-production) that substitutes the live `current_week`. Downstream fetches
(`scoreboard`, `teams/stats`) already accept a `week`, so they follow; `matchups` delta
logic and the lastmonth/remaining-games "as of today" paths would need explicit handling.
- **Implementation cost:** **M** — small where the fetch already takes `week`; larger for
  the lastmonth/remaining-games assumptions and for gating the override out of production.
- **Locks in:** a new config knob and a code path that reads "current week" from somewhere
  other than Yahoo — touches `data/client.py` conventions (architectural surface). Every
  future week-keyed fetch must respect the override.
- **Good if:** we want to exercise the *real* authenticated fetch/parse/cache code against
  live-but-past Yahoo data, and the Tech Lead is comfortable adding a client-layer override
  seam. Still limited: lastmonth rates for a past week are unavailable from the API.

### Option B — seed the parquet cache with a captured past-week snapshot
Capture a real past-week response set once (matchups, teams/stats, rosters) and write it
into `CACHE_DIR` so the live paths read from cache instead of hitting the (empty) API.
- **Implementation cost:** **S–M** — a capture script + fixtures; no client override seam
  if the cache read path is hit before the API. But the 2026-05-31 always-re-fetch guard
  for `current_week` means seeded current-week data gets clobbered by a live (empty) fetch
  unless the guard is worked around.
- **Locks in:** a second source of truth living in the cache dir; risk of stale/fake data
  leaking into a real session; still no answer for lastmonth (never cached that way) or the
  always-live available pool.
- **Good if:** we mainly need the *rendering + compute* paths fed with realistic data and
  can tolerate not exercising the live API round-trip. Overlaps heavily with demo mode.

### Option C — reuse the demo-mode snapshot dataset as a dev fixture for authenticated routes
Let authenticated week-keyed routes optionally source from `data/demo.py`'s existing
week-14 snapshot (behind a dev flag), reusing fixtures we already maintain.
- **Implementation cost:** **S** — smallest; demo hooks already return the right shapes
  (`get_projection_context`, `get_projection_pair_data`).
- **Locks in:** blurs the authenticated/demo boundary the team has deliberately kept clean
  (demo-parity is its own architectural surface); a dev flag that swaps data sources in the
  authenticated path is easy to leave on by accident.
- **Good if:** the goal is purely "see the authenticated page render with plausible
  numbers during off-season" and we accept it's the same data demo mode already shows — i.e.
  it does **not** buy us real live-fetch coverage beyond what demo already gives.

## Open questions the Tech Lead consult must resolve
- **Is the exercise worth it at all,** given lastmonth rates and remaining-games cannot be
  sourced for a past week from the live API? Or does that push us to Option B/C (seed those
  too), at which point "test against live past-week data" collapses back into "richer demo
  fixtures"?
- **Where should the override live** — env var, query param gated to non-production, or a
  config knob — and how do we guarantee it can never be active in production? (New config
  knob is itself an escalation-list surface.)
- **Does a past-week override conflict** with the 2026-05-31 "current_week always
  re-fetched" delta-fetch guard in `matchups.py`? If we pin a past week, is that week now
  "current" for the guard, or do we bypass delta logic entirely in dev?
- **Cache correctness:** if we seed `CACHE_DIR` (Option B) or override the week (Option A),
  how do we prevent fake/stale past-week data from leaking into a genuine authenticated
  session? Does seeded data need an isolated cache namespace?
- **Boundary policy (Option C):** is sourcing authenticated routes from `data/demo.py`
  ever acceptable, or does the demo-parity architectural boundary forbid it outright?
- **Scope of the eventual real ticket(s):** does the chosen option stay within the "≤2–3
  files, one focused session" rule, or does it need splitting (e.g. capture script vs.
  override seam)?

## Out of scope for this spike
- Any production behaviour change — the override/seed must be dev-only.
- The always-live waiver available-players pool (Yahoo only serves the current pool; a past
  week is unrecoverable — not solvable here).
- Implementing the chosen option. This brief produces a decision + follow-up ticket(s),
  not code.

## Dependencies
- Tech Lead consult required before this can become a `ready` implementation ticket.
- Informational overlap with ticket 031 (`/demo/projection` parity) — the Tech Lead should
  weigh how much of this need 031's demo path already covers.
