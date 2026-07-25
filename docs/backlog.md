# Backlog — Fantasy Hockey Waiver Wire

Features and ideas deferred from active development. Each entry has enough context
to pick up without re-explaining the original idea.

---

## Week Projection Page — SCOPED 2026-07-02 → tickets 028–031

**Original request:** Show projected stats for the current week based on games remaining
and recent player performance.
**Resolution:** The data/analysis/demo layers turned out to be already built and
framework-free (`analysis/projection.py`, `client.get_settings_and_categories` /
`get_all_teams_week_stats`, `roster.get_team_roster`, `players.get_players_lastmonth_stats`,
`schedule.get_remaining_games`, and the demo hooks below). No data-layer ticket was
needed — the migration is route+template only, scoped as tickets 028 (common.py prereq),
029 (shell), 030 (matchup fragment), 031 (demo parity). See `docs/ROADMAP.md`.
**Milestone:** none (shipped — historical record)
**Blocked by:** nothing

---

## Trade Analysis

**Original request:** Evaluate proposed trades — compare what you give up vs. what you gain
across stat categories.
**What was included:** Nothing — explicitly out of scope for the prototype per CLAUDE.md.
**What was deferred:** Entire feature.
**Context for later:** The `analysis/matchup_sim.py` head-to-head simulation logic (comparing
two sets of stat averages category by category) is a reasonable starting point for trade
analysis. The core question is: "how does my team's average rank change if I swap player A
for player B?" That's a delta on `analysis/team_scores.avg_ranks()` before and after the
hypothetical roster change.
**Milestone:** none
**Blocked by:** nothing
**Estimated complexity:** Large

---

## Migration: Per-user cache storage — DROPPED 2026-07-23 (Tech Lead consult)

**Resolution:** Ruled out on the merits. See `docs/DECISIONS.md` "Cache: stays
league-keyed; write safety comes from atomic rename + in-process locking, not per-user
keying" (2026-07-23). An audit of every cache call site found the three cached data types
(`matchups`, `ww_season__*` pools, `ww_lastmonth`) are all league-scoped and contain no
user-private data. The premise below — "must be per-user since multiple users will share
one deployment" — was wrong: per-user keys would multiply Yahoo API calls and disk usage
by the number of managers per league while leaving the actual concurrency defect
(non-atomic writes, unguarded read-modify-write) unfixed. Do not scope this.
**Milestone:** none (dropped — the concurrency fix it was conflated with is scoped as ticket 037)
**Blocked by:** nothing

The original entry is preserved below for context only.

---

**Original request:** Migrate away from Streamlit as part of the public app rebuild.
**What was included:** Tech Lead ticket (001) will specify the storage backend. ARCHITECTURE.md will define where cached data lives.
**What was deferred:** Implementation — replacing `.cache/{league_key}/` parquet files with the chosen storage backend (object storage, DB blob columns, etc.).
**Context for later:** The cache layer is in `data/cache.py`. Key functions to port: `read`, `write`, `append`, `last_updated`, `is_stale`, `write_player_pool`, `upsert_lastmonth_cache`. The new implementation must be per-user (keyed by user ID + league key) since multiple users will share one deployment. The parquet file format can likely be preserved — just the storage location changes.
**Estimated complexity:** Medium (one data ticket)

---

## Migration: Week projection page — SCOPED 2026-07-02 → tickets 028–031

**Original request:** Rebuild the Streamlit week projection page (`pages/04_week_projection.py`) in the new framework.
**Resolution:** Scoped into tickets 028–031 (see the "Week Projection Page" entry above and `docs/ROADMAP.md`). This was a duplicate of that entry; both are now resolved.
**Milestone:** none (shipped — historical record)
**Blocked by:** nothing

---

## Deployment configuration

