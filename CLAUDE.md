# Fantasy Hockey Manager Tool

## Project Purpose
A public-facing web app that helps fantasy hockey managers evaluate waiver wire add/drop decisions using Yahoo Fantasy API data. Users authenticate with their own Yahoo account; the backend fetches their league, matchup, and player data; the frontend renders stat tables and rankings. A demo mode lets unauthenticated users explore a pre-snapshotted dataset.

The repo is mid-migration: a FastAPI/HTMX app (`web/`, `db/`) is replacing the original Streamlit prototype (`app.py`, `pages/`) view-by-view. The pure-Python `data/`, `analysis/`, and `auth/` layers are shared by both and are stable.

## Team Workflow
Development runs through a team-of-personas workflow: tickets in `tickets/`, persona definitions in `.team/`, operating manual in **`WORKFLOW.md`** (start with its Quick start section). If you're asked to scope, implement, QA, or review a ticket, read the relevant persona file first.

## Key Documentation
- `docs/ARCHITECTURE.md` — stack, directory structure, layer rules, data flow, storage tiers
- `docs/DECISIONS.md` — newest-first architectural decisions log (why things are the way they are)
- `docs/LEARNINGS.md` — recurring gotchas, including all Yahoo API quirks
- `docs/improvements.md` — Type-tagged tracker for quality nits and bugs
- `RUNNING.md` — first-time setup and run instructions (venv, ngrok, Yahoo OAuth)
- Yahoo Fantasy Sports API (official): https://developer.yahoo.com/fantasysports/guide/#player-resource
- Yahoo Fantasy API (better structured): https://yahoo-fantasy-node-docs.vercel.app/resource/player/stats

Auth flow and API patterns are established in `auth/oauth.py` and `data/client.py` — read those as the reference implementation, not the notebook.

## Caching
The parquet cache layer (`data/cache.py`) is the primary defence against Yahoo rate limits. Storage tiers and refresh strategies are documented in `docs/ARCHITECTURE.md` § Storage tiers; delta-fetch behaviour is documented in `docs/DECISIONS.md` (see the matchups.py entries).

- Cache location is the `CACHE_DIR` env var: defaults to `.cache/` locally, `/data/cache/` in production. Both are gitignored — cache files can always be regenerated from the API.
- Available (waiver) players are never cached — always fetched live.

## Secrets & Auth
- Yahoo OAuth 2.0, redirect-based flow, implemented directly with `requests` in `auth/oauth.py` (the `yahoo_oauth` library is incompatible — see `docs/DECISIONS.md` 2026-03-03).
- Credentials come from environment variables, loaded from a gitignored `.env` file locally: `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REDIRECT_URI`. See `.env.example` for the full set (`DB_PATH`, `CACHE_DIR`, `HTTPS_ONLY`).
- Never hardcode credentials or commit secrets files.
- Token refresh is handled transparently by the session middleware — users should not need to re-auth mid-session.
- Sessions are server-side: tokens live in SQLite, the browser holds only an opaque `session_id` cookie (see `docs/ARCHITECTURE.md` § Session strategy).

## API Notes
- Yahoo Fantasy API uses OAuth 2.0. Redirect URIs must be registered in the Yahoo developer console; Yahoo requires HTTPS, so local development uses an ngrok tunnel (see `RUNNING.md`).
- Rate limits apply — the cache layer is the primary defence against hitting them.
- **Minimise API calls**: always prefer bulk/collection endpoints over per-entity calls. For example, use `/league/{key}/teams/stats;type=week;week={w}` (1 call for all teams) instead of N individual `/team/{key}/stats` calls. When adding new data fetches, check whether a collection endpoint exists before defaulting to a per-item loop.
- Weekly data is keyed by week number within a season.
- Player stats endpoints differ for season aggregate vs recent (`type=lastmonth` is the only param that returns last-30-day stats — see `docs/DECISIONS.md` 2026-03-23).
- The API returns XML by default; use format=json query param where supported.

## Known Gotchas
All recurring gotchas (Yahoo API quirks, xmltodict behaviour, test patch targets) live in **`docs/LEARNINGS.md`** — read it before touching `data/` or `analysis/`. One legacy note: the Streamlit prototype reruns the entire script on every interaction, so its expensive operations are wrapped in `@st.cache_data`; this does not apply to the FastAPI app.

## Testing Strategy
- Save raw API responses as JSON fixtures in `tests/fixtures/`.
- Unit test all `data/` and `analysis/` functions against fixtures — no framework dependency, straightforward to test.
- Test `cache.py` read/write/append/delta logic explicitly with known dataframes.
- Do not make live API calls in tests.
- Run with `python -m pytest tests/`.

## Running Locally

### FastAPI app (current)
```bash
pip install -r requirements-web.txt
uvicorn web.main:app --reload
```

### Streamlit prototype (legacy, being torn down)
```bash
pip install -r requirements.txt
streamlit run app.py
```

See `RUNNING.md` for full first-time setup and subsequent-run instructions (venv, ngrok, Yahoo OAuth).

## Development Workflow
- Make changes directly in the main working directory (`/Users/carlinleung/personal_dev/fantasy_hockey`). **Do not use git worktrees** unless explicitly asked.

## Key Decisions Log
See `docs/DECISIONS.md` for the newest-first decisions log, including the 2026-04-10 stack selection (FastAPI + Jinja2 + HTMX + Alpine + Tailwind via CDN, SQLite, Fly.io).

## Out of Scope (for now)
- Trade analysis (deferred — context preserved in `docs/backlog.md`)
- Multi-season historical data
- Push notifications or scheduling
- Native mobile apps (responsive web only — see `docs/DECISIONS.md` 2026-04-10)

Note: multi-user deployment is **no longer** out of scope — per-user cache storage and deployment configuration are tracked on `docs/ROADMAP.md`.
