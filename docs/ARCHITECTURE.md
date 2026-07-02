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
    DECISIONS.md             # Newest-first decisions log
  requirements.txt           # Existing Streamlit deps (kept for prototype)
  requirements-web.txt       # fastapi uvicorn[standard] jinja2 itsdangerous python-multipart
  Dockerfile                 # python:3.11-slim; installs requirements-web.txt
  fly.toml                   # planned, not yet in repo (deployment is a roadmap item); port 8000; /data volume mount
```

## Key patterns

1. **Single DB connection per request** — `db/connection.py` opens a SQLite connection in WAL
   mode; a FastAPI dependency `Depends(get_db)` provides it to route handlers and closes it
   after the response.

2. **Session middleware via `Depends(require_user)`** — reads `session_id` cookie, looks up
   tokens in `user_sessions`, calls `_is_valid`; if within the 60-second buffer calls
   `_try_refresh`; injects a `CurrentUser` dataclass into `request.state`. Routes that do
   not declare `Depends(require_user)` are public. `optional_user` is a variant that returns
   `None` instead of raising `RequiresLogin`; use it for routes that serve both authenticated
   and unauthenticated visitors.

3. **Demo and auth routes bypass session checks** — `/demo/*` and `/auth/*` are registered
   on a public `APIRouter` that does not include the `require_user` dependency.

4. **`data/` and `analysis/` called directly from route handlers** — no additional service
   layer. Route handlers are the integration point between HTTP and the Python data stack.

5. **HTMX fragment pattern for filter interactions** — filter controls POST to
   `/api/waiver/players` with `HX-Request: true`; the handler returns a rendered HTML
   `<table>` fragment that HTMX swaps into the DOM. No JSON API needed.

6. **Pure-Python `data/`, `analysis/`, `auth/` layers** — no framework imports (no
   `import streamlit`, no `import fastapi`), no route decorators, no DB ORM calls (raw
   `sqlite3` lives in `db/connection.py` only). These modules take inputs and return
   DataFrames or plain Python dicts; route handlers in `web/` are the only integration
   point. The Reviewer treats violations as always-blockers.

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

All architecture and stack decisions live in [`docs/DECISIONS.md`](DECISIONS.md)
(newest-first). The original stack selection is recorded there as the 2026-04-10
entries.