**Original request:** Deploy the rebuilt app publicly.
**What was included:** Nothing yet. Tech Lead ticket (001) will name the deployment target.
**What was deferred:** Dockerfile, CI/CD pipeline, environment variable configuration, and production secrets management.
**Milestone:** m1
**Blocked by:** nothing
**Superseded (2026-07-25):** The M1 slice of this is now scoped as **ticket 039** (`fly.toml`
single pinned machine + 1 GB volume + `.dockerignore`), per the Tech Lead consult 2026-07-23
(DECISIONS "Deployment: M1 shape"). The `Dockerfile` and `.env.example` already exist; CI is
explicitly not an M1 requirement. What remains here beyond ticket 039 is post-M1 hygiene (CI,
richer secrets management) — revive that residue at M2.
**Context for later:** Current app has no containerisation. The new stack will need at minimum a `Dockerfile`, a `.env.example`, and CI steps for running `pytest tests/`. The chosen deployment platform (from ARCHITECTURE.md) will determine what else is needed.
**Estimated complexity:** Medium

---

## Streamlit Community Cloud decommissioning

**Original request:** Identified as a go-live step after scoped tickets 001–005.
**What was included:** Nothing.
**What was deferred:** The final cutover: stop the SC deployment, update or redirect any existing links, confirm the new Fly.io app is the canonical URL.
**Milestone:** m1
**Blocked by:** ticket 039
**Context for later:** This is an M1 go-live step and an **owner action, not a ticket** (a
dashboard operation, no code change) — recorded under "M1 launch steps" in `docs/ROADMAP.md`.
It cannot start until the Fly app is live and validated, which requires ticket 039's `fly.toml`
plus the owner-run `fly deploy`. SC watches the `main` branch. The simplest decommission is disconnecting the app in the SC dashboard. If there are external links to the SC URL, a redirect (either in `fly.toml` or via DNS) is worth setting up. This is the last step — do it only after the new app is live and validated.
**Estimated complexity:** Small

---

## Waiver Wire: Multi-position filtering — SCOPED 2026-07-02 → ticket 032

**Original request:** Allow selecting multiple positions simultaneously on the waiver wire
page (e.g. C + LW to find dual-eligible forwards).
**Resolution:** Scoped as a single UI-layer ticket (032). On investigation the change is
smaller than this entry originally assumed:
- **No cache-key decision needed.** `data/cache.py` already keys the player pool by
  `(league_key, position, stat)` (see `read_player_pool` / `write_player_pool` /
  `is_player_pool_stale`). Multi-select just loops the existing per-position fetch over
  each selected position and unions the pools — no new cache layout, no `data/cache.py`
  change.
- **No `analysis/` change needed.** `filter_by_position(df, position_group)` stays
  single-position; the route calls it per selected position and unions the results (or
  the API per-position fetch already narrows the pool). Keeps the change to route +
  template only.
- **Per-position API fetch is load-bearing.** `fetch_season_pool` returns only the
  top-25 per stat sort, so an "All" pool crowds out sparse positions (D, G). The route
  must fetch each selected position's pool separately — do NOT collapse to one "All"
  fetch. See the comment in `pages/03_waiver_wire.py` ~line 247 (archive) for the
  original rationale.
**Correction to the original premise:** The Streamlit prototype
(`pages/03_waiver_wire.py`, archive) was ALSO single-select (pill buttons, one
`ww_position` value) — multi-select is net-new UX, not a port of prior behaviour.
**Milestone:** none (shipped — historical record)
**Blocked by:** nothing
**Estimated complexity:** Small–Medium (2 files: `web/routes/waiver.py`,
`web/templates/waiver/index.html`).

---

## Migration: Login page

