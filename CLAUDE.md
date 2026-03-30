# Fantasy Hockey Manager Tool

## Project Purpose
A Streamlit web app that helps fantasy hockey managers make better add/drop decisions by surfacing team weaknesses and ranking available waiver wire players against those weaknesses.

## Key Documentation
- Yahoo Fantasy Sports API (official): https://developer.yahoo.com/fantasysports/guide/#player-resource
- Yahoo Fantasy API (better structured): https://yahoo-fantasy-node-docs.vercel.app/resource/player/stats
- Improvements backlog: docs/improvements.md

Auth flow and API patterns are established in `auth/oauth.py` and `data/client.py` — read those as the reference implementation, not the notebook.

## Architecture

```
fantasy_hockey/
  CLAUDE.md
  app.py                        # Streamlit entry point — run with `streamlit run app.py`
  reference/
    waiver_wire_notebook.ipynb  # read-only reference, do not execute
  auth/
    oauth.py                    # Yahoo OAuth flow, token storage/refresh
  data/
    client.py                   # raw Yahoo API calls, rate limit handling
    cache.py                    # read/write local parquet files, delta fetch logic
    leagues.py                  # fetch games, leagues, return list for selection
    matchups.py                 # fetch matchup data — checks cache first, fetches missing weeks
    players.py                  # fetch available players, season + 30-day stats
  analysis/
    team_scores.py              # weekly scores across all teams, avg rank per team
    matchup_sim.py              # head-to-head simulation using period averages
    waiver_ranking.py           # rank available players by selected stat categories
  pages/
    01_league_overview.py       # weekly team scores view
    02_matchup_sim.py           # head-to-head simulation view
    03_waiver_wire.py           # player ranking view
  tests/
    fixtures/                   # saved API responses for offline testing
  .cache/
    {league_key}/
      matchups.parquet          # all historical matchup data, appended incrementally
      players.parquet           # player stats snapshot
      last_updated.json         # timestamps per data type
```

The data/ and analysis/ layers are pure Python with no Streamlit dependencies — they take inputs and return dataframes. The pages/ layer handles all Streamlit UI code. app.py handles auth state and routes to pages.

Each layer only imports from the layer below it. Streamlit UI code never lives outside of app.py or pages/.

## Tech Stack
- Python 3.11+
- streamlit for the web UI
- yahoo_oauth for OAuth token management
- requests or yahoo_fantasy_api wrapper for API calls (check notebook for what's already working)
- pandas for data transformation
- pyarrow for parquet read/write (comes with pandas)
- pytest for tests

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

## Streamlit-Specific Patterns

### Session State
```python
if "league_key" not in st.session_state:
    st.session_state.league_key = None
```

### In-session Caching
```python
@st.cache_data(ttl=3600)
def get_matchup_data(league_key, week):
    ...
```

`@st.cache_data` is for within-session performance. The `.cache/` parquet files handle persistence across sessions. These are two separate caching layers — do not conflate them.

### Auth Flow
On app load, check for a valid token in session state. If none exists, show a login button that initiates the Yahoo OAuth flow. Once authenticated, store the token in st.session_state and rerun. Never store tokens in st.cache_data — use session state only.

### Page Structure
Guard each page with an auth check at the top:
```python
if "token" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()
```

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
```bash
pip install -r requirements.txt
streamlit run app.py
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