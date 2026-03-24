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

### Fetching available players: sort + paginate
The API supports `status=A` (available/unrostered) and `sort=OR` (overall rank). Use:

```
/league/{key}/players;status=A;sort=OR;start={n};out=stats;stats_type={type}
```

Fetch pages of 25 until we have enough depth (target: ~100 players, i.e. 4 pages). Stop early if the last player on a page has an overall rank much worse than the top of the list (configurable threshold). Available players change constantly — never cache this response.

The `out=stats` param returns season stats inline, avoiding a second API call per player.

### 30-day stats
The Yahoo API supports `type=lastmonth` for the `stats_type` param (equivalent to "last 30 days"). Season stats use `type=season`. The notebook's `sort=60` (60-day sort) is a sort key, not a stats type — don't conflate the two.

For the toggle between "season" and "recent" ranking, fetch both stat types upfront and swap the source DataFrame on toggle. Two API calls on page load (once per session), not per interaction.

### Team context: deferred
The idea of pre-highlighting which categories the user's team is weak in (to guide the multi-select) is explicitly out of scope for this iteration. The multi-select is purely manual. Revisit later.

## Files to create

### `data/players.py`
Fetches available player lists and their stats. No Streamlit dependencies.

```python
def get_available_players(session, league_key, stats_type="season", max_players=100) -> list[dict]:
    """
    Fetch available (unrostered) players sorted by overall rank.
    stats_type: "season" | "lastmonth"
    Returns a list of flat dicts with player metadata + stat values.
    """
```

Each player dict should include:
- `player_key`, `player_name`, `team_abbr`, `display_position`, `status` (injury flag if any)
- One key per enabled stat category (float, coerced same as team stats)

Pagination: loop `start=0, 25, 50, 75` until `max_players` reached or API returns fewer than 25 results.

Use `_as_list()` and `_coerce()` from `data/client.py`. Import `_get` from there too (or move to a shared helper — check what's cleanest).

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

# Load players once per session (two fetches: season + lastmonth)
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
# Available players with season stats, sorted by overall rank, page 1
/league/{key}/players;status=A;sort=OR;start=0;out=stats;stats_type=season

# Same but last-30-day stats
/league/{key}/players;status=A;sort=OR;start=0;out=stats;stats_type=lastmonth

# Next page
/league/{key}/players;status=A;sort=OR;start=25;out=stats;stats_type=season
```

These endpoints are not in the existing `data/client.py` — they need to be added to `data/players.py` rather than bolting onto `client.py`, which currently only handles team-level data.

## What to verify first (before building)

- [ ] Confirm `stats_type=lastmonth` returns the right data (vs. `type=lastweek` etc.) — test with a known player
- [ ] Confirm `out=stats` actually includes stat values inline in the players response
- [ ] Confirm `status=A` correctly filters to only unrostered players
- [ ] Check what `display_position` looks like in the response for multi-position players (e.g. `"C,LW"`)
- [ ] Confirm page size is 25 and `start` is 0-indexed

## Out of scope for this iteration
- Team weakness context (pre-highlighting weak categories)
- Caching available players (always live by design)
- Per-player detail view or drill-down
- Comparison against a specific rostered player (add/drop trade-off view)