**Original request:** Rebuild the login/landing experience in the new framework.
**What was included:** `/auth/login` redirects immediately to Yahoo OAuth — there is no dedicated login page, just a nav link that kicks off the OAuth flow.
**What was deferred:** A proper login landing page (e.g. a page at `/login` or `/` for unauthenticated users that explains the app, offers a "Sign in with Yahoo" button, and links to the demo mode).
**Context for later:** The current entry point is `GET /auth/login` in `web/routes/auth.py` which immediately generates an OAuth URL and redirects. The home route (`/`) serves the league-picker to authenticated users; unauthenticated visits fall through to the login redirect. A dedicated login page would intercept unauthenticated `/` visits and render a landing screen before the OAuth round-trip begins. This is also the natural place to surface the demo mode entry point prominently.
**Milestone:** none
**Blocked by:** nothing
**Milestone note (2026-07-25):** leans **m2** if anything — it is stranger-facing (a landing
page that explains the app and surfaces the demo entry point, which is the M2 "find + evaluate
via demo without signing in" path), not required for M1's authenticated journey. Left `none`
because it is not on the critical path for either milestone: M1 friends already sign in via the
existing `/auth/login` redirect + the ticket-023 home CTA, and M2's demo discovery is served by
the smaller "Try the demo" home-link follow-up. Promote to m2 only if the owner wants a proper
landing page as part of the stranger-evaluation experience.
**Estimated complexity:** Small (UI ticket; no new data layer work)

---

## Past-week real-fixture capture + parse/cache tests — DEFERRED 2026-07-03 (from spike 033)

**Original request:** Follow-up to the ticket 033 spike resolution (DECISIONS.md 2026-07-03
"Dev/test: no runtime past-week override; use captured fixtures + demo mode instead"):
capture a real past-week raw Yahoo response set into `tests/fixtures/` once, then add tests
exercising the authenticated fetch/parse/cache paths that demo mode bypasses
(`data/client.py`, `data/cache.py`, `data/scoreboard.py`).
**What was included:** Nothing yet — deferred, not scoped into a ticket.
**What was deferred:** The whole capture + tests effort.
**Why deferred (PM judgment, 2026-07-03):** The named parse/cache/orchestration paths are
*already* comprehensively covered by fixture-based tests — `tests/test_client.py` (every
parse branch, single-item wrapping, `-`/`None` coercion, URL+week construction),
`tests/test_scoreboard.py` (week dates, all pairings, single-matchup wrapping, week in URL,
error cases), `tests/test_cache.py` (read/write/append/last_updated/is_stale/isolation/
CACHE_DIR), and `tests/test_matchups.py` (delta-fetch: empty/partial cache, current-week
always re-fetched, prev-week re-fetch, dedup, one-call-per-week, season-not-started). The
resolution's framing ("paths demo mode bypasses") describes paths that are in fact covered —
just with hand-built fixtures rather than captured ones. The only *net-new* value is:
(1) real-shape hardening — real Yahoo payloads (goalie categories incl. GAA/GA lower-is-
better, full skater+goalie stat sets, real multi-matchup + roster shapes) could stress parse
assumptions the synthetic fixtures don't; and (2) one integration seam — flowing real client
parse output through the real cache round-trip together (today client-parse and cache are
tested separately, and `test_matchups.py` feeds the cache *fake* client output). Both are
nice-to-have, not a dangerous hole.
**Why it's not a clean one-session Engineer ticket:** The capture step needs a manual,
owner-only action — a live authenticated Yahoo session against a league with a *completed*
past week, run during the off-season (must first confirm last season's league key is still
queryable), plus sanitising real PII (team names, manager nicknames, league keys) out of the
saved JSON. The Engineer can't do this in-session, so a "ready" ticket would actually be
`blocked` on an owner prerequisite.
**Context for later — how to pick this up:** When the owner next has live authenticated
access (e.g. once the season starts, or by querying a still-accessible past-season league):
capture `scoreboard;week=N`, `teams/stats;type=week;week=N`, and team `roster` responses for
one completed week; sanitise identifiers; save under `tests/fixtures/` with a
`realweek_` prefix to distinguish from the synthetic set. Then add (a) parse assertions over
the real payloads in the existing `test_client.py`/`test_scoreboard.py` and (b) one
integration test flowing real parse output → `cache.append` → `cache.read` round-trip. Keep
`type=lastmonth` and `get_remaining_games` out of scope — they can't be sourced for a past
week (DECISIONS.md 2026-07-03). **Overlaps ROADMAP item 5 "Demo mode snapshot tooling"** — if
that lands a live-capture script first, reuse its capture/sanitise step here rather than
building a second one.
**Milestone:** none
**Blocked by:** nothing (gated on a manual owner capture, not on another ticket)
**Estimated complexity:** Small (fixtures + assertions in existing test files), but gated on a
manual owner capture.

---

## UX cleanup and design application

**Original request:** General UX polish pass; details TBD, but must include applying existing designs to the built pages.
**What was included:** Nothing — all pages to date used functional but unstyled or minimally styled markup.
**What was deferred:** The full polish pass.
**Context for later:** Scope is intentionally open — owner to specify designs and priority pages when this is picked up. At minimum: apply existing design assets/mockups to the Overview (leaderboard, head-to-head) and Waiver Wire pages. Likely also covers nav improvements, mobile responsiveness, and any interaction-level refinements (loading states, empty states, error states). Recommend scoping one page at a time when this is activated rather than one large ticket across all pages.
**Milestone:** none
**Blocked by:** nothing
**Milestone note (2026-07-25):** deliberately `none`. M1's definition is functional ("using
Overview, Waiver, and Projection"), not styled, so polish does not block M1; and it is open-ended
enough that forcing it onto M1 or M2 would manufacture precision. Owner may pull a specific page's
polish into M2 (strangers judge on presentation) if desired, but scope that as its own tagged
ticket rather than tagging this open-ended parent.
**Estimated complexity:** Medium–Large (depends on scope of designs; split into per-page tickets when activated)

---

## Waiver ranking: cross-position NaN composites bury a position group — FILED 2026-07-04 (from ticket 032)

**Original request:** Flagged by the code author during ticket 032 (multi-position waiver
filter). Not a defect in 032's union logic — a separate, pre-existing ranking-behaviour issue.
**What it is:** `analysis/waiver_ranking.rank_players` sinks players whose composite score is
NaN in any selected stat to the bottom of the ranking. When a search mixes a skater-only stat
with a goalie-only stat (now easily reachable via a D+G multi-position search, thanks to 032),
every goalie is NaN on the skater stat and vice-versa — so one position group is pushed to the
bottom and buried on later pages, even though both groups are correctly present in the pool.
**Why it surfaced now:** 032 made disjoint-stat, cross-position combinations far more
reachable than the old single-select UX did. The old UX effectively never mixed a skater-only
and goalie-only stat in one ranked list.
**What was deferred:** The whole fix. 032 ships without addressing it (correctly — the union
logic is right; the goalies/defencemen are in the pool, just ranked low).
**Context for later:** Fix lives in `analysis/waiver_ranking.py` (`rank_players` and its NaN
handling), pure-Python/pandas layer — testable against fixtures, no framework or API surface.
Open design question to resolve when scoping: what *should* a mixed skater+goalie stat ranking
do? Options include (a) rank within each position group and interleave, (b) rank only on stats
common to all selected positions, (c) surface a UI hint when the selected stats don't apply to
all selected positions. Pick the behaviour before scoping — this is an analysis-layer ticket,
so read the module first and write observable ACs over the ranked order.
**Milestone:** none
**Blocked by:** nothing
**Estimated complexity:** Small–Medium (one analysis-layer ticket + fixture tests), pending the
ranking-behaviour design decision above.
**See also:** "Waiver wire: rank on projected stats rather than raw recent production"
(filed 2026-07-23) — that idea changes *what* `rank_players` is fed, not how it treats NaN,
so the burial behaviour described here carries straight over. Whoever scopes either should
read both; fixing this one first means the projected ranking inherits the fix.

---

## Waiver wire: "playing this week" games weighting — FILED 2026-07-23

**Original request:** "Add a filter using games/schedule data (logic can likely be reused from
the week projection work) so players can be ranked or filtered by how many games they play in
the current week: 1, 2, 3, 4, etc."
**Owner decision (2026-07-23):** **It is a ranking weight, not a hard filter.** Games played this
week adjusts where a player lands in the ranking; it never removes players from the pool. The
original "filter or rank?" question is resolved — build the weight.
**What was included:** Nothing — logged only, not scoped into a ticket.
**What was deferred:** The whole feature.
**Read this first:** this idea is very likely superseded by "Waiver wire: rank on projected stats"
(filed 2026-07-23) — see the "Relationship to the projected-stats idea" bullet below before
scoping either one.
**Context for later:**
- **The data is already there, and cheaper than the owner assumed.** `data/schedule.py`
  `get_remaining_games(team_abbrs, from_date, to_date) -> {team_abbr: count}` hits the *public*
  NHL API (`api-web.nhle.com`, no auth). It costs zero Yahoo calls, so this feature carries no
  Yahoo rate-limit exposure.
