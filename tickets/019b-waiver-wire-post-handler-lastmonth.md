# 019b — Waiver Wire: Last-30 branching and games remaining

## Status
blocked

## Type
feature

## Touches
- `web/routes/waiver.py`
- `web/templates/waiver/_table.html`
- `tests/test_waiver.py`

## Why
The "Last 30 days" radio on the waiver wire page is disabled after 019a ships. Users
want to evaluate players on recent form, not just season totals — a player who is hot
in the last month is a better add than one coasting on an early-season burst. This
ticket makes the radio functional: it fetches recent stats, joins them to season
metadata, adds a games-remaining column so managers can see schedule strength, and
updates the fragment footer. When lastmonth data is unavailable, the table gracefully
falls back to season stats.

## Acceptance criteria
- [ ] `POST /api/waiver/players` with `period="Last 30 days"` and at least one stat
  returns 200 HTML with a `games_played` column and footer reading "last 30 days stats".
- [ ] `POST /api/waiver/players` with `period="Season"` renders identically to 019a:
  no GP column, no games-remaining column, footer reads "season stats".
- [ ] `POST /demo/api/waiver/players` with `period="Last 30 days"` returns 200 HTML
  with a games-remaining column; no Yahoo API calls and no cache writes occur.
- [ ] When `get_matchups` returns None or the games-remaining fetch throws, the table
  still renders with `games_remaining == 0` for all players; no 500.
- [ ] When `lm_pool` is empty after both cache read and fetch, `base_df` falls back to
  `season_pool` and the table renders with season stats; no 500.

## Out of scope
- Changes to the season path — the 019a season branch is unchanged.
- Caching `games_remaining_map` across requests (noted as future improvement in
  `docs/improvements.md` if worth capturing).
- Any changes to `data/`, `analysis/`, or `auth/` layers.

## Notes for the Engineer

**Remove the Last 30 days disable from 019a.** 019a adds a `disabled` attribute or
tooltip to the radio. Remove it here so the radio is fully interactive.

**Period branching — lastmonth path:**
1. Collect `pool_keys = set(season_pool["player_key"])`.
2. If `not cache.is_lastmonth_stale(league_key)`: call `cache.read_lastmonth_cache(league_key)`;
   filter to `pool_keys` to build initial `lm_pool`; derive `missing_keys`.
3. If `missing_keys` non-empty: call `fetch_lastmonth_batch(session, list(missing_keys),
   id_to_name)`; if non-empty, call `cache.upsert_lastmonth_cache(league_key, new_lm)`
   and merge into `lm_pool` via `_merge_pool` (same function from 019a — do not copy it).
4. If `lm_pool` empty: fall back — `base_df = season_pool`.
5. Otherwise:
   ```python
   meta_cols = ["player_key", "player_name", "team_abbr", "display_position", "status"]
   season_meta = season_pool[[c for c in meta_cols if c in season_pool.columns]]
   base_df = season_meta.merge(lm_pool, on="player_key", how="inner")
   ```
Cache functions must not be mixed across paths: season path uses `is_player_pool_stale` /
`read_player_pool` / `write_player_pool`; lastmonth path uses `is_lastmonth_stale` /
`read_lastmonth_cache` / `upsert_lastmonth_cache`.

**GAA recomputation.** `stat_id == '23'` is GAA. Yahoo returns season GAA for
`type=lastmonth` queries. Verify `fetch_lastmonth_batch` recomputes it from GA / GP
(`data/players.py` lines 289–293) before assuming `lm_pool` GAA values are correct.

**Games remaining — date type mismatch.** `get_current_matchup` returns `week_start` /
`week_end` as strings. `get_remaining_games` expects `datetime.date`. Always convert:
```python
from datetime import date
from_date = date.fromisoformat(matchup["week_start"])
to_date   = date.fromisoformat(matchup["week_end"])
```

**Games remaining — fetch flow:**
1. `matchups_df = get_matchups(...)` (disk cache hit). If None or empty, skip entirely
   (`games_remaining_map = {}`).
2. `current_week = int(matchups_df["week"].max())`.
3. `scoreboard.get_current_matchup(session, league_key, current_week)` → `matchup` dict.
4. `schedule.get_remaining_games(team_abbrs, from_date, to_date)` where `team_abbrs` is
   `ranked_df["team_abbr"].unique().tolist()`.
5. `ranked_df["games_remaining"] = ranked_df["team_abbr"].map(lambda a: games_remaining_map.get(a, 0))`.
6. Entire block wrapped in `try/except`; on any error, `games_remaining_map = {}`.

**Template updates.** `games_remaining` column appears after the player name column when
`period == "Last 30 days"`, format integer (`{int(v)}`) or `—` for NaN. `games_played`
column appears when `period == "Last 30 days"` and `games_played` is in `ranked_df`,
format integer. Footer left side: "last 30 days stats" when `period == "Last 30 days"`.

**Demo mode.** When `demo=True` and `period == "Last 30 days"`: use
`demo_module.load_lastmonth_pool()` as `lm_pool` and `demo_module.get_games_remaining()`
as `games_remaining_map`. No cache or Yahoo calls.

## Verification
1. `POST /api/waiver/players` with `period="Last 30 days"` and `stats=["Goals"]` —
   response contains a `games_played` column and footer reads "last 30 days stats".
2. `POST /api/waiver/players` with `period="Season"` — fragment unchanged from 019a:
   no GP column, no games-remaining, footer reads "season stats".
3. `POST /demo/api/waiver/players` with `period="Last 30 days"` — 200 HTML; confirm
   no cache writes and no live Yahoo calls (check logs or mock).
4. Mock `get_matchups` to return None → table renders; all `games_remaining == 0`; no 500.
5. Mock `get_current_matchup` to raise → same fallback as above.
6. Mock both cache read and `fetch_lastmonth_batch` to return empty DataFrames → table
   renders season stats (fallback); no 500.
7. Edge: player in `season_pool` absent from both lastmonth cache and fetch → that player
   is excluded from the inner join and does not appear in the Last 30 days table.
8. Edge: GAA column in `lm_pool` — confirm values are recomputed (GA / GP), not raw
   season GAA. Compare against Streamlit prototype output for the same player.
9. Manual: select "Last 30 days" radio → table re-renders with GP column and updated
   footer. Switch back to "Season" → GP column disappears.

## Dependencies
- Ticket 019a must be complete: `POST /api/waiver/players` and `_table.html` exist;
  `_merge_pool` and `_waiver_post_impl` are in place; season path is fully functional.
