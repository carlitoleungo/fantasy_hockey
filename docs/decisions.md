# Key Decisions Log

Historical implementation decisions. Read this file when you need context on *why* something was done a particular way.

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

### players.py: type=lastmonth is the correct param for last-30-day player stats (2026-03-23)
Confirmed via validate_api.py against a live league. `date=lastmonth` and `week=lastmonth` both return season totals. `out=stats` on the league players collection endpoint also always returns season totals regardless of `sort_type`. Only `/player/{key}/stats;type=lastmonth` (and the batch form `/players;player_keys={keys}/stats;type=lastmonth`) returns the last 30 days.

### players.py: two API calls per page of 25 players (2026-03-23)
`get_available_players()` uses a two-call-per-page pattern:
1. `/leagues;league_keys={key}/players;status=A;sort=OR;sort_type=season;out=stats;start={n};count=25` — player list with season stats inline and player keys
2. `/players;player_keys={keys}/stats;type=lastmonth` — batch lastmonth stats for those same keys

This gives both stat periods in 2 API calls per page (8 total for 100 players) instead of 1+N. The batch lastmonth call returns `{player_key: stats}` only — no metadata — so metadata is taken from the season response and re-attached by the caller.

### players.py: imports private helpers from data/client.py (2026-03-23)
`data/players.py` imports `_get`, `_as_list`, `_coerce`, and `BASE_URL` directly from `data/client.py`. These are intentionally shared across the data layer. The same patch-target rule applies: tests for `players.py` must patch `data.players._get`, not `data.client._get`.

### pages/03_waiver_wire.py: player fetch deferred until categories are selected (2026-03-23)
Player data (8 API calls) is not fetched on page load. The fetch triggers only once the user has selected at least one stat category, then caches both DataFrames in session state for the rest of the session. An empty state message is shown before any selection. This avoids unnecessary API calls for a view that wouldn't be useful without categories selected anyway.

### pages/03_waiver_wire.py: table shows stat values, not per-category ranks (2026-03-23)
The waiver wire table shows raw stat values for selected categories alongside `composite_rank` (the sum of per-category ranks). Individual per-category ranks are internal to `rank_players()` and not surfaced in the UI. This keeps the table readable and gives the user the actual numbers to reason about.

### pages/03_waiver_wire.py: category multi-select shows all scoring stats (2026-03-23)
The multi-select always shows all enabled scoring categories regardless of the position filter. No position-aware filtering of the category list. Simplest approach — revisit if the UX feels cluttered.

### pages/03_waiver_wire.py: selected-only columns with "Show all stats" checkbox (2026-03-23)
The table shows metadata + selected stat columns + composite_rank by default. A "Show all stats" checkbox reveals all stat columns. Keeps the table focused on the user's decision without hiding data entirely.

### Notebook dead ends: do not port (2026-03-03)
The following notebook sections are explicitly marked dead ends or are broken and should not be ported without explicit confirmation:
- "Get matchups for matchup analyser" — incomplete implementation
- "Get rosters and player stats per roster" — has a variable-shadowing bug, extremely slow (1 API call per player)
- "Calculating expected stats" — uses deprecated `statsapi.web.nhl.com` URL and removed `df.append()` API
- "Player Roster & Stats Testing Grounds" — unfinished pagination experiments