- **The waiver page already calls it.** `web/routes/waiver.py` fetches games remaining
  (~lines 240–253), maps a `games_remaining` column onto the ranked DataFrame (~lines 280–283),
  and `web/templates/waiver/_table.html` (~line 146) already renders it as a column. So the
  feature is not "add schedule data", it is "make the number already on screen actionable".
- **Two real gaps:** (a) it is computed **only** when `period == "Last 30 days"` — the Season
  branch never populates `games_remaining_map`, so the column is blank there; (b) it is
  display-only — nothing in `analysis/waiver_ranking.rank_players` consumes it.
- **Where the weight would go.** `rank_players` sums per-category ranks into `composite_rank`
  (lower is better) and sorts on it. A games weight has to modify either that sum or the values
  fed into it. Weighting the composite is the crude version: it scales an *ordinal* rank sum, so
  the weight has no principled scale, and it applies uniformly across categories including rate
  stats (GAA, SV%) where "more games" should not inflate the value at all. That crudeness is the
  core reason the projected-stats idea is the better version of this — see below.
- **Week-window inconsistency to resolve while in there.** Waiver uses
  `from_date = week_start`; the projection route uses `from_date = max(today, week_start)`
  (`web/routes/projection.py` ~line 153). `get_remaining_games` skips games already in a FINAL
  state, so the two mostly agree, but they are not the same rule. Pick one and make both use it.
