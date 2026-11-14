# Learnings — Fantasy Hockey Waiver Wire

Recurring gotchas that a model or new contributor can't guess from the code. Read this
before touching `data/` or `analysis/`. Only add entries that would affect future, unrelated
work, not one-off bugs. Prune entries once the architecture makes them irrelevant.

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

### Read parquet through an open file handle, not a path

`cache.read()` opens the file and hands the handle to `pd.read_parquet`. Given a path,
pyarrow (seen with pandas 3.1 / pyarrow 26) may open the file more than once; if a
concurrent write's `os.replace()` lands in between, the read sees a mix of two files and
raises `OSError: Unexpected end of stream`. One handle pins one inode, so atomic replace
stays safe. `tests/test_cache.py::test_reads_during_concurrent_writes_never_observe_a_partial_file`
catches a regression.

### Tests must patch the importing module's namespace

Data modules import helpers by name (`from data.client import _get`), which binds the
name in the importing module. Patching `data.client._get` has no effect on them — patch
`data.players._get`, `data.leagues._get`, etc. (See DECISIONS.md 2026-03-03 entry.)

**Exception — the demo data module.** The route modules import `from data import demo as
demo_module` and call `demo_module.get_matchups()`. The function name is looked up on the
`data.demo` module object at call time, not bound into the route module, so the rule
above inverts: patch `data.demo.get_matchups`, **not**
`web.routes.overview.get_matchups`. Patching the route module for a demo handler fails
silently — the handler still gets the real snapshot, so a test meant to exercise an
empty-state branch quietly runs against the populated one and passes while guarding
nothing. Check whether a route binds the function name or goes through a module object before
choosing a target.
(The working pattern is in `tests/test_demo_overview_routes.py` lines 11-12.)

### Purge `__pycache__` between mutation probes, or CPython replays the previous result

CPython invalidates a `.pyc` on source **size + mtime**, not content. Mutation probes that
delete one same-length line at a time (e.g. the four 77-byte `**shell_context(...)` lines in
`web/routes/overview.py`) produce successive source files of identical size, and when two
probes land in the same second the cached bytecode is reused — the run reports the *previous*
mutation's result. `pytest -p no:cacheprovider` does not help: it governs pytest's own cache,
not CPython's bytecode cache. Delete every `__pycache__` between mutations
(`find . -name __pycache__ -type d -not -path "./.venv/*" -exec rm -rf {} +`). This has happened
before: a QA pass certified the wrong test as a branch's guard.

### Off-season → no live data; week-keyed feature pages only show empty states

During the NHL off-season (roughly mid-April to early October), live Yahoo data for week-keyed features is
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
`client.py` / `cache.py`. There is deliberately no runtime past-week override (see `docs/DECISIONS.md` § Testing);
the fallback is captured fixtures, listed as an idea in `docs/TODO.md`.

## Styles and demo data

- **Demo last-month rows have no names or positions.** `data/demo.load_lastmonth_pool()` is
  stats-only, like the live last-month fetch; the waiver route joins names, team, positions and
  status from the season pool in both modes. Before 2026-11-05 the demo skipped that join and
  rendered blank player cells.
- **The demo's `games_remaining.json` was all zeros** (snapshot taken after the week ended). It
  holds the 26 teams from `projection_pair_data.json`, the same week the Projection demo uses,
  plus six edge-case teams (0 and 4 games) added by `scripts/add_demo_edge_cases.py`.
- **Part of the demo snapshot is hand-made edge cases.** `scripts/add_demo_edge_cases.py` adds
  derived (not real) last-30 rows for D and G, every Yahoo status code (`IR-LT`, `IR-NR`, `SUSP`,
  `GTD` and the rest), 0- and 4-game weeks and an accented name. Re-running
  `scripts/generate_demo_data.py` overwrites them, so run the edge-case script straight after.
- **Yahoo seems to strip accents from player names** ("Teuvo Teravainen", "Charle-Edouard
  D'Astous" in the snapshot). Don't rely on it: the demo carries one accented name
  so templates are checked against them.
- **`.gitignore` ignores `package.json` and `package-lock.json` everywhere.** The style tooling in
  `web/styles/` is committed with `git add -f`.
- **Class names built in templates are invisible to Tailwind.** `pchip-{{ pos }}` or
  `s{{ level }}` never appear literally, so the build purges them unless they are in the
  `safelist` in `web/styles/tailwind.config.js`.
- **New Tailwind classes need a rebuild.** The committed `web/static/app.css` only contains
  classes Tailwind found in `web/templates/**`; a class added without `npm run build` silently
  does nothing.
