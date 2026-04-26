# Bug Report: Week 23 Shows All Zeroes for All Teams

**Reported:** 2026-04-26
**Severity:** Major

## Summary

The overview page displays all-zero stats for all teams in week 23. Confirmed stats exist (e.g. team "Ilya Sobrokin": 31 G, 42 A, 73 PTS, expected overall rank ~3.07) but are not shown.

## Steps to Reproduce

1. Open the app early in a new week (before any games have been played for that week).
2. The week is fetched — Yahoo API returns `"-"` for all stats (no activity yet) → `_coerce()` converts to `0.0` for every stat.
3. Week N is now `_last_cached_week`.
4. Games are played. Stats accumulate.
5. Open the app again on any later day.
6. **Result:** All stats for that week remain `0.0`. The table shows every team with every stat at `0`.

## Root Cause

**File:** [`data/matchups.py`](../data/matchups.py), lines 44–46

```python
last_week = _last_cached_week(league_key)
fetch_from = start_week if last_week is None else last_week + 1
weeks_to_fetch = list(range(fetch_from, current_week + 1))
```

Once a week is stored in the cache — even with all-zero stats — `_last_cached_week` returns that week number, so `fetch_from` jumps past it. The week is never re-fetched.

There is a partial mitigation at lines 50–54 that re-fetches `current_week - 1` (the previous completed week) if the cache was last written today. But this does **not** apply to `current_week` itself, so the current week can be permanently stuck at zeroes once it is cached early.

### Why the "today" condition doesn't save us

When the next week starts, `current_week` advances to N+1 and week N becomes `prev_week`. The re-fetch condition then checks:

```python
lu = cache.last_updated(league_key, "matchups")
if lu is not None and lu.astimezone().date() == _date.today():
```

`lu` is the timestamp from days ago (when the all-zero data was written). Unless the user happens to open the app on the exact day week N+1 is first fetched, `lu.date() != today` and week N is never re-fetched.

## Impact

- All teams show `0` for every scoring stat for the affected week.
- Rankings (`avg_rank`) are meaningless — all teams rank equally since all values are identical.
- The bug is sticky: once zeroes are cached, the app will never self-correct on subsequent visits.

## Expected Behaviour

The current week's stats should always be re-fetched on each app visit (or at minimum, once per day), because they update as games are played throughout the week.

## Proposed Fix

Always include `current_week` in `weeks_to_fetch`, regardless of whether it is already cached:

```python
# data/matchups.py  lines 44–46
last_week = _last_cached_week(league_key)
fetch_from = start_week if last_week is None else last_week + 1
weeks_to_fetch = list(range(fetch_from, current_week + 1))

# Always re-fetch the current week — stats update as games are played.
if current_week not in weeks_to_fetch:
    weeks_to_fetch.append(current_week)
```

`cache.append` followed by `drop_duplicates(keep="last")` (already in `get_matchups`) will ensure the freshly fetched data replaces the stale zeroes.

## Files Involved

| File | Role |
|------|------|
| [`data/matchups.py`](../data/matchups.py) | Delta-fetch logic — **location of the bug** |
| [`data/client.py`](../data/client.py) | `_coerce()` converts `"-"` → `0.0` (correct behaviour; not the bug) |
| [`data/cache.py`](../data/cache.py) | `append()` + `drop_duplicates(keep="last")` used by dedup |
| [`analysis/team_scores.py`](../analysis/team_scores.py) | `weekly_scores_ranked()` — displays whatever is in the cache |