- **Failure mode to decide.** The waiver schedule fetch is wrapped in a bare
  `except Exception: games_remaining_map = {}`. Today that degrades to a blank column. As a
  weight it degrades silently and invisibly instead: every player gets 0 games, the weight
  becomes uniform, and the user sees a plausible-looking ranking that quietly ignores the
  schedule. Less destructive than a filter emptying the pool, but harder to notice — the ranking
  should say when schedule data is unavailable rather than pretending.
- **No schedule caching exists.** `data/cache.py` has tiers for matchups, player pools, and
  lastmonth stats — nothing for schedule. Every waiver submit re-hits the NHL API. Fine today;
  worth a short-TTL cache entry if this becomes a control users toggle repeatedly.
- **Layer:** as a weight this is no longer route + template only — `analysis/waiver_ranking.py`
  changes too, so it spans the analysis and UI layers and must be at least two tickets.
- **Demo/off-season caveat (applies to all three 2026-07-23 waiver entries):**
  `demo/data/games_remaining.json` is all zeros (snapshotted off-season), and per
  `docs/LEARNINGS.md` "Off-season → no live data" the live path returns zeros too. A games
  weighting therefore cannot be demonstrated or QA'd end-to-end until the demo snapshot is
  regenerated (ROADMAP "Demo mode snapshot tooling"). Plan on fixture-based tests plus a
  refreshed snapshot.
