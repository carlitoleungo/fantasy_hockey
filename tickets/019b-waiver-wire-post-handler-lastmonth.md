# 019b — Waiver Wire: Last-30 branching and games remaining

## Summary
Extends the POST handler from 019a with two features: (1) the Last 30 days stat period —
a second cache/fetch pass for lastmonth data followed by a join on `player_key` to
`season_meta` — and (2) the games-remaining column, derived from
`data.scoreboard.get_current_matchup` and `data.schedule.get_remaining_games` and added
to the `_table.html` fragment when `period == "Last 30 days"`. The Last 30 days radio
becomes functional. The handler's season path and fragment structure are unchanged;
this ticket only extends the period-branching block and the template's GP column.

## Acceptance criteria

### Period branching — Last 30 days
- [ ] When `period == "Last 30 days"`:
  1. Collect `pool_keys = set(season_pool["player_key"])`.
  2. If `not cache.is_lastmonth_stale(league_key)`: call
     `cache.read_lastmonth_cache(league_key)`; filter to `pool_keys` to build the
     initial `lm_pool`; derive `missing_keys` as `pool_keys - set(lm_pool["player_key"])`.
  3. If `missing_keys` is non-empty: call `fetch_lastmonth_batch(session,
     list(missing_keys), id_to_name)`; if result is non-empty, call
     `cache.upsert_lastmonth_cache(league_key, new_lm)` and merge into `lm_pool` via
     `_merge_pool`.
  4. If `lm_pool` is empty after both steps, fall back to `season_pool` as `base_df`
     (non-fatal — same behaviour as the Streamlit prototype when lastmonth data is
     unavailable).
  5. Otherwise build `base_df`:
     ```python
     meta_cols = ["player_key", "player_name", "team_abbr",
                  "display_position", "status"]
     season_meta = season_pool[[c for c in meta_cols if c in season_pool.columns]]
     base_df = season_meta.merge(lm_pool, on="player_key", how="inner")
     ```
- [ ] Cache functions are not mixed across paths:
  - Season path: `is_player_pool_stale` / `read_player_pool` / `write_player_pool` only.
  - Last-30 path: `is_lastmonth_stale` / `read_lastmonth_cache` / `upsert_lastmonth_cache` only.
- [ ] The Last 30 days radio in the shell is no longer disabled; selecting it triggers a
  POST that executes the lastmonth branch.

### Games remaining
- [ ] Fetch `matchups_df` via `get_matchups` (disk cache hit). If `matchups_df` is None
  or empty, skip games remaining entirely (`games_remaining_map = {}`).
- [ ] Derive `current_week = int(matchups_df["week"].max())`. Call
  `scoreboard.get_current_matchup(session, league_key, current_week)` to obtain
  `week_start` and `week_end` as strings.
- [ ] Wrap strings to `datetime.date` before calling `get_remaining_games`:
  ```python
  from datetime import date
  from_date = date.fromisoformat(matchup["week_start"])
  to_date   = date.fromisoformat(matchup["week_end"])
  ```
- [ ] Call `schedule.get_remaining_games(team_abbrs, from_date, to_date)` where
  `team_abbrs` is the list of unique `team_abbr` values in `ranked_df`.
- [ ] `ranked_df["games_remaining"] = ranked_df["team_abbr"].map(
  lambda a: games_remaining_map.get(a, 0))`.
- [ ] The entire games-remaining block is wrapped in try/except; on any error,
  `games_remaining_map` defaults to `{}` (all players show 0) and the table still
  renders.

### `_table.html` fragment updates
- [ ] `games_remaining` column appears after the player name column when `period ==
  "Last 30 days"`. Format: integer (`{int(v)}`) or `—` for NaN.
- [ ] `games_played` column appears when `period == "Last 30 days"` and `games_played`
  is present in `ranked_df`. Format: integer.
- [ ] Footer bar left side reads "{total_rows} players · last 30 days stats" when
  `period == "Last 30 days"` (was "season stats" in 019a).
- [ ] When `period == "Season"`, the fragment is identical to the 019a output (no GP,
  no games-remaining column, footer says "season stats").

