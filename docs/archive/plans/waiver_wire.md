> **Archived — Streamlit prototype only.** This plan was written and implemented for the original Streamlit prototype. The data layer it describes (`data/players.py`, `analysis/waiver_ranking.py`) is preserved and unchanged. The UI layer (`pages/03_waiver_wire.py`) is being replaced by `web/routes/waiver.py` + Jinja2 templates. The API endpoint research, two-call-per-page pattern, and ranking approach documented here all remain valid and should be referenced when building the FastAPI waiver route. See [`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md) for the current architecture.

---

# Plan: Waiver Wire Player Ranking (Features 5 & 6)

## What we're building

A page (`pages/03_waiver_wire.py`) where the user can:
1. Select stat categories they want to improve
2. Optionally filter by player position
3. See available (unrostered) players ranked by how well they perform in the selected categories
4. Toggle between season and last-30-day ranking

## Design decisions

### Ranking method: composite rank score
Raw stat values can't be summed across categories because they're on different scales (e.g. Goals ≈ 0–2 per game, Shots on Goal ≈ 0–10). Instead:

1. For each selected category, rank all fetched players (1 = best)
2. Sum the per-category ranks to get a composite score
3. Sort ascending — lower composite = better overall fit

This is the same approach `analysis/team_scores.py` uses for team ranking. Reuse `LOWER_IS_BETTER` logic there for goalie stats (GAA, GA).

### Position filtering
Position filtering is essential for real add/drop decisions (you can only drop for a comparable roster slot). The Yahoo API returns a `display_position` field per player (e.g. `"C,LW"`, `"D"`, `"G"`). Filter client-side after fetching.

UI should offer:
- All positions (default)
- Skaters (F + D)
- Forwards only (C, LW, RW, F)
- Defensemen only (D)
- Goalies only (G)
- Individual position checkboxes as a stretch goal

### Fetching available players: two calls per page

`out=stats` on the league players endpoint **always returns season stats** regardless of
`sort_type`. This was confirmed via validate_api.py: Morgan Geekie showed 34 goals
season, 2 goals lastmonth — the inline stats never changed.

The correct parameter for lastmonth stats is `type=lastmonth` on the individual
`/player/{key}/stats` endpoint (not `date=lastmonth` or `week=lastmonth`, both of which
return season totals).

**Two-call pattern per page:**

1. Fetch player list with season stats inline:
   ```
   /leagues;league_keys={key}/players;status=A;sort=OR;sort_type=season;out=stats;start={n};count=25
   ```
   → yields player keys, metadata, and season stat values

2. Fetch lastmonth stats for the same player keys as a batch:
   ```
   /players;player_keys={key1,key2,...}/stats;type=lastmonth
   ```
   → yields lastmonth stat values to merge with step 1

   **Note:** The batch form of this call (`player_keys=...`) still needs to be confirmed
   working. If it doesn't, fall back to individual `/player/{key}/stats;type=lastmonth`
   calls — but that's 25 calls per page and too slow for production use.

Fetch 4 pages (100 players total). Stop when `players_node is None` (confirmed behaviour
at end of results). Available players change constantly — never cache this response.

### 30-day stats — confirmed working
- `type=lastmonth` on `/player/{key}/stats` returns the last 30 days ✓
- `date=lastmonth` returns season totals (wrong)
- `week=lastmonth` returns season totals (wrong)
- `out=stats` inline on the league players endpoint always returns season totals (wrong)
- `sort_type=lastmonth` controls player ordering only, not what stats are returned

For the toggle between "season" and "recent" ranking: store both DataFrames in session
state on page load, swap the source on toggle. The fetch happens once per session.

### Team context: deferred
The idea of pre-highlighting which categories the user's team is weak in (to guide the
multi-select) is explicitly out of scope for this iteration. The multi-select is purely
manual. Revisit later.

## Files to create

### `data/players.py`
Fetches available player lists and their stats. No Streamlit dependencies.

```python
def get_available_players(session, league_key, max_players=100) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch available (unrostered) players and return (season_df, lastmonth_df).

    Each DataFrame has the same rows (players) with columns:
        player_key, player_name, team_abbr, display_position, status,
        <stat_name...>  (float, coerced — one col per enabled scoring category)

    Two API calls per page of 25:
      1. League players endpoint (season stats inline)
      2. /players;player_keys={keys}/stats;type=lastmonth (lastmonth stats)
    """
```

Pagination: loop `start=0, 25, 50, ...` until `max_players` reached or `players_node is None`.

Use `_as_list()`, `_coerce()`, and `_get` from `data/client.py`.

Stat names should match the enabled stat categories from `get_stat_categories()` so column
names are consistent with the matchups DataFrame used elsewhere.

### `analysis/waiver_ranking.py`
Pure pandas — no API calls, no Streamlit.

```python
def rank_players(
    df: pd.DataFrame,
    selected_categories: list[str],
    lower_is_better: frozenset[str] | None = None,
) -> pd.DataFrame:
    """
    Add a composite_rank column based on per-category ranks across selected_categories.
    Returns df sorted ascending by composite_rank.
    """
```

- Reuse `LOWER_IS_BETTER` from `analysis/team_scores.py` (import it, don't duplicate)
- If `selected_categories` is empty, return df unsorted with `composite_rank = None`
- Position filtering happens in the page layer before calling this function

### `pages/03_waiver_wire.py`
UI only. Follows the same session state pattern as `01_league_overview.py` and `02_matchup_sim.py`.

```python
# Auth guard
if "tokens" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()

# Load players once per session (two DataFrames: season + lastmonth)
if "players_season" not in st.session_state:
    ...fetch and store both DataFrames...

# Controls
position_filter = st.selectbox("Position", [...])
selected_cats = st.multiselect("Stat categories to improve", stat_columns)
ranking_period = st.radio("Rank by", ["Season", "Last 30 days"])

# Ranking
df = players_season or players_lastmonth depending on toggle
df = filter_by_position(df, position_filter)
ranked = rank_players(df, selected_cats)
st.dataframe(ranked)
```

Display columns: player name, team, position, selected stat values + composite rank. Hide unselected stat columns by default but allow expansion.

## API endpoint reference

```
# Page 1: available players with season stats inline, sorted by overall rank
/leagues;league_keys={key}/players;status=A;sort=OR;sort_type=season;out=stats;start=0;count=25

# Page 2, 3, ...
/leagues;league_keys={key}/players;status=A;sort=OR;sort_type=season;out=stats;start=25;count=25

# Lastmonth stats for a batch of player keys (to be confirmed working in batch form)
/players;player_keys={key1},{key2},...,{keyN}/stats;type=lastmonth

# Fallback: individual player lastmonth stats (confirmed working, but slow at scale)
/player/{key}/stats;type=lastmonth
```

Note: the league players URL uses the plural form (`/leagues;league_keys=`) not
`/league/{key}/players` — this is what validate_api.py tested and confirmed working.

## What to verify before building

- [x] `sort=OR` works on the league players endpoint
- [x] `out=stats` returns season stat values inline
- [x] `status=A` filters to available players
- [x] `position=F/D/G` filtering works
- [x] Pagination: `players_node is None` at end of results
- [x] `type=lastmonth` on `/player/{key}/stats` returns lastmonth stats
- [x] `/players;player_keys={keys}/stats;type=lastmonth` works as a **batch** call

## Out of scope for this iteration
- Team weakness context (pre-highlighting weak categories)
- Caching available players (always live by design)
- Per-player detail view or drill-down
- Comparison against a specific rostered player (add/drop trade-off view)
