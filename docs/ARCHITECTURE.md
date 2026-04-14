# Architecture — Fantasy Hockey Waiver Wire

## Overview

A public-facing web app that helps fantasy hockey managers evaluate waiver wire add/drop
decisions using Yahoo Fantasy API data. Users authenticate with their own Yahoo account;
the backend fetches their league, matchup, and player data; the frontend renders stat tables
and rankings. A demo mode lets unauthenticated users explore a pre-snapshotted dataset.

The backend is Python (FastAPI). The frontend is server-rendered HTML (Jinja2 templates)
enhanced with HTMX for partial-page filter interactions and Alpine.js for lightweight
client-side toggles. No JS build pipeline.

## Tech stack

- **Backend:** FastAPI + uvicorn (single worker) — keeps `data/` and `analysis/` importable
  with no language boundary; single worker is safe for SQLite write concurrency
- **Frontend:** Jinja2 templates + HTMX CDN + Alpine.js CDN + TailwindCSS CDN — interactive
  table/filter UX without a build pipeline; total JS payload ~22 KB
- **Auth:** Yahoo OAuth 2.0 via `requests` (existing `auth/oauth.py` logic, minus Streamlit
  imports) with server-side sessions in SQLite
- **Session store:** SQLite at `/data/app.db` (two tables: `oauth_states`, `user_sessions`) —
  zero-infrastructure, single-file, WAL mode for concurrent reads
- **League data cache:** Local disk at `/data/cache/{league_key}/` (parquet files via
  existing `data/cache.py`, `CACHE_DIR` env-overridable) — persistent across restarts via
  Fly.io volume
- **Deployment:** Fly.io, single region (`iad`), 1 container + 1 persistent volume at `/data`

## What's preserved from the prototype

| Path | What it does | Status |
|------|-------------|--------|
| `data/__init__.py` | Package marker | Unchanged |
| `data/client.py` | Yahoo API calls, XML→dict parsing, `_as_list`/`_coerce` helpers | Unchanged |
| `data/cache.py` | Parquet + metadata JSON disk cache; delta-fetch, TTL, append patterns | Unchanged (`CACHE_DIR` pointed at `/data/cache/`) |
| `data/matchups.py` | Incremental matchup fetch with delta-fetch pattern | Unchanged |
| `data/players.py` | Available player pagination, season + lastmonth stats | Unchanged |
| `data/leagues.py` | Fetch and enumerate user's hockey leagues | Unchanged |
| `data/roster.py` | Roster fetching | Unchanged |
| `data/schedule.py` | Schedule / games-remaining data | Unchanged |
| `data/scoreboard.py` | Scoreboard data | Unchanged |
| `data/demo.py` | Demo mode static file loader | Unchanged |
| `demo/data/` | Static parquet/JSON snapshot for demo mode | Unchanged |
| `analysis/__init__.py` | Package marker | Unchanged |
| `analysis/waiver_ranking.py` | Composite player ranking by stat category | Unchanged |
| `analysis/team_scores.py` | Weekly team standings and avg rank | Unchanged |
| `analysis/matchup_sim.py` | Head-to-head simulation | Unchanged |
| `analysis/projection.py` | Week projection logic | Unchanged |
| `auth/oauth.py` (core logic) | `_stamp_expiry`, `_is_valid`, `_try_refresh`, `exchange_code` | Logic preserved; Streamlit imports and file-based nonce helpers removed in ticket 004 |

## What's replaced

| Old | New | Why |
|-----|-----|-----|
| `app.py` | `web/main.py` | Streamlit entry point → FastAPI app factory |
| `pages/__init__.py` | (removed — no equivalent in FastAPI structure) | Streamlit package marker → not needed |
| `pages/01_league_overview.py` | `web/routes/leagues.py` + templates | Streamlit page → FastAPI route + Jinja2 |
| `pages/03_waiver_wire.py` | `web/routes/waiver.py` + templates | Streamlit page → FastAPI route + Jinja2 |
| `pages/04_week_projection.py` | `web/routes/projection.py` + templates | Streamlit page → FastAPI route + Jinja2 |
| `st.session_state["tokens"]` | SQLite `user_sessions` table | In-process per-tab → persistent per-user |
| `@st.cache_data` | FastAPI dependencies + HTTP cache headers | Streamlit-specific → standard HTTP caching |
| `_save_state` / `_load_states` in `auth/oauth.py` | SQLite `oauth_states` table | Shared flat file → atomic, TTL-aware DB rows |
| `.streamlit/oauth_states.json` | `oauth_states` DB table | Per-row atomic ops replace whole-file writes |
| `.cache/{league_key}/` (path only) | `/data/cache/{league_key}/` | Local ephemeral disk → persistent volume |

