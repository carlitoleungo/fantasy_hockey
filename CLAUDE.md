# Fantasy Hockey Manager Tool

## Project Purpose
A public-facing web app that helps fantasy hockey managers evaluate waiver wire add/drop decisions using Yahoo Fantasy API data. Users authenticate with their own Yahoo account; the backend fetches their league, matchup, and player data; the frontend renders stat tables and rankings. A demo mode lets unauthenticated users explore a pre-snapshotted dataset.

## Key Documentation
- Yahoo Fantasy Sports API (official): https://developer.yahoo.com/fantasysports/guide/#player-resource
- Yahoo Fantasy API (better structured): https://yahoo-fantasy-node-docs.vercel.app/resource/player/stats
- Improvements backlog: docs/improvements.md

Auth flow and API patterns are established in `auth/oauth.py` and `data/client.py` — read those as the reference implementation, not the notebook.

## Architecture

See `docs/ARCHITECTURE.md` for directory structure and layer rules.

## Tech Stack

See `docs/ARCHITECTURE.md` for stack decisions.

## Caching Strategy

### What gets cached and how

| Data | Location | Refresh strategy |
|---|---|---|
| Historical weekly scores | .cache/{league_key}/matchups.parquet | Incremental — only fetch weeks newer than last_updated |
| Player season stats | .cache/{league_key}/players.parquet | Daily — refresh if last_updated > 24 hours ago |
| Player last-30-day stats | .cache/{league_key}/players.parquet | Daily — refresh if last_updated > 24 hours ago |
| Available (waiver) players | Never cached | Always fetch live — changes constantly |
| League/team metadata | .cache/{league_key}/league_meta.parquet | Fetch once per session, rarely changes mid-season |

### cache.py responsibilities
- `read(league_key, data_type)` — load a parquet file, return dataframe or None if not found
- `write(league_key, data_type, df)` — write/overwrite a parquet file, update last_updated.json
- `append(league_key, data_type, df)` — append new rows to existing parquet file
- `last_updated(league_key, data_type)` — return datetime of last write, or None
- `is_stale(league_key, data_type, max_age_hours)` — return True if cache is older than threshold

### Delta fetch pattern
matchups.py should use this pattern:
1. Call cache.last_updated() to find the most recent week stored locally
2. Fetch only weeks newer than that from the API
3. Append new rows with cache.append()
4. Return the full dataset from cache.read()

On first run with an empty cache, this fetches all weeks. On subsequent runs it fetches only the latest week (or nothing, if already current).

### Cache files are gitignored
Add .cache/ to .gitignore. Cache files contain league-specific data and can always be regenerated from the API.

## Secrets & Auth
- Yahoo OAuth credentials stored in .streamlit/secrets.toml (gitignored)
- Access via `st.secrets["yahoo"]["client_id"]` etc.
- Never hardcode credentials or commit secrets files
- Token refresh should be handled transparently — users should not need to re-auth mid-session

```toml
[yahoo]
client_id = "your_client_id"
client_secret = "your_client_secret"
```

## API Notes
- Yahoo Fantasy API uses OAuth 1.0a
- Rate limits apply — the cache layer is the primary defence against hitting them
- **Minimise API calls**: always prefer bulk/collection endpoints over per-entity calls. For example, use `/league/{key}/teams/stats;type=week;week={w}` (1 call for all teams) instead of N individual `/team/{key}/stats` calls. When adding new data fetches, check whether a collection endpoint exists before defaulting to a per-item loop.
- Weekly data is keyed by week number within a season
- Player stats endpoints differ for season aggregate vs recent (check docs links above)
- The API returns XML by default; use format=json query param where supported

## Known Gotchas
- Streamlit reruns the entire script on every interaction — expensive operations must be wrapped in @st.cache_data or guarded with session state checks
- OAuth redirect URIs must be registered in the Yahoo developer console — localhost and any deployed URL must be registered separately (default Streamlit port is 8501)
- When a Yahoo API response collection has exactly 1 item, xmltodict returns a dict instead of a list. Always check `@count` and wrap in a list when needed
- `stat['value']` from Yahoo API can be `'-'` (player didn't play) or `None` — coerce to 0
- `stat_id == '0'` is games played; `stat_id in ['22', '23']` are GA/GAA — handle these specially in per-game calculations
- `is_only_display_stat == '1'` marks non-scoring stats; filter these out using `is_enabled`

## Testing Strategy
- Save raw API responses as JSON fixtures in tests/fixtures/
- Unit test all data/ and analysis/ functions against fixtures — no Streamlit dependency, straightforward to test
- Test cache.py read/write/append/delta logic explicitly with known dataframes
- Do not make live API calls in tests

## Running Locally

### Streamlit prototype
```bash
pip install -r requirements.txt
streamlit run app.py
```

### FastAPI app
```bash
pip install -r requirements-web.txt
uvicorn web.main:app --reload
```

## Development Workflow
- Make changes directly in the main working directory (`/Users/carlin/dev/fantasy_hockey`). **Do not use git worktrees** unless explicitly asked.

## Key Decisions Log
See `docs/decisions.md` for historical implementation decisions.

## Out of Scope (for now)
- User accounts or multi-user support (single user, local use only)
- Deployment to a hosted service (run locally for now)
- Trade analysis
- Multi-season historical data
- Push notifications or scheduling