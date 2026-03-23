# Fantasy Hockey Manager Tool

## Project Purpose
A Streamlit web app that helps fantasy hockey managers make better add/drop decisions by surfacing team weaknesses and ranking available waiver wire players against those weaknesses.

## Key Documentation
- Yahoo Fantasy Sports API (official): https://developer.yahoo.com/fantasysports/guide/#player-resource
- Yahoo Fantasy API (better structured): https://yahoo-fantasy-node-docs.vercel.app/resource/player/stats
- Existing working notebook: reference/waiver_wire_notebook.ipynb
- Streamlit docs: https://docs.streamlit.io
- Streamlit session state: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
- Improvements backlog: docs/improvements.md

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
- **Minimise API calls**: always prefer bulk/collection endpoints over per-entity calls. For example, use `/league/{key}/teams/stats;type=week;week={w}` (1 call for all teams) instead of N individual `/team/{key}/stats` calls. When adding new data fetches, check whether a collection endpoint exists before defaulting to a per-item loop.
- Weekly data is keyed by week number within a season
- Player stats endpoints differ for season aggregate vs recent (check docs links above)
- The API returns XML by default; use format=json query param where supported

## Known Gotchas
- Streamlit reruns the entire script on every interaction — expensive operations must be wrapped in @st.cache_data or guarded with session state checks
- OAuth redirect URIs must be registered in the Yahoo developer console — localhost and any deployed URL must be registered separately (default Streamlit port is 8501)
- There are two separate caching layers: @st.cache_data (in-session, in-memory) and .cache/ parquet files (cross-session, on-disk). Keep these concerns separate in the code
- When a Yahoo API response collection has exactly 1 item, xmltodict returns a dict instead of a list. Always check `@count` and wrap in a list when needed
- `stat['value']` from Yahoo API can be `'-'` (player didn't play) or `None` — coerce to 0
- `stat_id == '0'` is games played; `stat_id in ['22', '23']` are GA/GAA — handle these specially in per-game calculations
- `is_only_display_stat == '1'` marks non-scoring stats; filter these out using `is_enabled`

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

## Development Workflow
- Make changes directly in the main working directory (`/Users/carlin/dev/fantasy_hockey`). **Do not use git worktrees** unless explicitly asked — the user runs the app from the main directory and can't easily test changes made in a worktree branch.

## Key Decisions Log

### Auth: yahoo_oauth not used for the OAuth flow (2026-03-03)
`yahoo_oauth`'s `OAuth2` class assumes interactive terminal input — it opens a browser and waits for the user to paste an authorisation code. Streamlit uses a redirect-based callback: Yahoo sends the user back to `http://localhost:8501/?code=...`. These are incompatible. The auth flow is implemented directly with `requests` instead. The notebook's core pattern (check validity → refresh if needed → return authenticated session) is preserved in `auth/oauth.py`.

### Auth: tokens stored in .streamlit/oauth_token.json, not secrets.toml (2026-03-03)
Credentials (client_id, client_secret) live in `.streamlit/secrets.toml` as static config. Tokens (access_token, refresh_token, expires_at) are written to `.streamlit/oauth_token.json` at runtime. Writing dynamic tokens back into secrets.toml would mix static config with mutable state and require TOML parsing. Both files are gitignored. The token file format mirrors what yahoo_oauth would produce for compatibility.

### Auth: session state key is "tokens" (dict), not "token" (2026-03-03)
The full token payload (access_token, refresh_token, expires_at, etc.) is stored under `st.session_state["tokens"]`. Page auth guards should check `"tokens" not in st.session_state`. The CLAUDE.md template showing `"token"` (singular) referred to the concept, not a literal key name.

### Auth: get_session() is the single interface for authenticated API calls (2026-03-03)
All data/ layer code should call `auth.oauth.get_session()` to get a `requests.Session` with the Bearer token header already set. This function handles loading from session state, falling back to disk, and refreshing transparently. Nothing outside auth/ should touch token storage directly.

### client.py: unknown and display-only stats silently skipped (2026-03-03)
The notebook emitted `"Unknown Stat ID: 22"` columns for unrecognised stat IDs and relied on the caller to drop them (`df.drop(columns=['Unknown Stat ID: 22'])`). `client.get_team_week_stats()` instead silently ignores any stat not in the enabled categories lookup. This keeps the DataFrame clean without requiring callers to know which IDs to drop.

### client.py: _as_list() handles the single-item xmltodict gotcha centrally (2026-03-03)
Rather than scattering `if int(@count) == 1` checks (as the notebook did for teams), a single `_as_list(value)` helper normalises any dict-or-list value to always be a list. Used on: the stat categories list, `stat_position_type` (which can be a list when a stat applies to multiple position types), the teams list, and the per-week stat list.

### matchups.py: delta fetch uses max(week) from cache data, not last_updated timestamp (2026-03-03)
`cache.last_updated()` returns when something was written (a datetime), not which weeks are present. For the delta fetch pattern, what matters is which week numbers exist in the data. `_last_cached_week()` reads `df['week'].max()` from the cached parquet file. `cache.last_updated()` / `cache.is_stale()` are reserved for time-based staleness checks (e.g. player stats refreshed daily).

### matchups.py: current week is included in delta fetch; won't refresh mid-week (2026-03-03)
`get_matchups()` fetches up to and including `current_week`. Once that week is cached, the next call finds `last_cached_week == current_week` and fetches nothing new until Yahoo advances `current_week`. Intra-week stat updates are therefore not reflected until the cache is manually cleared. This is acceptable for a daily-use tool; a `force_refresh` flag can be added later if needed.

### leagues.py: patch target is data.leagues._get, not data.client._get (2026-03-03)
`leagues.py` imports `_get` directly via `from data.client import _get`. This binds the name in `leagues.py`'s own namespace, so patching `data.client._get` in tests has no effect. Tests for `leagues.py` must patch `data.leagues._get`. The same rule applies to any future module that imports `_get` (or other helpers) by name from `data.client` — always patch the name in the importing module's namespace.

### leagues.py: get_user_hockey_leagues() filters by game code, not game name (2026-03-03)
The Yahoo games endpoint returns a `code` field (e.g. `"nhl"`, `"mlb"`) that is stable across seasons. `get_user_hockey_leagues()` filters on `game_code == "nhl"`. The human-readable `name` field ("Yahoo Fantasy Hockey") is not used for filtering as it could change.

### team_scores.py: avg_ranks uses method='min' for ties (2026-03-03)
When two teams score identically on a stat in the same week, both receive the lower (better) rank and the next rank is skipped. This matches standard sports ranking convention (two teams tied for 1st → both rank 1, next team ranks 3rd).

### team_scores.py: LOWER_IS_BETTER covers both full name and abbreviation (2026-03-03)
Yahoo stat column names in the matchups DataFrame are the full `stat_name` strings returned by the API (e.g. "Goals Against Average"), not abbreviations. `LOWER_IS_BETTER` includes both the full names and common abbreviations ("GA", "GAA") for defensive breadth. If a league uses non-standard stat names, callers can pass an explicit `lower_is_better` set to `avg_ranks()`.

### pages/: matchups loaded once per session via session state, not @st.cache_data (2026-03-03)
`@st.cache_data` can't safely call `get_session()` because that function reads `st.session_state`, which is not available in cached function contexts. Instead, pages load data once per session by guarding with `"matchups_df" not in st.session_state` (invalidated if the league changes). `@st.cache_data` is reserved for pure computations that don't touch session state or the API — e.g. `_compute_avg_ranks(df)` in `01_league_overview.py`.

### client.py: bulk teams/stats endpoint replaces per-team fetching (2026-03-23)
`get_all_teams_week_stats()` uses `/league/{key}/teams/stats;type=week;week={w}` to fetch every team's stats for a week in a single API call. This replaces the previous pattern of calling `get_team_week_stats()` once per team per week. For a 12-team league over 20 weeks, this reduces API calls from ~240 to ~20 (plus setup calls). `matchups.py` now uses this bulk endpoint exclusively. The per-team `get_team_week_stats()` is retained in `client.py` for cases where only one team's stats are needed.

### client.py: _coerce() handles None values, not just '-' (2026-03-23)
The Yahoo API can return `None` for stat values (not just the string `'-'`). `_coerce()` and the `games_played` handler now treat `None` identically to `'-'` — coerced to 0. This fixes the `float() argument must be a string or a real number, not 'NoneType'` error on the league overview page.

### Notebook dead ends: do not port (2026-03-03)
The following notebook sections are explicitly marked dead ends or are broken and should not be ported without explicit confirmation:
- "Get matchups for matchup analyser" — incomplete implementation
- "Get rosters and player stats per roster" — has a variable-shadowing bug, extremely slow (1 API call per player)
- "Calculating expected stats" — uses deprecated `statsapi.web.nhl.com` URL and removed `df.append()` API
- "Player Roster & Stats Testing Grounds" — unfinished pagination experiments

## Out of Scope (for now)
- User accounts or multi-user support (single user, local use only)
- Deployment to a hosted service (run locally for now)
- Trade analysis
- Multi-season historical data
- Push notifications or scheduling