## Directory structure

```
fantasy_hockey/
  web/
    main.py                  # FastAPI app factory; mounts routers, registers middleware
    routes/
      auth.py                # GET /auth/login, GET /auth/callback
      leagues.py             # GET /leagues (HTML)
      waiver.py              # GET /waiver (HTML), POST /api/waiver/players (HTMX fragment)
      projection.py          # GET /projection (HTML)
      demo.py                # GET /demo/* — no auth required
      health.py              # GET /health → {"status": "ok"}
    middleware/
      session.py             # Validates session cookie; refreshes tokens; injects current_user
    templates/               # Jinja2 .html files
      base.html
      waiver.html
      leagues.html
      projection.html
      demo/
    static/                  # Favicon, any vendored CSS overrides
  db/
    schema.sql               # CREATE TABLE oauth_states, user_sessions
    connection.py            # get_db() → sqlite3 connection with WAL mode + row_factory
  auth/
    oauth.py                 # As-is minus st imports; client_id/secret/redirect_uri as params
  data/                      # Unchanged
  analysis/                  # Unchanged
  demo/data/                 # Unchanged
  docs/
    ARCHITECTURE.md          # This file
    decisions.md             # Historical decisions log
  requirements.txt           # Existing Streamlit deps (kept for prototype)
  requirements-web.txt       # fastapi uvicorn[standard] jinja2 itsdangerous python-multipart
  Dockerfile                 # python:3.11-slim; installs requirements-web.txt
  fly.toml                   # port 8000; /data volume mount
```

## Key patterns

1. **Single DB connection per request** — `db/connection.py` opens a SQLite connection in WAL
   mode; a FastAPI dependency `Depends(get_db)` provides it to route handlers and closes it
   after the response.

2. **Session middleware via `Depends(require_user)`** — reads `session_id` cookie, looks up
   tokens in `user_sessions`, calls `_is_valid`; if within the 60-second buffer calls
   `_try_refresh`; injects a `CurrentUser` dataclass into `request.state`. Routes that do
   not declare `Depends(require_user)` are public.

3. **Demo and auth routes bypass session checks** — `/demo/*` and `/auth/*` are registered
   on a public `APIRouter` that does not include the `require_user` dependency.

4. **`data/` and `analysis/` called directly from route handlers** — no additional service
   layer. Route handlers are the integration point between HTTP and the Python data stack.

5. **HTMX fragment pattern for filter interactions** — filter controls POST to
   `/api/waiver/players` with `HX-Request: true`; the handler returns a rendered HTML
   `<table>` fragment that HTMX swaps into the DOM. No JSON API needed.

## Data flow

```
Browser → FastAPI route handler
  → Depends(require_user) validates session cookie → injects current_user
  → route calls data/ functions (requests.Session built from auth/oauth.py)
    → data/cache.py checks parquet files at /data/cache/{league_key}/
    → cache miss → Yahoo API call via data/client.py → write cache
  → route calls analysis/ functions on the DataFrame
  → Jinja2 renders full HTML page (or HTMX fragment for filter interactions)
Browser ← HTML response
```

Demo path:
```
Browser → /demo/* route → data/demo.py loads static parquet/JSON → Jinja2 renders → Browser
```

## Session strategy

**After `GET /auth/callback`** validates the nonce and receives tokens from Yahoo:
1. `_stamp_expiry(tokens)` adds `expires_at = time.time() + expires_in`
2. `session_id = secrets.token_urlsafe(32)` is generated server-side
3. Row inserted: `user_sessions(session_id, access_token, refresh_token, expires_at, created_at)`
4. Response sets `Set-Cookie: session_id=<value>; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000` (30 days)
5. Redirect to `/`

