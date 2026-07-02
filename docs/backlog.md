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

## Waiver Wire: Multi-position filtering — HIGH PRIORITY

**Original request:** Allow selecting multiple positions simultaneously on the waiver wire
page (e.g. C + LW to find dual-eligible forwards).
**What was included:** Single-select radio buttons (All / C / LW / RW / D / G) — one
position at a time only.
**What was deferred:** Multi-select position filtering.
**Context for later:** Two surfaces need to change:
1. `web/templates/waiver/index.html` — convert position pill `<input type="radio">` to
   `<input type="checkbox" name="positions">` (keep "All" as a special case that clears
   the others). The form already uses `hx-trigger="change"` so HTMX re-POST fires
   automatically.
2. `analysis/waiver_ranking.py` — `filter_by_position(df, position)` takes a single
   string. Update signature to accept a list (or comma-separated string) and filter
   using `display_position` contains-any logic. Note: `display_position` is composite
   (`"C,LW"`) — split on comma when matching.
3. `web/routes/waiver.py` — update the `position` form field to accept `list[str]`
   (FastAPI: `positions: list[str] = Form([])`); update the cache key and `api_position`
   mapping accordingly. Per-position caching will need a decision on how to key multi-select
   combinations (union of individual position caches vs. a new combined key).
**Why deferred:** The waiver wire tickets (018, 019a, 019b) used the Streamlit prototype's
single-select design. Multi-select is core UX — managers routinely look for C/LW or
LW/RW eligible players.
**Estimated complexity:** Medium (template + analysis + route changes; cache key strategy
needs a short Tech Lead or PM decision)

---

## Migration: Login page

**Original request:** Rebuild the login/landing experience in the new framework.
**What was included:** `/auth/login` redirects immediately to Yahoo OAuth — there is no dedicated login page, just a nav link that kicks off the OAuth flow.
**What was deferred:** A proper login landing page (e.g. a page at `/login` or `/` for unauthenticated users that explains the app, offers a "Sign in with Yahoo" button, and links to the demo mode).
**Context for later:** The current entry point is `GET /auth/login` in `web/routes/auth.py` which immediately generates an OAuth URL and redirects. The home route (`/`) serves the league-picker to authenticated users; unauthenticated visits fall through to the login redirect. A dedicated login page would intercept unauthenticated `/` visits and render a landing screen before the OAuth round-trip begins. This is also the natural place to surface the demo mode entry point prominently.
**Estimated complexity:** Small (UI ticket; no new data layer work)

---

## UX cleanup and design application

**Original request:** General UX polish pass; details TBD, but must include applying existing designs to the built pages.
**What was included:** Nothing — all pages to date used functional but unstyled or minimally styled markup.
**What was deferred:** The full polish pass.
**Context for later:** Scope is intentionally open — owner to specify designs and priority pages when this is picked up. At minimum: apply existing design assets/mockups to the Overview (leaderboard, head-to-head) and Waiver Wire pages. Likely also covers nav improvements, mobile responsiveness, and any interaction-level refinements (loading states, empty states, error states). Recommend scoping one page at a time when this is activated rather than one large ticket across all pages.
**Estimated complexity:** Medium–Large (depends on scope of designs; split into per-page tickets when activated)

---

[PM populates this file as features are scoped down during active development]
