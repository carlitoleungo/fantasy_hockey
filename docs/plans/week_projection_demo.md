# Plan: Extend Demo Mode to Cover Week Projection

## Context

`pages/04_week_projection.py` currently shows an info message and stops in demo mode (lines 234–241). The goal is to populate it with static demo data so the full projection UI works — team selector, projected category comparison, roster breakdown — without any live API calls.

---

## Confirmed Data Gaps

After reading `demo/data/`:

| Data | Status |
|---|---|
| Roster players per team | **Missing** — only waiver wire players in `players_season.parquet` / `players_lastmonth.parquet` |
| Games remaining | **Present but all zeros** — `games_remaining.json` has a full end-of-week snapshot, unusable for projection |
| Last-30-day stats for rostered players | **Missing** — `players_lastmonth.parquet` covers 25 waiver wire players only |
| Teams list | Available via `matchups.parquet` (12 teams, `team_key` + `team_name`) |
| Scoreboard (matchup pairings + week dates) | **Missing** |
| Live week stats (current totals) | **Missing** for the projection page format |

`matchups.parquet` columns: `team_key`, `team_name`, `week`, `games_played`, + 14 stat columns
`players_lastmonth.parquet` columns: `player_key`, `games_played`, + skater stats only (no goalie stats)

---

## Approach: Hybrid

**Option A (real fetch) for roster + schedule:**
- `data/roster.py::get_team_roster(session, team_key, week=14)` already supports the `week=` param → historical roster fetch is feasible
- `data/schedule.py::get_remaining_games()` uses the public NHL API (no auth) → can query any past date range

**Option B (derived) for last-30-day stats:**
- Yahoo's `type=lastmonth` endpoint always returns the trailing 30 days from *today* — no historical date anchor. A real historical fetch is not possible.
- Derive per-game rates from season totals fetched alongside the roster (season GP + stat totals → per-game rate used as the lastmonth proxy). This is a reasonable approximation and the demo never claims to be a live snapshot.

**Hybrid is the right call** because it gives realistic player names and teams for rosters, accurate NHL schedule data, and avoids the only real API limitation (lastmonth stats). For live week stats, use zeros (clean "start of week" view — more illustrative for demo purposes).

---

## Files Generated (committed to repo, never recomputed at runtime)

### `demo/data/projection_context.json`
Shape matches what `pages/04_week_projection.py` stores in `st.session_state["projection_data"]`:
```json
{
  "current_week": 14,
  "stat_categories": [...],
  "teams": [
    {"team_key": "465.l.8977.t.1", "team_name": "West Coast Young Bloodz"},
    {"team_key": "465.l.8977.t.2", "team_name": "The kIRillers"}
  ],
  "live_stats_rows": [
    {"team_key": "465.l.8977.t.1", "Goals": 0.0, "Assists": 0.0, ...},
    {"team_key": "465.l.8977.t.2", "Goals": 0.0, ...}
  ],
  "scoreboard": {
    "week_start": "2025-12-29",
    "week_end": "2026-01-04",
    "matchups": [{"team_a_key": "465.l.8977.t.1", "team_b_key": "465.l.8977.t.2"}]
  }
}
```
Only 2 teams and 1 matchup — the dropdown shows exactly the demo pair, no edge cases from selecting a team with no data.

### `demo/data/projection_pair_data.json`
```json
{
  "my_team_key": "465.l.8977.t.1",
  "opp_team_key": "465.l.8977.t.2",
  "my_roster": [
    {"player_key": "nhl.p.XXXX", "player_name": "...", "team_abbr": "EDM",
     "display_position": "C", "roster_slot": "C"},
    ...
  ],
  "opp_roster": [...],
  "lastmonth_stats": {
    "nhl.p.XXXX": {"games_played": 18, "Goals": 0.83, "Assists": 1.44, ...},
    ...
  },
  "games_remaining": {
    "EDM": 2, "COL": 3, "TOR": 1, ...
  }
}
```

---

## Script: `scripts/extend_demo_data.py`

Run once, commit output. Steps:
1. Load `demo/data/league_meta.json` for league key and snapshot week
2. Get Yahoo OAuth session (standalone auth helper with `.streamlit/secrets.toml` + token cache)
3. Fetch week 14 scoreboard → pick the first matchup pair as the demo pair; get week_start/week_end
4. Fetch rosters: `roster.get_team_roster(session, team_key, week=14)` for both teams
5. Collect all rostered player keys; fetch season stats via `/players;player_keys={keys}/stats;type=season`
6. Derive `lastmonth_stats`: store season totals + season GP; per-game rate (`stat / gp`) implicitly used by projection formula. GAA: recomputed from GA/GP.
7. Call `schedule.get_remaining_games(all_abbrs, from_date=wednesday_of_week14, week_end)` → mid-week games remaining
8. Build and save `projection_context.json` and `projection_pair_data.json`

---

## Changes to `data/demo.py`

Two new loader functions:

```python
def get_projection_context() -> dict:
    """
    Return {current_week, stat_categories, teams, live_stats_rows, scoreboard}
    for the demo week projection page.
    """
    return _load_json("projection_context.json")


def get_projection_pair_data() -> dict:
    """
    Return {my_team_key, opp_team_key, my_roster, opp_roster,
    lastmonth_stats, games_remaining} for the demo projection pair.
    """
    return _load_json("projection_pair_data.json")
```

---

## Changes to `pages/04_week_projection.py`

Replace lines 234–241 (the demo `st.stop()` block) with:
- An `st.info()` banner noting this is a fixed Week 14 snapshot
- Session state pre-population from demo data (same keys as the non-demo path)
- Fall through to normal rendering code — no `st.stop()`

The lazy fetch block (`if pair_key not in st.session_state`) is automatically skipped because the demo only exposes 2 teams in the teams list, meaning only one pair key is ever possible and it's already pre-populated.

---

## Files Modified

| File | Change |
|---|---|
| `scripts/extend_demo_data.py` | **Create** — one-time data generation script |
| `demo/data/projection_context.json` | **Create** (generated by script, committed) |
| `demo/data/projection_pair_data.json` | **Create** (generated by script, committed) |
| `data/demo.py` | **Modify** — add `get_projection_context()` and `get_projection_pair_data()` |
| `pages/04_week_projection.py` | **Modify** — replace demo `st.stop()` with demo data injection |
