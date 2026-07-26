# Code Review — 037

**Reviewed:** 2026-07-25
**QA verdict on entry:** APPROVED (`tickets/037-qa.md`) — gate satisfied.

**Files reviewed:**
- `data/cache.py` (+139 / −31) — atomic temp-file + `os.replace()` for both writers; per-league lock registry; `write`/`append`/`upsert_lastmonth_cache`/`_write_meta` serialised; path helpers resolve `None` to `CACHE_DIR/_shared/`.
- `tests/test_cache.py` (+243, no deletions) — `run_concurrently()` barrier helper plus 16 new tests across two sections; no existing test modified.
- `tickets/037-cache-write-hardening.md` (+1 / −1) — `## Status` `ready` → `qa`. Workflow bookkeeping, not source.

Independently verified: `git status --porcelain` shows only these three tracked files modified (plus the two new untracked ticket artifacts). No other source file is touched. `.venv/bin/python -m pytest tests/` → **453 passed**.

---

### Scope: CLEAN

The diff is confined to the two paths in `Touches`. Every `Out of scope` clause holds:

| Out-of-scope clause | Status |
|---|---|
| No per-user cache keying | Held — no user dimension appears in any key or path. |
| No call site adopts the shared tier | Held — verified below, this was the item I checked hardest. |
| `data/matchups.py` untouched (ticket 038) | Held — file unmodified. |
| No `fcntl`/`filelock`/new dependency | Held — `tempfile` and `threading` are stdlib; `requirements-web.txt` unmodified. |
| No on-disk-layout or caller-visible signature change | Held — layout identical; the only signature movement is widening `str` → `str \| None`, which is source- and call-compatible. |

**Shared-tier adoption — traced, not assumed.** All ten production `cache.*` call sites (`data/matchups.py:52,67,69,94`; `web/routes/waiver.py:187,188,197,215,216,226`) pass `league_key` positionally and never `None`. The one place a `None` league exists in the codebase is `_waiver_post_impl(..., league_key: str | None = None)` in `web/routes/waiver.py:143`, which is the demo path — and every `cache.*` call in that function sits inside an `else:` branch of `if demo:`, so the demo path reaches none of them. On the authenticated path both route handlers return early when `_get_league_key()` is falsy (`waiver.py:63-64`, `:323-324`), so `league_key` is always a real string by the time the cache is called. `_shared/` is unreachable in production, exactly as the DECISIONS entry requires.

Worth recording for whoever builds the M2 tier: before this change, a `None` league reaching a cache call failed loudly with `TypeError: unsupported operand type(s) for /: 'PosixPath' and 'NoneType'`. It now silently writes to `_shared/`. That loss of a fail-fast guard is inherent to the affordance and was accepted by the decision, not introduced carelessly — noting it so the M2 ticket knows the safety net is gone.

### Architecture: CLEAN

Checked against every always-blocker item:

- **Framework imports in `data/`** — none. `data/cache.py` imports `json`, `os`, `tempfile`, `threading`, `datetime`, `pathlib`, `pandas`. Clean.
- **Per-entity Yahoo loop** — N/A, this module makes no API calls.
- **`_coerce()` / `_as_list()`** — N/A, no Yahoo payload parsing.
- **Demo counterpart** — N/A and verified rather than assumed: `data/demo.py` contains zero references to `cache`, and `data/cache.py` adds no live data function.
- **DECISIONS conflict** — none. The implementation matches the 2026-07-23 "Cache: stays league-keyed" entry's Option B literally (temp file in the same directory, `os.replace()`, module-level `dict[str, threading.Lock]` keyed on `league_key`, `_write_meta` included) and the 2026-07-23 shared-tier entry's Option C (`_parquet_path` and callers accept `None` → `CACHE_DIR/_shared/{data_type}.parquet`, no adopters). The single-worker coupling that the 2026-07-23 deployment entry calls a correctness requirement is now written into the module docstring at `data/cache.py:15-21`, citing both 2026-04-10 and 2026-07-23. That is the right place for it: the next person to propose a second worker reads it in the file the assumption lives in.
- **Implicit-decision drift** — none. No new convention is established that the two cited entries do not already ratify.

### Locking discipline — no deadlock, no missed guard, no ordering hazard

I traced this rather than trusting the handoff, since the `_write_unlocked` / `_write_meta_unlocked` split is the part most likely to hide a self-deadlock.

**Acquisition sites are exactly four**, all public entry points, each acquiring once: `_write_meta:143`, `write:168`, `append:178`, `upsert_lastmonth_cache:246`. Nothing else in the module calls `_lock_for`.

**Nothing reachable while a lock is held acquires a lock.** The lock-holding bodies reach `_ensure_dir`, `_write_parquet`, `_write_json`, `_atomic_write`, `_read_meta`, `_write_meta_unlocked`, `_write_unlocked`, `read`, `_now`, and pandas I/O — none of which touches `_lock_for`. So the non-reentrant `threading.Lock` never re-enters, and the split cores are the correct fix rather than a workaround hiding a latent `RLock` need.

