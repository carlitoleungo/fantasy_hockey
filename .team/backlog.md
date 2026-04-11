# Backlog — Fantasy Hockey Waiver Wire

Features and ideas deferred from active development. Each entry has enough context
to pick up without re-explaining the original idea.

---

## Week Projection Page

**Original request:** Show projected stats for the current week based on games remaining
and recent player performance.
**What was included:** Scaffolded in `pages/04_week_projection.py`; demo data hooks exist
in `data/demo.py` (`get_projection_context()`, `get_projection_pair_data()`).
**What was deferred:** Full implementation — the data functions and UI are not yet built.
**Context for later:** The demo stubs in `data/demo.py` define the expected return shapes.
The data layer will need a new function to fetch remaining schedule data and compute
projected stats from `players_lastmonth` rates × games remaining. The `get_remaining_games()`
function in `data/schedule.py` (or equivalent) already fetches games-remaining-this-week
for the waiver wire page — that logic can likely be extended for weekly projections.
**Estimated complexity:** Large (separate data ticket + UI ticket minimum)

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

## Migration: League overview page

**Original request:** Rebuild the Streamlit league overview page (`pages/01_league_overview.py`) in the new framework.
**What was included:** Nothing yet — the data and analysis layers it depends on (`data/matchups.py`, `analysis/team_scores.py`, `analysis/matchup_sim.py`) are preserved and need no changes.
**What was deferred:** The UI implementation.
**Context for later:** The page renders two views: (1) a weekly leaderboard table with all teams' stats for a selected week, color-coded by best/worst; (2) a head-to-head comparison between two selected teams showing category-by-category winners. The current implementation uses custom HTML/CSS tables embedded in `st.html()`. The new UI can use a component library or plain HTML — the data shapes from `analysis/team_scores.weekly_scores_ranked()` and `analysis/matchup_sim.simulate()` are stable.
**Estimated complexity:** Medium (UI ticket only, data layer is ready)

---

## Migration: Waiver wire page

**Original request:** Rebuild the Streamlit waiver wire page (`pages/03_waiver_wire.py`) in the new framework.
**What was included:** Nothing yet.
**What was deferred:** The UI implementation.
**Context for later:** The page has position filter buttons (All/C/LW/RW/D/G), stat category toggles (multi-select chips), a ranking period radio (Season / Last 30 days), and a paginated table (25 rows/page). Lazy-loading is critical — player pools are fetched per (position, stat) pair only when that combination is selected. The current implementation stores fetched pools in session state keyed by `ww_fetched_sorts`. The new implementation needs an equivalent client-side or server-side lazy-fetch pattern. Data comes from `data/players.py` and is ranked by `analysis/waiver_ranking.py`.
**Estimated complexity:** Large (lazy-loading complexity; consider splitting into data-API ticket + UI ticket)

---

## Migration: Week projection page

**Original request:** Rebuild the Streamlit week projection page (`pages/04_week_projection.py`) in the new framework.
**What was included:** Nothing yet.
**What was deferred:** The UI implementation (and completion of the underlying data/analysis layer — see "Week Projection Page" entry above).
**Context for later:** This page depends on live scoreboard data (one API call per page load), team rosters (fetched per team pair selection), last-30-day player stats, and remaining schedule. It is the most data-intensive page. Tackle after the simpler pages are ported.
**Estimated complexity:** Large

---

## Migration: Demo mode port

**Original request:** Preserve the demo mode (full app experience with static data, no Yahoo account) in the new framework.
**What was included:** Nothing yet. Demo data files in `demo/data/` are preserved and need no changes.
**What was deferred:** The demo mode routing and data loading in the new framework.
**Context for later:** Demo mode currently bypasses OAuth entirely and loads from `data/demo.py` instead of the live API. The new implementation needs: (1) a public `/demo` route that doesn't require a session, (2) a demo-mode flag in the request context, (3) conditional data loading in route handlers (call `data.demo.*` instead of `data.client.*` when in demo mode). The demo data loaders (`get_matchups`, `get_stat_categories`, `get_player_pools`, etc.) are already in `data/demo.py`.
**Estimated complexity:** Medium

---

## Deployment configuration