- **Relationship to the projected-stats idea — read before scoping.** Now that this is a weight
  rather than a filter, it and "Waiver wire: rank on projected stats" are **the same operation
  applied at different points**, not two complementary features. Both take recent production and
  adjust the ranking by games remaining. The difference is only *where*: this one scales the
  composite rank afterwards; the projected-stats idea scales each stat before ranking, via
  `per_game × games_remaining`. The projected version is strictly better on three counts — it
  works in stat units rather than on an ordinal rank sum, it correctly leaves rate stats (GAA,
  SV%) unscaled, and it divides by last-30 `games_played` first, so a player who happened to play
  more games in the last 30 days does not get credit for availability twice.
  **Consequence:** shipping both would double-count games remaining, once in the projected values
  and again in the weight. Treat this entry as the cheap approximation: build it only if the
  projected-stats idea is not happening soon; otherwise skip straight to that one and keep the
  games column as an explanatory display. The two should not both ship as ranking levers.
**Open questions for the owner (still unanswered):** should the weighting apply to the Season
period too, or stay a Last-30-days-only control? (The Season pool has no last-30 `games_played`,
so the two periods cannot use the same formula.)
**Milestone:** none
**Blocked by:** nothing
**Estimated complexity:** Small–Medium (analysis + route + template; two tickets, since it now
crosses the analysis/UI layer boundary), rising if it must also work in demo mode with a
regenerated snapshot. **But see the overlap bullet above — this may not be worth building at
all if the projected-stats idea is on the table.**

---

## Waiver wire: off-night identification + roster conflict check — FILED 2026-07-23

**Original request:** "On the waiver wire, identify which players play on off-nights. Ideally
this also checks against the user's own roster, to confirm the player could actually be started
on all those nights, or to flag where there would be a lineup conflict."
**Owner decision (2026-07-23) — off-night definition:** an off-night is a night where **fewer
than half the teams in the league have games**, evaluated **relative to that week's schedule**
rather than against a fixed constant. So the threshold is a proportion of the league (fewer than
half of 32 teams playing, i.e. fewer than ~8 games on the slate), applied per week against that
week's actual nights, not a hardcoded game count. This resolves the "fixed vs. relative" question
— it is relative, per week.
**What was included:** Nothing — logged only, not scoped into a ticket.
**What was deferred:** The whole feature.
**Context for later — this is two features, and the second one is the expensive one:**

*Part A — per-night schedule data (cheap, does not exist yet).* This is the main correction to
the premise: **the project does not have per-night granularity today.**
`data/schedule.get_remaining_games` deliberately collapses the schedule into a count per team
and throws the dates away (`nhl_counts[nhl_abbr] += 1`, ~line 97). The underlying NHL response
*does* carry it — the parse already walks `gameWeek[] → date → games[]` (~lines 77–84) — so a
sibling function returning `{team_abbr: [ISO date, ...]}` is a pure re-parse of the same HTTP
response: **no additional API cost, no new endpoint, no auth**. Pure-Python `data/` layer,
fixture-testable alongside `tests/test_schedule.py`.

*Part B — applying the off-night definition (settled, see Owner decision above).* A night counts
as an off-night when fewer than half the league's teams have games that night, judged relative to
the week in question. Two implementation notes follow from that:
- The rule is a **proportion of teams playing**, not a game count, so the calculation needs the
  count of distinct teams on the slate per date (each game contributes two teams). "Fewer than
  half of 32" lands around 8 games, but derive it from the team proportion so it stays correct if
  the league expands.
- **The current parse cannot supply this.** `get_remaining_games` filters games down to the
  requested `team_abbrs` (~lines 95–97) before counting, so it never sees the full nightly slate.
  The off-night calculation needs the *whole* league's schedule per date — which the same NHL
  response already contains and the function currently discards. No extra API call, but it does
  mean Part A's new function should return the full slate per date, not just the requested teams'
  games. Scope Part A with that in mind or Part B will need to re-fetch.
