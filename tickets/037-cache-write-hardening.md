# 037 — Cache write-hardening: atomic rename + per-league lock + shared-tier affordance

## Status
ready

## Type
refactor

## Milestone
m1

## Touches
- data/cache.py
- tests/test_cache.py

## Why
M1 puts up to ~8 authenticated users, including several managers from the *same* league,
on one deployment. The route handlers are sync `def`, so FastAPI runs them in the
threadpool and two requests genuinely interleave. `data/cache.py` writes are not
concurrency-safe today, and a corrupted parquet or `last_updated.json` **persists on the
volume** and fails every subsequent read for that league until someone deletes it by hand
— it does not self-heal. It does not even take two users: a single manager rapid-firing
HTMX filter changes at `/api/waiver/players` produces concurrent writes to the same pool
files on their own. This is the concurrency defect that must close before M1 goes live.

## Acceptance criteria
- [ ] With N threads each calling `cache.append(league, "matchups", <one-row df>)` concurrently on the same league+data_type, after all threads join `cache.read(league, "matchups")` returns a DataFrame with exactly N rows — no rows lost to an interleaved read-modify-write.
- [ ] With one thread repeatedly calling `cache.write(league, dt, df)` while another repeatedly calls `cache.read(league, dt)` on the same file, no read raises `ArrowInvalid`/`FileNotFoundError`/`OSError` from observing a partially written file — every read returns either the previous complete frame or the new complete frame.
- [ ] Concurrent `_write_meta` calls for distinct data types on one league never raise `JSONDecodeError`, and after they join `last_updated.json` parses and contains a timestamp for every data type written (no lost metadata keys).
- [ ] The shared-tier path affordance exists: calling the write/read API with the league omitted or `None` (e.g. `cache.write(None, "some_type", df)` / `cache.read(None, "some_type")`) round-trips through `CACHE_DIR/_shared/some_type.parquet`, and every existing league-keyed call site is unchanged in behaviour.
- [ ] `.venv/bin/python -m pytest tests/` is green (existing `tests/test_cache.py` cases still pass plus the new concurrency + shared-path assertions).

## Out of scope
- **Per-user cache keying — dropped, not deferred.** Do not add a user dimension to any
  cache key or path. See the DECISIONS entry cited below.
- **Adopting the shared tier at any call site.** This ticket adds only the `_shared/` path
  *affordance* (the ~5 lines that let `None`/absent league resolve to `CACHE_DIR/_shared/`).
  No caller passes `None` in production at M1; `ww_lastmonth` and the NHL schedule stay
  league-keyed until M2. Wiring the affordance to real call sites is explicitly M2.
- **`data/matchups.py` and its append-per-page-load bloat** — that is ticket 038, kept
  separate (different file, different concern). Do not touch `matchups.py` here.
- **File locking across processes (`fcntl`/`filelock`) or any new dependency** — rejected
  in the consult; an in-process `threading.Lock` is sufficient under the single uvicorn
  worker. Do not add a requirement.
- Changing the on-disk layout (`{league_key}/{data_type}.parquet`), the parquet format, or
  any function signature visible to callers beyond accepting `None`/absent league.

## Notes for the Engineer
- **Architectural surface — the Tech Lead consult is already done; do not re-open it.**
  This ticket implements two DECISIONS entries verbatim; cite them, don't re-derive:
  - `docs/DECISIONS.md` **"Cache: stays league-keyed; write safety comes from atomic rename
    + in-process locking, not per-user keying" (2026-07-23)** — the chosen fix (Option B):
    write to a temp file in the same directory and `os.replace()` onto the target (atomic on
    POSIX within a filesystem), and guard the read-modify-write paths with a **module-level
    `dict[str, threading.Lock]` keyed on `league_key`**. The three failure modes it fixes:
    non-atomic `write()` (`df.to_parquet(path)` at `data/cache.py:89`), unguarded
    read-modify-write in `append()` (`data/cache.py:93-104`) and `upsert_lastmonth_cache()`
    (`data/cache.py:162-172`), and the truncating `open(..., "w")` in `_write_meta()`
    (`data/cache.py:65-71`).
  - `docs/DECISIONS.md` **"Cache: league-independent data gets a shared tier at M2; M1 only
    preserves the affordance" (2026-07-23)** — `_parquet_path` (`data/cache.py:32`), and by
    extension `_meta_path` (`:37`) and `_ensure_dir` (`:42`), accept a `None`/absent league
    and resolve to `CACHE_DIR/_shared/{data_type}.parquet`. Affordance only; no call site
    adopts it.
- **Why `threading.Lock` is enough:** it is load-bearing on the single-uvicorn-worker
  decision (`docs/DECISIONS.md` 2026-04-10 "Runtime: single uvicorn worker"). The two are
  explicitly coupled — do not introduce anything that assumes multiple workers.
- **Atomic-write mechanics:** the temp file MUST be created in the *same directory* as the
  target (same filesystem) or `os.replace()` is not atomic. Apply the temp-file+`os.replace`
  pattern to all three writers: the parquet write in `write()`/`append()`, and the JSON
  write in `_write_meta()`. `read()` needs no lock — atomic rename means a reader always sees
  a complete file — but `append()`, `upsert_lastmonth_cache()`, and `_write_meta()` do (they
  read-modify-write). `write()` itself calls `_write_meta()`, so its metadata update is
  serialised through the same lock.
- **Lock registry:** a module-level `dict[str, threading.Lock]` needs its own guard for the
  get-or-create of a per-league lock (a small module-level lock around the dict access), or
  use a structure that creates locks atomically. Key the lock on `league_key`; for the
  `None`/shared case, key it on `"_shared"` (or a sentinel) so shared-tier writes are also
  serialised.
- **`_read_meta` robustness:** with atomic metadata writes a torn read can no longer happen,
  so no defensive JSON parsing is required beyond what exists. Do not add retry loops.
- **Testing concurrency deterministically is the hard part.** Use `threading` with a
  `Barrier` (or many threads + a shared start event) to force overlap, and assert on the
  *outcome* (row counts, valid parse) rather than timing. The existing `tests/test_cache.py`
  already exercises read/write/append/last_updated/is_stale/isolation/CACHE_DIR under a
  `tmp_path`-based `CACHE_DIR` override — follow that fixture pattern for the new cases.

## Verification
- `.venv/bin/python -m pytest tests/test_cache.py` green, including the new concurrency cases
  (append row-count under N threads; write/read overlap never raising; concurrent
  `_write_meta` producing valid JSON with all keys) and the shared-path round-trip.
- Full suite `.venv/bin/python -m pytest tests/` green — confirms no caller regressed (matchups,
  waiver pool, lastmonth cache all still read/write correctly through the hardened paths).
- Demo mode is unaffected (demo reads snapshots, not the cache), but sanity-check that
  `GET /waiver` and `GET /overview` still render for an authenticated session after a warm
  cache write.

## Dependencies
- Tech Lead consult on the cache concurrency + shared-tier questions — RESOLVED 2026-07-23
  (two DECISIONS entries cited above). No other ticket blocks this; do it first of the M1
  cache work (038 sequences after it).
</content>