### Demo mode — Last-30 path
- [ ] `POST /demo/api/waiver/players` with `period="Last 30 days"`: uses
  `demo_module.load_lastmonth_pool()` as `lm_pool` and
  `demo_module.get_games_remaining()` as `games_remaining_map`. No `cache.*` calls,
  no Yahoo API calls.

### Unit tests
- [ ] Given a fixture `season_pool` (3 players) and a fixture `lm_pool` (2 of those
  3 players), the `period == "Last 30 days"` join returns exactly 2 rows.
- [ ] When `lm_pool` is empty after both cache read and fetch, `base_df` falls back to
  `season_pool` (3 rows in the fixture above).
- [ ] `games_remaining_map = {}` (simulating a games-remaining fetch failure) → all
  players in `ranked_df` have `games_remaining == 0`; no exception raised.
- [ ] `matchups_df` is None → games-remaining block is skipped; `ranked_df` is returned
  without a `games_remaining` column (or with all zeros, per implementation choice);
  no 500.

## Files likely affected
- `web/routes/waiver.py` (extend `_waiver_post_impl` with the lastmonth branch and
  games-remaining block)
- `web/templates/waiver/_table.html` (add GP and games-remaining columns; update footer
  label)

## Dependencies
- Requires 019a (`POST /api/waiver/players` and `_table.html` exist; `_merge_pool` and
  `_waiver_post_impl` are in place; season path is fully functional).

## Notes for the engineer

**Date type mismatch — wrap strings before calling `get_remaining_games`.**
`get_current_matchup` returns `week_start`/`week_end` as strings (`"YYYY-MM-DD"`), but
`get_remaining_games` expects `datetime.date` objects. Failing to convert causes a
`TypeError` at runtime. Always wrap:
```python
from datetime import date
from_date = date.fromisoformat(matchup["week_start"])
to_date   = date.fromisoformat(matchup["week_end"])
```

**`_merge_pool` is unchanged.**
The lastmonth pool build uses the same `_merge_pool` function defined in 019a. Do not
write a second copy.

**GAA recomputation for lastmonth.**
`stat_id == '23'` is GAA. Yahoo returns season GAA for `type=lastmonth` queries, so it
must be recomputed from GA / games_played. See `data/players.py` lines 289–293 — this
logic lives in `fetch_lastmonth_batch`; verify it is in place before assuming the
`lm_pool` GAA values are correct.

**`season_meta` join: only confirmed columns.**
`season_pool` may not always have all five `meta_cols`. Use the guarded list:
`[c for c in meta_cols if c in season_pool.columns]` to avoid `KeyError` on the
`.merge()`.

**Games remaining is 2–3 external calls on a cold POST.**
The try/except guard is mandatory — do not remove it. Future improvement: cache
`games_remaining_map` in `user_sessions` with a 1-hour TTL.

**Remove the Last 30 days radio disable introduced in 019a.**
019a may have added a `disabled` attribute or tooltip to the radio. Remove it here so
the radio is fully interactive.

## Notes for QA
- Test 1: `POST /api/waiver/players` with `period="Last 30 days"` and at least one stat
  → `base_df` contains `games_played`; fragment renders GP column; footer reads
  "last 30 days stats".
- Test 2: `POST /api/waiver/players` with `period="Season"` → fragment is unchanged
  from 019a (no GP column, no games-remaining column, footer reads "season stats").
- Test 3: `POST /demo/api/waiver/players` with `period="Last 30 days"` → 200 HTML;
  no Yahoo API calls made (verify with mock).
- Test 4: Mock `get_matchups` to return None → table renders with all
  `games_remaining == 0`; no 500.
- Test 5: Mock `get_current_matchup` to raise an exception → same fallback as Test 4.
- Test 6: `lm_pool` empty after cache read and fetch (mock both to return empty
  DataFrames) → `base_df` falls back to `season_pool`; table renders with season stats.
- Manual: select "Last 30 days" radio → table re-renders with GP column and updated
  footer. Switch back to "Season" → GP column disappears.
- Edge case: player in `season_pool` but absent from both lastmonth cache and fetch
  result → that player is excluded from the inner join and does not appear in the
  Last 30 days table.
- Edge case: GAA column in `lm_pool` — confirm values are recomputed (GA / GP), not
  the raw season GAA returned by Yahoo. Compare against the Streamlit prototype output
  for the same player.