**On each subsequent request to a protected route:**
1. `require_user` dependency reads `session_id` from cookie; missing → 302 to `/auth/login`
2. Row looked up in `user_sessions`; not found → 302 to `/auth/login`
3. `_is_valid(tokens)`: if False → `_try_refresh(tokens)` → update row; if refresh fails → delete row + 302 to `/auth/login`
4. `CurrentUser(session_id, access_token, expires_at)` injected into `request.state`

**Logout:** DELETE row from `user_sessions`, clear cookie, redirect to `/`.

## Storage tiers

| Tier | Technology | Location | TTL / lifecycle |
|------|-----------|----------|-----------------|
| CSRF state nonces | SQLite `oauth_states` table | `/data/app.db` | `expires_at = now + 300 s`; row deleted on first valid use (one-time) |
| OAuth tokens per user | SQLite `user_sessions` table | `/data/app.db` | 30-day cookie `Max-Age`; row deleted on logout or refresh failure |
| League parquet cache | Local disk via `data/cache.py` | `/data/cache/{league_key}/` | Per-type TTL: matchups incremental, players 24 h |
| Demo data | Static files baked into container image | `demo/data/` | Immutable; updated by regenerating and redeploying |

## Decisions log

| Date | Decision | Rationale | Alternatives considered |
|------|----------|-----------|------------------------|
| 2026-04-10 | FastAPI over Flask or Django as the backend framework | FastAPI's async-native request handling supports concurrent per-user Yahoo OAuth callbacks without threading configuration; automatic OpenAPI docs aid single-engineer maintenance; Pydantic validation integrates cleanly with the existing Python data stack. Flask lacks native async support and requires extra libs (Flask-Login, Blueprints) to reach feature parity. Django's ORM, admin, and templating are heavy for a thin API-proxy app, and its opinionated project layout conflicts with the existing `data/`/`analysis/` module structure | Flask (synchronous by default, OAuth callback handling requires extra libs); Django (high-ceremony ORM + settings overhead; incompatible project layout assumptions) |
| 2026-04-10 | FastAPI + HTMX + Jinja2; no JS build pipeline | Single-engineer Python team; UI is tables and filters, not a rich SPA; HTMX handles partial-page updates without a JS framework or build step | React + FastAPI (adds build pipeline and a language context switch); Vue (same trade-offs as React at smaller scale) |
| 2026-04-10 | Responsive web only; PWA deferred | Waiver wire UX (select filters, scan table, pick player) fits a mobile browser without native code; native adds two codebases and app-store friction for marginal UX gain | React Native (rejected); PWA (deferred — manifest.json can be added later without architecture change) |
| 2026-04-10 | Single uvicorn worker | SQLite is not safe for concurrent writes across multiple processes; a single worker eliminates write-lock contention with no throughput cost at the expected scale (dozens–low hundreds of concurrent users) | Multiple workers with Postgres (adds managed DB cost and ops complexity) |
| 2026-04-10 | SQLite for session/nonce storage | Zero infrastructure; single file; WAL mode handles concurrent reads; `DELETE … WHERE state = ?` is atomic within one process | Redis (adds a second service to operate); Postgres (adds cost and managed-DB complexity) |
| 2026-04-10 | Fly.io with persistent volume | Container-based one-command deploys; persistent volume at `/data` solves cache ephemerality without adding an object-storage SDK; North American single-region sufficient for the audience | Railway (similar DX, less mature persistent volume support); AWS ECS (excessive operational overhead for a single engineer) |
| 2026-04-10 | Parquet cache stays on local disk (`/data/cache/`) | `data/cache.py` requires zero changes; `CACHE_DIR` env var redirects the path; the persistent volume makes disk storage durable | S3 / Cloudflare R2 (would require modifying `cache.py` and adding an SDK dependency) |
| 2026-04-10 | Server-side session: tokens in DB, session_id in cookie | Long-lived OAuth tokens are sensitive credentials; keeping them in the DB limits exposure if a cookie is stolen or leaked | Signed cookie with tokens embedded (simpler, but tokens leave the server) |
