# Bug Tracker

> **Scope:** This file tracks bugs in the current FastAPI stack and in the preserved data/analysis layers (`data/`, `analysis/`). For bugs specific to the Streamlit prototype, see [`docs/archive/prototype-bugs.md`](archive/prototype-bugs.md).

---

## Open

### `matchups.py` re-fetch loop causes parquet bloat and unnecessary API calls

**Symptom:** On every page load for the rest of a given day, `prev_week` stats are re-fetched from Yahoo and appended to the parquet file. The data stays correct in memory (duplicate rows are dropped on read) but the parquet grows unboundedly and adds latency on every load.

**Root cause:** The intent of `matchups.py` lines 50–54 is to re-fetch `prev_week` once per day in case its stats were updated after an earlier fetch:
```python
lu = cache.last_updated(league_key, "matchups")
if lu is not None and lu.astimezone().date() == _date.today():
    weeks_to_fetch = [prev_week] + weeks_to_fetch
```
The condition fires on **every** page load for the rest of the day, because each successful fetch updates `last_updated` to now (today). This appends `prev_week` rows to the parquet on every load. `drop_duplicates(keep="last")` in `get_matchups()` keeps the data correct in memory, but the parquet bloats over time.

**Fix (not yet implemented):**
- Replace the `last_updated == today` condition with a per-week staleness check, or track a separate `prev_week_refreshed_date` value in `last_updated.json`.
- Alternatively, use `cache.write()` (overwrite) instead of `cache.append()` after deduplication, so the parquet stays clean regardless of how many times re-fetch runs.

**Affected files:** `data/matchups.py`, `data/cache.py`
**Discovered:** 2026-03-30

---

## Closed

<!-- Move resolved bugs here with a brief resolution note -->
