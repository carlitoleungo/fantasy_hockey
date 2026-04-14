# Key Decisions Log — Streamlit Prototype

> **Archived — Streamlit prototype only.** These decisions describe implementation choices made for the original Streamlit prototype. They are preserved for historical context but do not apply to the current FastAPI stack. The session state patterns, token storage approach, and page structure described here have all been superseded. See [`docs/decisions.md`](../decisions.md) for decisions that apply to the current stack, and [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) for the current architecture.

---

### Auth: tokens stored in .streamlit/oauth_token.json, not secrets.toml (2026-03-03)
Credentials (client_id, client_secret) live in `.streamlit/secrets.toml` as static config. Tokens (access_token, refresh_token, expires_at) are written to `.streamlit/oauth_token.json` at runtime. Writing dynamic tokens back into secrets.toml would mix static config with mutable state and require TOML parsing. Both files are gitignored. The token file format mirrors what yahoo_oauth would produce for compatibility.

*Superseded by: SQLite `user_sessions` table (ticket 004a/004b). Tokens now stored server-side in the DB; credentials read from `os.environ`.*

### Auth: session state key is "tokens" (dict), not "token" (2026-03-03)
The full token payload (access_token, refresh_token, expires_at, etc.) is stored under `st.session_state["tokens"]`. Page auth guards should check `"tokens" not in st.session_state`. The CLAUDE.md template showing `"token"` (singular) referred to the concept, not a literal key name.

*Superseded by: `session_id` cookie + `user_sessions` DB table (ticket 004b). Token dict no longer stored in session state.*

### Auth: get_session() is the single interface for authenticated API calls (2026-03-03)
All data/ layer code should call `auth.oauth.get_session()` to get a `requests.Session` with the Bearer token header already set. This function handles loading from session state, falling back to disk, and refreshing transparently. Nothing outside auth/ should touch token storage directly.

*Superseded by: `get_session()` is removed from `auth/oauth.py` in ticket 004a. Route handlers build the session from tokens retrieved via `require_user` middleware (ticket 005).*

### pages/: matchups loaded once per session via session state, not @st.cache_data (2026-03-03)
`@st.cache_data` can't safely call `get_session()` because that function reads `st.session_state`, which is not available in cached function contexts. Instead, pages load data once per session by guarding with `"matchups_df" not in st.session_state` (invalidated if the league changes). `@st.cache_data` is reserved for pure computations that don't touch session state or the API — e.g. `_compute_avg_ranks(df)` in `01_league_overview.py`.

*Superseded by: FastAPI route handlers call data/ functions directly; HTTP cache headers and FastAPI dependencies replace `@st.cache_data` and session state guards.*

### pages/03_waiver_wire.py: player fetch deferred until categories are selected (2026-03-23)
Player data (8 API calls) is not fetched on page load. The fetch triggers only once the user has selected at least one stat category, then caches both DataFrames in session state for the rest of the session. An empty state message is shown before any selection. This avoids unnecessary API calls for a view that wouldn't be useful without categories selected anyway.

*Note for new stack: the deferred-fetch rationale still applies — consider an equivalent lazy-load pattern in the FastAPI/HTMX waiver route.*

### pages/03_waiver_wire.py: table shows stat values, not per-category ranks (2026-03-23)
The waiver wire table shows raw stat values for selected categories alongside `composite_rank` (the sum of per-category ranks). Individual per-category ranks are internal to `rank_players()` and not surfaced in the UI. This keeps the table readable and gives the user the actual numbers to reason about.

### pages/03_waiver_wire.py: category multi-select shows all scoring stats (2026-03-23)
The multi-select always shows all enabled scoring categories regardless of the position filter. No position-aware filtering of the category list. Simplest approach — revisit if the UX feels cluttered.

### pages/03_waiver_wire.py: selected-only columns with "Show all stats" checkbox (2026-03-23)
The table shows metadata + selected stat columns + composite_rank by default. A "Show all stats" checkbox reveals all stat columns. Keeps the table focused on the user's decision without hiding data entirely.
