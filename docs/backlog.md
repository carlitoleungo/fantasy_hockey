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
**Estimated complexity:** Large

---

## Migration: Per-user cache storage

**Original request:** Migrate away from Streamlit as part of the public app rebuild.
**What was included:** Tech Lead ticket (001) will specify the storage backend. ARCHITECTURE.md will define where cached data lives.
**What was deferred:** Implementation — replacing `.cache/{league_key}/` parquet files with the chosen storage backend (object storage, DB blob columns, etc.).
**Context for later:** The cache layer is in `data/cache.py`. Key functions to port: `read`, `write`, `append`, `last_updated`, `is_stale`, `write_player_pool`, `upsert_lastmonth_cache`. The new implementation must be per-user (keyed by user ID + league key) since multiple users will share one deployment. The parquet file format can likely be preserved — just the storage location changes.
**Estimated complexity:** Medium (one data ticket)

---

## Migration: Week projection page — SCOPED 2026-07-02 → tickets 028–031

**Original request:** Rebuild the Streamlit week projection page (`pages/04_week_projection.py`) in the new framework.
**Resolution:** Scoped into tickets 028–031 (see the "Week Projection Page" entry above and `docs/ROADMAP.md`). This was a duplicate of that entry; both are now resolved.

---

## Deployment configuration

**Original request:** Deploy the rebuilt app publicly.
**What was included:** Nothing yet. Tech Lead ticket (001) will name the deployment target.
**What was deferred:** Dockerfile, CI/CD pipeline, environment variable configuration, and production secrets management.
**Context for later:** Current app has no containerisation. The new stack will need at minimum a `Dockerfile`, a `.env.example`, and CI steps for running `pytest tests/`. The chosen deployment platform (from ARCHITECTURE.md) will determine what else is needed.
**Estimated complexity:** Medium

---

## Streamlit Community Cloud decommissioning

**Original request:** Identified as a go-live step after scoped tickets 001–005.
**What was included:** Nothing.
**What was deferred:** The final cutover: stop the SC deployment, update or redirect any existing links, confirm the new Fly.io app is the canonical URL.
**Context for later:** SC watches the `main` branch. The simplest decommission is disconnecting the app in the SC dashboard. If there are external links to the SC URL, a redirect (either in `fly.toml` or via DNS) is worth setting up. This is the last step — do it only after the new app is live and validated.
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
**Estimated complexity:** Small–Medium (2 files: `web/routes/waiver.py`,
`web/templates/waiver/index.html`).

---

## Migration: Login page

**Original request:** Rebuild the login/landing experience in the new framework.
**What was included:** `/auth/login` redirects immediately to Yahoo OAuth — there is no dedicated login page, just a nav link that kicks off the OAuth flow.
**What was deferred:** A proper login landing page (e.g. a page at `/login` or `/` for unauthenticated users that explains the app, offers a "Sign in with Yahoo" button, and links to the demo mode).
**Context for later:** The current entry point is `GET /auth/login` in `web/routes/auth.py` which immediately generates an OAuth URL and redirects. The home route (`/`) serves the league-picker to authenticated users; unauthenticated visits fall through to the login redirect. A dedicated login page would intercept unauthenticated `/` visits and render a landing screen before the OAuth round-trip begins. This is also the natural place to surface the demo mode entry point prominently.
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
**Estimated complexity:** Small (fixtures + assertions in existing test files), but gated on a
manual owner capture.

---

## UX cleanup and design application

**Original request:** General UX polish pass; details TBD, but must include applying existing designs to the built pages.
**What was included:** Nothing — all pages to date used functional but unstyled or minimally styled markup.
**What was deferred:** The full polish pass.
**Context for later:** Scope is intentionally open — owner to specify designs and priority pages when this is picked up. At minimum: apply existing design assets/mockups to the Overview (leaderboard, head-to-head) and Waiver Wire pages. Likely also covers nav improvements, mobile responsiveness, and any interaction-level refinements (loading states, empty states, error states). Recommend scoping one page at a time when this is activated rather than one large ticket across all pages.
**Estimated complexity:** Medium–Large (depends on scope of designs; split into per-page tickets when activated)

---

[PM populates this file as features are scoped down during active development]