**No lock-ordering hazard.** `_lock_for()` acquires `_locks_guard`, and `return lock` sits inside that `with` block, so the guard is released by `__exit__` before the caller's `with lock:` begins. The guard is therefore never held while a league lock is acquired, and only one league lock is ever held at a time. There are no two locks to order.

**No missed guards.** The three read-modify-write paths named in the DECISIONS entry (`append`, `upsert_lastmonth_cache`, `_write_meta`) are all serialised, plus `write` so its metadata update joins the same critical section. Everything left unguarded is read-only: `read`, `last_updated`, `is_stale`, `read_player_pool`, `read_lastmonth_cache`, `is_player_pool_stale`, `is_lastmonth_stale`. `write_player_pool` delegates to the guarded `write`. That set is complete. Note that `last_updated`/`is_stale` read `last_updated.json` unlocked — safe for the same reason `read()` is, now that the JSON write is atomic.

### Temp-file placement and `.tmp` leakage — correct

`tempfile.mkstemp(dir=path.parent, ...)` puts the temp file in the target's own directory, which is the precondition that makes `os.replace()` atomic rather than a silent cross-filesystem copy. Both call paths guarantee the directory exists first: `_write_unlocked` calls `_ensure_dir` before `_write_parquet`, and `_write_meta_unlocked` calls `_ensure_dir` before `_write_json`. Those are the only two callers of `_atomic_write`, so the precondition is complete rather than incidental. `test_temp_file_is_written_into_the_target_directory` spies on `mkstemp` and asserts every `dir=` argument — the right thing to test, because this property degrades silently rather than failing.

Cleanup on exception uses `except BaseException: tmp.unlink(missing_ok=True); raise`, which covers a failure inside `write_to` and inside `os.replace`, and correctly re-raises rather than swallowing. QA independently injected a mid-write exception and observed no `.tmp` debris with the previous frame intact. The remaining leak window is a hard process kill, which no `try`/`except` can close — logged to `docs/improvements.md`, see below.

The `.{name}.` prefix keeps temp files hidden and out of any `*.parquet` or `ww_season__*` match; I confirmed nothing in `data/`, `web/`, `analysis/`, or `auth/` globs or lists the cache directory at all, so debris cannot leak into a read path.

### AC4 "omitted or `None`" — I agree with the Engineer and QA

**AC4 is met.** The Engineer implemented `None` only and flagged it rather than quietly narrowing the AC, and QA adjudicated it rather than waving it through. Both were right, and the reasoning survives scrutiny:

`league_key` is the first positional parameter of `read`/`write`/`append`. Giving it a default forces defaults onto `data_type` and `df`, which makes `cache.write()` with zero arguments a legal call — a caller-visible signature change the ticket's own `Out of scope` forbids. Reordering to `write(data_type, df, league_key=None)` breaks AC4's second clause, since all ten call sites pass the league positionally. The two halves of AC4 are in direct tension, and the AC's own worked examples (`cache.write(None, "some_type", df)` / `cache.read(None, "some_type")`) are the `None` form — so the examples, which are the operative specification, are satisfied exactly. Nothing was lost.

Endorsing QA's note to the PM: drop "omitted" from this phrasing in future tickets. It reads as an alternative but is not expressible for a leading positional parameter, and it cost two roles a paragraph each to adjudicate.

### Diff size — the ~200-line heuristic is not breached in substance

`data/cache.py` is +139 / −31, about 108 net lines, comfortably inside the heuristic and close to the "roughly 20 lines" the DECISIONS entry estimated once the docstring, the two path helpers, and the `_unlocked` split are counted. The remaining +243 is entirely `tests/test_cache.py`, and the heuristic exists to bound *source* churn risk, not test coverage.

I checked whether any of the test bulk is unwarranted and concluded it is not. QA's de-hardening run proved 14 of 16 non-vacuous. Of the two that survive de-hardening, `test_writes_leave_no_temp_files_behind` guards the debris hazard the temp-file mechanism itself introduces, and `test_upsert_lastmonth_still_replaces_rows_for_the_same_player` is a legitimate sequential regression guard — `upsert_lastmonth_cache` stopped calling `write()` and now calls `_write_unlocked()`, so pinning its dedup behaviour is exactly right. The six shared-path tests are the heaviest section relative to a five-line affordance, and `test_concurrent_shared_appends_do_not_lose_rows` is close to a duplicate of its league-keyed twin, but it does exercise the distinct `_lock_for(None) → "_shared"` sentinel mapping. I would not cut any of it.

`run_concurrently()`'s `join(timeout=60)` plus the `is_alive()` assertion is the right shape: a deadlock surfaces as a named failure instead of a hung suite.

### Security and data: CLEAN

