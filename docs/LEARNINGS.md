# Learnings — Fantasy Hockey Waiver Wire

Recurring gotchas and patterns that apply across tickets. Every persona reads this
before starting work. Only add entries that would affect future, unrelated tickets —
not one-off bugs or ticket-specific issues.

If this file grows past ~30 entries, the PM should prune stale items during a
product review (remove anything resolved by architecture changes or no longer relevant).

---

### xmltodict single-item collections: always normalise with `_as_list()`

When a Yahoo API collection has exactly 1 item, `xmltodict` returns a dict instead of a
list. Never index a Yahoo collection directly — normalise via `_as_list()` from
`data/client.py` first. Known to affect: stat categories, `stat_position_type`, teams,
per-week stat lists.

### Stat values need `_coerce()` — never assume numeric

`stat['value']` can be `'-'` (player didn't play) or `None`, not just a number. Coerce
to `0.0` via `_coerce()` from `data/client.py` before any arithmetic or DataFrame load.

### `stat_id == '0'` is games played, not a scoring category

Don't let it leak into ranking calculations; handle it specially in per-game maths.
Related: `is_only_display_stat == '1'` marks non-scoring display stats — filter using
`is_enabled`.

### GAA (`stat_id == '23'`) must be recomputed for lastmonth

Yahoo returns *season* GAA even when `type=lastmonth` is requested. Recompute as
GA / games_played — see `data/players.py` ~lines 289–293 for the reference
implementation.

### `display_position` is composite

Values like `"C,LW"` — split on comma before filtering by position.

### Player `status` values

`""` (healthy), `"DTD"`, `"O"`, `"IR"`.

### Bulk endpoints over per-entity loops

Never make N per-entity Yahoo API calls when a collection endpoint exists. Example:
`/league/{key}/teams/stats;type=week;week={w}` fetches every team's stats for a week in
one call. When adding a new fetch, check `data/client.py` and the Yahoo docs for a
collection endpoint before defaulting to a loop.

### Tests must patch the importing module's namespace

Data modules import helpers by name (`from data.client import _get`), which binds the
name in the importing module. Patching `data.client._get` has no effect on them — patch
`data.players._get`, `data.leagues._get`, etc. (See DECISIONS.md 2026-03-03 entry.)

### Off-season → no live data; week-keyed feature pages only show empty states

We develop during the NHL off-season, so live Yahoo data for week-keyed features is
empty or stale: matchups, weekly scoreboards, `type=lastmonth` player rates, and
`schedule.get_remaining_games` (which counts games from today forward) all return
nothing meaningful. The app fetches **live snapshots by default** (`current_week` is read
live from `league["current_week"]` — `data/client.py:145`; available waiver player pools
are cached with a 24 h TTL, so an off-season fetch caches an empty/stale pool for a day
unless `CACHE_DIR` is cleared). Consequence: an authenticated live visual test or
QA pass of any week-keyed page (Week Projection 029/030, matchups) can only exercise the
empty/placeholder state — it cannot validate real compute against live data. **Demo mode
(`data/demo.py`, snapshotted at `snapshot_week`) is the current answer for a *visual*
check**, but it does not exercise the authenticated live-fetch code paths in
`client.py` / `cache.py`. Testing those against a *specific past week* is unsolved and
being explored — see the scoping brief `tickets/033-dev-past-week-testing-spike.md`.

---

[Test Engineer and team members add entries here as they're discovered]