- "Relative to that week's schedule" means the off-night set is computed over the nights of the
  fantasy week being viewed (`week_start`..`week_end` from the scoreboard, as the waiver route
  already resolves them), not over a rolling window or the whole season.

*Part C — the roster conflict check (this is the cost driver).* The app currently cannot answer
"could I actually start this player", for three separate reasons:
- **It does not know which team is the user's.** `db/schema.sql` `user_sessions` stores
  `session_id`, tokens, and `league_key` — no team key. `data/client.get_teams` returns
  team_key / team_id / name / manager but no `is_owned_by_current_login` flag. The projection
  page sidesteps this entirely by making the user pick their team from a dropdown on every
  request (`web/routes/projection.py`, `/projection/matchup?team_key=…`). So this needs either
  a persisted my-team column (schema change + a picker + the auto-detect question) or the same
  per-request selector on the waiver page. **Decide this first — everything else in Part C
  depends on it.**
- **Roster slot limits are not fetched.** `data/client.get_settings_and_categories` parses only
  `current_week` / `start_week` / `end_week` plus stat categories. Yahoo's league settings
  response also carries `roster_positions` (how many C / LW / RW / D / G / Util / BN slots).
  Parsing it costs **no extra API call** — the settings call is already made — just extra parse
  work and a wider return shape.
- **Roster fetches are per-team, per-date, and uncached.** `data/roster.get_team_roster(session,
  team_key, date="YYYY-MM-DD")` exists and already returns each player's actual `roster_slot`,
  which is exactly what a conflict check needs. But it is **1 Yahoo call per team per date**,
  and there is no collection endpoint for multi-date rosters. A literal "can I start him on all
  N nights" check wants the roster for each night (up to 7 calls/week/team); the cheap
  approximation is "today's roster, held constant for the rest of the week" (1 call). CLAUDE.md's
  bulk-endpoint rule and the rate-limit posture both push hard toward the 1-call approximation.
  Roster responses are not cached today (`data/cache.py` covers matchups, player pools,
  lastmonth only) — a short-TTL roster cache would be part of this work if the waiver page starts
  fetching a roster on every submit.

**Sequencing:** Part A is the natural first ticket and also unblocks nothing else, so it can be
done independently. Part B is a small analysis addition on top of A. Part C should be split out
and is the only piece with an architectural surface (session/schema + a new Yahoo fetch on a hot
path) — it needs a Tech Lead consult, not just scoping.
**STILL OPEN — the owner has not answered these; do not guess, and do not scope Part C until
they are settled:**
1. **Does "could actually be started" mean today's roster held constant for the rest of the week
   (approximate, 1 Yahoo API call), or a real per-night lineup check (exact, up to 7 calls per
   week per team)?** This is the single biggest cost fork in the whole idea — it decides whether
   Part C is a modest addition or a new fetch-and-cache tier.
2. **Is the owner willing to persist a "my team" selection (a `user_sessions` schema change plus
   a picker), or should the waiver page use a per-request team dropdown like the projection page
   does?** Nothing in Part C can start until this is decided.

*(The third original question — what defines an off-night — was answered on 2026-07-23; see the
Owner decision at the top of this entry.)*
**Milestone:** none
**Blocked by:** nothing
**Estimated complexity:** Large overall. Small for Part A (per-night schedule data + tests),
Small–Medium for Part B (off-night flagging + UI), Medium–Large for Part C (needs the my-team
decision, a settings-parse extension, a roster fetch on the waiver path, and probably a roster
cache tier).

---

## Waiver wire: rank on projected stats rather than raw recent production — FILED 2026-07-23

