# Fantasy Hockey Manager Tool

## Project Purpose
A Streamlit web app that helps fantasy hockey managers make better add/drop decisions by surfacing team weaknesses and ranking available waiver wire players against those weaknesses.

## Key Documentation
- Yahoo Fantasy Sports API (official): https://developer.yahoo.com/fantasysports/guide/#player-resource
- Yahoo Fantasy API (better structured): https://yahoo-fantasy-node-docs.vercel.app/resource/player/stats
- Existing working notebook: reference/waiver_wire_notebook.ipynb
- Streamlit docs: https://docs.streamlit.io
- Streamlit session state: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state

## What Already Works
The existing notebook handles:
- Yahoo OAuth authentication
- Fetching weekly matchup data from the API
- Transforming that data into a dataframe
- Coverage of all requirements up to and including team score comparison (#4 below)

Before implementing anything new, read reference/waiver_wire_notebook.ipynb and summarise the auth flow and data structures you find there. Reproduce its working patterns rather than inventing new onesm, but also adapt them to best practices for a streamlit app as the original file was written for manual use. Pay particular attention to how OAuth tokens are stored and refreshed, and how the API responses are structured.

Note: the notebook contains some functions labelled as dead ends — experimental work that was never fully implemented. Do not port these without confirming intent first.

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
Use st.session_state to persist data across interactions without re-fetching from disk:

```python
if "league_key" not in st.session_state:
    st.session_state.league_key = None
```

### In-session Caching
Use @st.cache_data for any function that reads from the local cache or does computation, to avoid re-running on every Streamlit interaction within a session:

```python
@st.cache_data(ttl=3600)
def get_matchup_data(league_key, week):
    ...
```

Note: @st.cache_data is for within-session performance. The .cache/ parquet files handle persistence across sessions. These are two separate caching layers — do not conflate them.

### Auth Flow
On app load, check for a valid token in session state. If none exists, show a login button that initiates the Yahoo OAuth flow. Once authenticated, store the token in st.session_state and rerun. Never store tokens in st.cache_data — use session state only.

### Page Structure
Each page in pages/ is a self-contained Streamlit script. Guard each page with an auth check at the top:

```python
if "token" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()
```

## Secrets & Auth
- Yahoo OAuth credentials stored in .streamlit/secrets.toml (gitignored)
- Access in code via st.secrets["yahoo"]["client_id"] etc.
- Never hardcode credentials or commit secrets files
- Token refresh should be handled transparently — users should not need to re-auth mid-session

.streamlit/secrets.toml structure:
```toml
[yahoo]
client_id = "your_client_id"
client_secret = "your_client_secret"
```

## Feature Requirements (in priority order)

### 1. Authentication
- OAuth flow using Yahoo account, initiated from the app homepage
- Token stored in st.session_state for the duration of the session
- Graceful handling of expired tokens with a re-auth prompt

### 2. League Selection
- After login, if the user has multiple Yahoo fantasy games/leagues, show a dropdown to select one
- Store selection in st.session_state so it persists across pages

### 3. Weekly Team Scores (Page 1)
- Week selector (dropdown or slider)
- Table showing all teams' scores for that week
- Average rank per team per scoring category, highlighted to show strengths/weaknesses

### 4. Matchup Simulation (Page 2)
- Dropdowns to select two teams
- Period selector for aggregation (e.g. last 4 weeks, full season, custom range)
- Side-by-side table showing average score per category with win/loss indicators

### 5. Stat Category Selection
- Multi-select widget (on Page 3) for the user to pick categories they want to improve
- Drives the waiver wire ranking below

### 6. Waiver Wire Player Ranking (Page 3)
- Fetch available (unrostered) players (always live — never cached)
- Show season stats and last-30-day stats side by side
- Rank players by performance in selected categories
- Allow user to toggle between season and recent ranking

## API Notes
- Yahoo Fantasy API uses OAuth 1.0a
- Rate limits apply — the cache layer is the primary defence against hitting them
- Weekly data is keyed by week number within a season
- Player stats endpoints differ for season aggregate vs recent (check docs links above)
- The API returns XML by default; use format=json query param where supported

## Known Gotchas
- Streamlit reruns the entire script on every interaction — expensive operations must be wrapped in @st.cache_data or guarded with session state checks
- OAuth redirect URIs must be registered in the Yahoo developer console — localhost and any deployed URL must be registered separately (default Streamlit port is 8501)
- There are two separate caching layers: @st.cache_data (in-session, in-memory) and .cache/ parquet files (cross-session, on-disk). Keep these concerns separate in the code
- [Add more here as you discover them during development]

## Testing Strategy
- Save raw API responses as JSON fixtures in tests/fixtures/
- Unit test all data/ and analysis/ functions against fixtures — these have no Streamlit dependency and are straightforward to test
- Test cache.py read/write/append/delta logic explicitly with known dataframes
- Do not make live API calls in tests
- Streamlit UI logic does not need unit tests — validate it manually

## Running Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Out of Scope (for now)
- User accounts or multi-user support (single user, local use only)
- Deployment to a hosted service (run locally for now)
- Trade analysis
- Multi-season historical data
- Push notifications or scheduling