**Original request:** Deploy the rebuilt app publicly.
**What was included:** Nothing yet. Tech Lead ticket (001) will name the deployment target.
**What was deferred:** Dockerfile, CI/CD pipeline, environment variable configuration, and production secrets management.
**Context for later:** Current app has no containerisation. The new stack will need at minimum a `Dockerfile`, a `.env.example`, and CI steps for running `pytest tests/`. The chosen deployment platform (from ARCHITECTURE.md) will determine what else is needed.
**Estimated complexity:** Medium

---

## Post-login landing page + league selector

**Original request:** Identified as a gap after scoped tickets 001–005.
**What was included:** Nothing — no ticket written yet.
**What was deferred:** After a successful OAuth callback the app redirects to `/`. That route doesn't exist yet. Users need a page where they can see their leagues and select one before any data page is useful.
**Context for later:** The Streamlit prototype handles this in `app.py` using `get_user_hockey_leagues()` from `data/leagues.py` and stores the result in `st.session_state`. The FastAPI equivalent is a `GET /` route that calls `data.leagues.get_user_hockey_leagues()` with the session's `requests.Session`, renders a league-picker template, and stores the selected `league_key` in the session row (add a `league_key TEXT` column to `user_sessions`). This is a prerequisite for every data page — nothing useful renders without a selected league.
**Estimated complexity:** Medium (route + template + session schema update)

---

## Logout route

**Original request:** Identified as a gap after scoped tickets 001–005. Specified in ARCHITECTURE.md session strategy but no ticket written.
**What was included:** Nothing.
**What was deferred:** `GET /auth/logout` — deletes the `user_sessions` row, clears the `session_id` cookie, redirects to `/`.
**Context for later:** ARCHITECTURE.md specifies: "Logout: DELETE row from `user_sessions`, clear cookie, redirect to `/`." One route handler, no data layer involvement. Straightforward but must exist before go-live — without it users have no way to disconnect their Yahoo account.
**Estimated complexity:** Small

---

## Error handling strategy

**Original request:** Identified as a gap after scoped tickets 001–005. Not currently designed anywhere.
**What was included:** Nothing.
**What was deferred:** A consistent approach to what users see when things go wrong: Yahoo API failures, invalid/expired cache, `requests.HTTPError` from token exchange, missing league data.
**Context for later:** The Streamlit prototype showed errors inline with `st.error()`. The FastAPI app needs: (1) a FastAPI exception handler registered in `web/main.py` for `requests.HTTPError` and a custom `YahooAPIError`; (2) a `500.html` / `error.html` Jinja2 template; (3) a decision on whether Yahoo API failures should show a user-facing message ("Yahoo is unavailable, try again") or just log and redirect. This should be designed before any data pages are built — retrofitting consistent error handling across four routes is harder than building it in upfront.
**Estimated complexity:** Medium (design decision + exception handler + error template)

---

## `CACHE_DIR` env var wiring

**Original request:** Identified as a gap after scoped tickets 001–005.
**What was included:** ARCHITECTURE.md specifies `CACHE_DIR` as env-overridable, pointing to `/data/cache/` on Fly.io.
**What was deferred:** Actually wiring it. `data/cache.py` currently hardcodes `CACHE_DIR = ".cache"`. The constant needs to read from `os.environ.get("CACHE_DIR", ".cache")` so the Fly.io volume path works without modifying `cache.py`'s logic.
**Context for later:** One-line change in `data/cache.py` line 24. Must be done before deployment — without it the cache writes to the container's ephemeral filesystem and is lost on every restart.
**Estimated complexity:** Small

---

## Streamlit Community Cloud decommissioning

**Original request:** Identified as a go-live step after scoped tickets 001–005.
**What was included:** Nothing.
**What was deferred:** The final cutover: stop the SC deployment, update or redirect any existing links, confirm the new Fly.io app is the canonical URL.
**Context for later:** SC watches the `main` branch. The simplest decommission is disconnecting the app in the SC dashboard. If there are external links to the SC URL, a redirect (either in `fly.toml` or via DNS) is worth setting up. This is the last step — do it only after the new app is live and validated.
**Estimated complexity:** Small

---

[PM populates this file as features are scoped down during active development]