**Original request:** "Project waiver-wire players' stats the same way the week projection does,
and rank on projected stats given the schedule, rather than on raw recent production."
**Product rationale (owner, 2026-07-23) — this is the point of the feature:** stars already rise
to the top of any 30-day or league-ranking sort, so a ranking that repeats that tells the manager
nothing he did not already know. The purpose of ranking on projected stats is to **surface hidden
gems** — the ordinary player whose value this week comes from the schedule. The owner explicitly
confirmed the consequence: **a 4-game journeyman outranking a 1-game star is the intended
behaviour, not a bug.** Anyone scoping this should not "fix" that by damping the schedule effect,
and QA should treat it as expected output rather than flagging it.
**What was included:** Nothing — logged only, not scoped into a ticket.
**What was deferred:** The whole feature.
**Context for later:**
- **The math exists and is a genuine reuse — but it is in the wrong layer.** The per-player
  projection formula lives in `_player_breakdown` in **`web/routes/projection.py`** (~lines
  61–89), not in `analysis/`: counting stat → `lastmonth / games_played × remaining_games`;
  rate stat (GAA, SV%, per `analysis/projection._is_rate_stat`) passed through unscaled.
  `analysis/projection.project_team_stats` is the team-level roll-up and is not directly
  reusable per player. So the clean first ticket is **lifting the per-player formula out of the
  route and into `analysis/projection.py`** (framework-free layer rule, `docs/ARCHITECTURE.md`
  key patterns #6), with the projection route adopting the moved helper. That gives waiver and
  projection one shared definition and makes the formula fixture-testable.
- **The waiver route already assembles every input.** In the "Last 30 days" branch,
  `web/routes/waiver.py` has `lm_pool` (per-player last-30 stats including `games_played`) and
  `games_remaining_map` (~lines 205–253). A projected-stat column is then a per-row apply, and
  `rank_players` runs on the projected columns instead of the raw ones.
- **Period interaction to decide.** This only works on the Last 30 days period — the Season pool
  carries no last-30 `games_played`, so there is no per-game rate to scale. Decide whether
  "Projected" replaces the Last 30 days option, becomes a third period option, or becomes a
  separate toggle.
- **Overlaps the NaN entry above.** See "Waiver ranking: cross-position NaN composites bury a
  position group" (filed 2026-07-04). Projecting changes *what values* `rank_players` receives,
  not *how it handles NaN* — goalies are still NaN on skater stats and vice versa, so the
  position-burial behaviour survives unchanged into a projected ranking. The two should be read
  together; the NaN design decision (rank-within-group vs. common-stats-only vs. UI hint) should
  be settled first so the projected ranking inherits it.
- **Supersedes the "playing this week" games weighting above — say so out loud when scoping.**
  The owner settled that idea as a ranking *weight* (2026-07-23), which makes it the same
  operation as this one applied at a cruder point: it scales the composite rank after ranking,
  where this scales each stat before ranking. This version is better on three counts — it works
  in stat units rather than on an ordinal rank sum, it leaves rate stats (GAA, SV%) unscaled via
  `_is_rate_stat`, and it divides by last-30 `games_played` first so availability is not counted
  twice. **Shipping both would double-count games remaining.** The honest recommendation: build
  this one, drop the separate weighting, and keep the games-remaining column purely as the
  on-screen explanation of why a player ranks where he does. Both ideas serve the owner's stated
  "surface hidden gems" goal; this is the correct implementation of it.
- **Off-season caveat:** games remaining is 0 for every team live, and
  `demo/data/games_remaining.json` is all zeros, so every projected value collapses to 0 and the
  ranking is degenerate. Verification has to be fixture-based until the demo snapshot is
  regenerated (see the games-weighting entry above and `docs/LEARNINGS.md`).
**Resolved (owner, 2026-07-23):** waiver players are unrostered, so there is no week-to-date total
to add — projecting them means "expected production over the *rest of this week*", and that is
confirmed as the intent. The ranking is deliberately schedule-driven, not schedule-neutral. See
the Product rationale at the top of this entry.
**Milestone:** none
**Blocked by:** nothing
**Estimated complexity:** Medium — one analysis-layer ticket (lift + generalise the per-player
projection, with fixture tests) plus one waiver route/template ticket. Do not bundle them; they
span the analysis and UI layers.

---

[PM populates this file as features are scoped down during active development]
