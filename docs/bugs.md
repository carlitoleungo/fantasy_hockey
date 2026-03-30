# Bug Tracker

---

## Open

### `matchups.py` re-fetch loop causes stale session data for `prev_week`

**Symptom:** After a new week starts, the most recently completed week (`current_week - 1`) may show all-zero stats in the UI despite the week being fully complete. Logging out and back in (which clears session state) resolves it immediately.

**Root cause — two related issues:**

1. **Stale session state.** `load_matchups()` stores the matchup DataFrame in `st.session_state` and only fetches it once per browser session. If a session was started before the real end-of-week stats were fetched, the in-memory DataFrame retains the zeros that were cached earlier in the week. The parquet on disk is correct; only the session is stale.

2. **Re-fetch loop accumulates duplicates.** The intent of `matchups.py` lines 50–54 is to re-fetch `prev_week` once per day in case its stats were updated after an earlier fetch:
   ```python
   lu = cache.last_updated(league_key, "matchups")
   if lu is not None and lu.astimezone().date() == _date.today():
       weeks_to_fetch = [prev_week] + weeks_to_fetch
   ```
   The condition fires on **every** page load for the rest of the day, because each successful fetch updates `last_updated` to now (today). This appends `prev_week` rows to the parquet on every load. `drop_duplicates(keep="last")` in `get_matchups()` keeps the data correct in memory, but the parquet bloats over time and the unnecessary API calls add latency.

**Workaround:** Log out → log back in to force a fresh data load.

**Fix (not yet implemented):**
- Replace the `last_updated == today` condition with a per-week staleness check, or track a separate `prev_week_refreshed_date` value in `last_updated.json`.
- Alternatively, use `cache.write()` (overwrite) instead of `cache.append()` after deduplication, so the parquet stays clean regardless of how many times re-fetch runs.

**Affected files:** `data/matchups.py`, `data/cache.py`
**Discovered:** 2026-03-30