No logging of any kind in `data/cache.py`, so no token, session ID, or PII exposure. No SQL. No new dependency. The only env var read is the pre-existing `CACHE_DIR`. `league_key` is used as a path component, but it originates from `user_sessions.league_key` in SQLite (`web/routes/common.py:32-37`, parameterised `?`), populated from Yahoo API responses — not from a request body or query string — and this diff changes nothing about that provenance. One incidental effect worth knowing rather than fixing: `mkstemp` creates files at mode 0600, so cache files written after this change are 0600 where they were previously 0644. In a single-user container that is harmless and marginally tighter.

### Issues

- **blocker:** none.
- **should-fix:** none.
- **nit:** `_atomic_write(path: Path, write_to)` is the only annotation-free parameter in a fully typed module. `write_to: Callable[[Path], None]` would match the file's own standard.
- **nit:** `_write_meta()` (the locking wrapper) now has no production caller — `write`/`append`/`upsert` all route through `_write_meta_unlocked`, so its only live caller is `tests/test_cache.py:365`. Ordinarily that reads as dead surface, but AC3 names `_write_meta` explicitly and requires it to be concurrency-safe when called directly, so keeping it is correct here. Flagging only so a future reader does not mistake it for an oversight and delete it.
- **nit:** the lock registry keys `None` on the literal `"_shared"`, so a league whose key were literally `_shared` would share a lock with the shared tier. Yahoo league keys are of the form `419.l.11111`, so this is unreachable. QA noted it too; no fix warranted.
- **nit:** `_write_unlocked` calls `_ensure_dir`, then `_write_meta_unlocked` calls it again. Redundant but harmless, and removing it would make `_write_meta_unlocked` unsafe to call on its own.

None of these are worth a round trip. Per the persona, `nit`s alone never block.

### Logged to `docs/improvements.md`

One new entry, in the `## Open` section:

- **"Atomic cache write is crash-safe against concurrent readers but not against machine restart"** (`Type: quality`, `data/cache.py:85`). `_atomic_write()` does no `fsync()` on the temp file before the rename and none on the directory after it, so a Fly machine restart or migration can leave the rename durable while the data blocks are not — a zero-length or truncated parquet on the volume, which is the same "persists and does not self-heal" failure the DECISIONS entry exists to prevent, arriving through a different door. The same entry covers `.tmp` debris after a hard kill.

  **This is not a 037 defect and was correctly excluded.** Ticket 037 and DECISIONS 2026-07-23 both scope the hardening to concurrent-reader atomicity, which `os.replace()` alone fully delivers; neither mentions `fsync`. Requesting it here would be scope creep of my own making. Logged for whenever `data/cache.py` is next opened, or sooner if the deployment ever reports an unreadable cache file after a restart.

### Verification adequacy

QA's report is unusually strong and I am not re-litigating it. Two things I want on the record because they raise my confidence in the APPROVED verdict rather than merely restating it:

QA closed the gap the Engineer honestly handed over. The Engineer could not drive authenticated `/waiver` and `/overview` and said so plainly instead of substituting weaker evidence and calling it done. QA judged the substitute inadequate — correctly, since the route tests patch `web.routes.waiver.cache.write_player_pool` and never touch disk — then built a harness with `data/cache.py` fully unmocked against a real tmp `CACHE_DIR`, and drove cold and warm plus eight concurrent authenticated requests. That converts the ticket's Verification section from claimed to observed. Only the Yahoo OAuth handshake remains owner-must-verify, and it never touches `data/cache.py`.

Non-vacuity was proven, not asserted. Reverting `_atomic_write` and `_lock_for` to their pre-change behaviour turned 8 tests red with real defect signatures (`ArrowInvalid`, `JSONDecodeError`) while all 26 pre-existing tests stayed green — which is the check that distinguishes tests that guard a defect from tests that merely re-describe the new implementation. QA also ran two edge cases the ticket never asked for: a failed write leaving the previous frame intact, and 24 threads mixing all four write paths without deadlock. That second one is the direct empirical counterpart to my static analysis of the `_unlocked` split above, and the two agree.

Backward compatibility with data already on the Fly.io volume was checked and passes: a pre-037 parquet plus a hand-written `last_updated.json` read correctly through the hardened module and appended cleanly. **No cache clearing is needed at deploy.**

---

### Verdict: APPROVED

The change implements both cited DECISIONS entries faithfully, stays inside `Touches`, introduces no dependency, and closes the M1 concurrency defect. The locking discipline is sound under static tracing and under QA's mixed-load test. The shared-tier affordance exists and is provably unreachable from production. Ticket `## Status` set to `done`; artifacts moved to `tickets/done/`.

One improvements entry logged (crash-durability of the atomic write), deliberately not requested as a change. Ticket 038 is unblocked and should proceed — QA's observation that `data/matchups.py` can still double-fetch a week across two `get_matchups` calls is now a duplicate-rows problem absorbed by the read-time dedup, not a corruption one, which is the correct posture for 038 to inherit.
