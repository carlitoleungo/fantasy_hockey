## Code Review — 038

**Reviewed:** 2026-07-26
**QA verdict on entry:** APPROVED (`tickets/038-qa.md`) — precondition met.

**Files reviewed:**
- `data/matchups.py` — `_merge_into_cache()` replaces `cache.append()`; module docstring step 4
  and the read-side dedup comment updated. +27/-5.
- `tests/test_matchups.py` — one appended section, `read_parquet_from_disk()` helper plus 4 tests.
  +105/-0, no pre-existing test edited.
- `docs/improvements.md` / `docs/archive/improvements-closed.md` — the DoD entry move. -19/+8.
- `tickets/038-matchups-parquet-bloat-fix.md` — `## Status` only.

**Independently verified:** `.venv/bin/python -m pytest tests/` → **457 passed**. `git diff` read
in full; no mutating git command run.

---

### Scope: CLEAN

The diff is exactly `Touches` (`data/matchups.py`, `tests/test_matchups.py`) plus the ticket's
prescribed DoD move and the `Status` line. `data/cache.py` is untouched — confirmed by
`git status`, which is the ticket's hardest scope constraint. The week-selection logic the ticket
put out of scope (`_last_cached_week`, `weeks_to_fetch`, the unconditional `current_week` append,
the `last_updated == today` prev-week branch) is byte-identical in the diff. Neither of the two
out-of-scope improvements items naming `data/matchups.py` was touched. No bonus features, no
"while I'm here" cleanup.

The ticket instructed the Engineer to **stop and flag** rather than widen scope if the clean fix
needed a cache-layer change. They did exactly that (`038-done.md`, "Known limitations"), and QA
reproduced the consequence rather than reasoning about it. That is the process working, and it is
why the concurrency finding below is a follow-up and not a change request.

### Architecture: CLEAN

Checked every always-blocker in the persona:

| Check | Result |
|---|---|
| Framework import in `data/` | None. Imports are `datetime`, `pandas`, `data.cache`, `data.client`. |
| Per-entity Yahoo loop where a bulk endpoint exists | Unchanged — still one `get_all_teams_week_stats` call per week. The diff touches no fetch code. |
| Raw `stat['value']` without `_coerce()` | No stat parsing added. |
| Yahoo array indexed without `_as_list()` | No Yahoo payload handling added. |
| Missing demo counterpart in `data/demo.py` | No new public function. `_merge_into_cache` is private and demo mode reads the snapshot via `data/demo.py`, never `data.matchups.get_matchups` (QA confirmed at `web/routes/overview.py:222-229`). |
| DECISIONS conflict | None. See below. |
| Implicit-decision drift | One question raised for the Tech Lead — see Findings. Not a blocker on this diff. |

**DECISIONS conformance, checked entry by entry:**

- **2026-05-31 "current_week always re-fetched"** — preserved. `data/matchups.py:45-47` is
  unchanged, and QA's `keep="first"` mutation fails both the new AC2 test and the pre-existing
  `test_current_week_always_refetched_even_when_cached`, so "fresh fetch wins" is guarded rather
  than incidental.
- **2026-03-03 "delta fetch uses max(week) from cache data, not last_updated"** — `_last_cached_week`
  is untouched and still reads the frame. The fix does not introduce a timestamp dependency.
- **2026-07-23 "Deployment: M1 shape"** — this is the entry the ticket exists to satisfy. Its 1 GB
  volume sizing is justified on `matchups` growth being "bounded once the parquet-bloat bug is
  fixed". The parquet is now bounded to `distinct(team_key, week)` = `weeks × teams`, which for a
  12-team, 25-week league is 300 rows regardless of session count. The sizing assumption now holds
  in code, not just in prose.
- **2026-07-23 "Cache: stays league-keyed; write safety from atomic rename + in-process locking"** —
  the letter of this decision is about `data/cache.py`'s own internals (`append`,
  `upsert_lastmonth_cache`, `_write_meta`), all unchanged. No contradiction, so no superseding entry
  is required and this does not halt the ticket. But the diff does erode the *property* the entry
  bought, which is finding 1.

### Verification adequacy: STRONG

QA's report is the most convincing I have reviewed on this project, and it did the thing that
matters: it distrusted the return value. Three points worth recording:

- The bug was **invisible from `get_matchups()`'s return value** — QA's pre-fix control run grows
  `32 → 72` rows on disk while the returned frame sits at 32 in both implementations. Any test
  asserting on the returned frame would have passed against the bug. AC4's on-disk assertion is
  therefore load-bearing, and QA proved it bypasses the read path by deleting the read-side
  `drop_duplicates` block and observing all 16 tests still pass.
- Mutation testing was run by both parties, on different mutations, in `rsync` copies outside the
  working tree. Restoring `cache.append` fails exactly the 4 new tests and none of the 12 old ones.
- The off-season substitute for the manual walk drove the **real** route handler and the **real**
  `get_matchups` with only Yahoo's HTTP layer faked, and reported per-load bytes and a hash of the
  rendered table. That is a legitimate stand-in for a file-growth measurement, and QA correctly
  labelled the live-Yahoo walk as owner-must-verify rather than claiming it.

The edge cases `LEARNINGS.md` would predict were covered: column-union on a mid-season stat-category
change, duplicate rows within a single fetch, `current_week=0` season-not-started, and `last_updated`
still being bumped so the prev-week branch keeps working. Off-season limits were declared, not
papered over.

### Code quality: CLEAN

The helper is 8 lines of plain pandas with an existing-first concat and `keep="last"`, mirroring the
semantics the read path already uses — no new abstraction, no new dependency, no config knob, and
nothing a reader has to hold in their head. The `keep="last"` ordering requirement is explained in
the docstring in terms of *why* (unconditional `current_week` + all-day `prev_week` re-fetch), not
what. The read-side dedup was correctly retained per the ticket, and its comment now says the one
thing that comment needs to say: it is self-heal defence for pre-038 files, not the fix.

Security: no logging added, no user input, no SQL, no auth surface, no new dependency. Nothing to
flag.

---

### Issues

**1. should-fix (logged, not blocking) — the write path lost read-modify-write atomicity.**

`_merge_into_cache` (`data/matchups.py:99-105`) calls `cache.read()` and then `cache.write()`.
`cache.write()` takes the per-league lock; the read that produced the merged frame does not. The
`cache.append()` it replaced held that lock across both halves. QA forced the interleaving and
measured it: pre-fix leaves weeks `[1, 2, 3]` on disk, post-fix leaves `[1, 2]`.

I am not requesting a change, for four reasons that I want on the record because this is the kind of
finding that gets waved through for the wrong reason:

1. **The harm the 2026-07-23 decision was written to prevent does not occur here.** That entry's
   case rests on corruption that "persists on the volume and does not self-heal" until someone
   deletes a file by hand. This window produces a valid, deduplicated, schema-correct parquet that
   is merely missing a week, and `_last_cached_week` re-derives and re-fetches it on the very next
   call (observed by QA, not inferred). Worst case is one extra Yahoo call.
2. **No acceptance criterion is affected under any interleaving**, because every write writes an
   already-deduplicated frame. The bloat this ticket exists to kill cannot come back through this
   window.
3. **The clean fix is impossible inside `Touches`.** `cache._write_unlocked` is private, so there is
   no way to hold the league lock across a read and a write from `data/matchups.py`. The ticket
   forbids `data/cache.py`. Requesting the change here would either force scope creep the ticket
   explicitly prohibits, or revert to a bug that M1's volume sizing depends on fixing. Blocking
   would be a process deadlock with a strictly worse outcome.
4. The exposure is narrow: two concurrent calls for one league normally fetch the same week set, in
   which case the losing writer's frame already contains those weeks. Divergent fetch sets are
   needed to lose anything at all.

Logged to `docs/improvements.md` as a `Type: bug` entry with the reproduction, the root cause, and
the proposed `cache.merge_on(league_key, data_type, df, subset)` primitive. Flagged there as
needing a Tech Lead ruling before scoping, because `data/cache.py` is an architectural surface.

**2. should-fix (logged) — `cache.append()` now has zero production callers.**

Confirmed independently: `grep` across `data/`, `web/`, `analysis/`, `auth/`, and `scripts/` finds
no remaining call site; only `tests/test_cache.py` exercises it. This is a consequence of the fix,
not a defect in it, and `data/cache.py` is out of scope here.

It should not be deleted in isolation, and I have said so in the tracker entry: ticket 037's
headline acceptance criterion ("N threads each calling `cache.append(league, 'matchups', …)` …
exactly N rows") is written against `append`, so removing it silently drops that concurrency
regression test. The right sequencing is to fold the decision into the `cache.merge_on` work —
`merge_on` is `append` plus a dedup subset, so one primitive can replace both.

**3. nit (logged) — `docs/DECISIONS.md:248` line-number drift.** The 2026-05-31 entry cites
`data/matchups.py` "lines 44–46"; the docstring change moved that block to 45–47. `docs/DECISIONS.md`
is not in `Touches` and I do not edit it, so this is logged for the Tech Lead. The durable fix is to
cite the symbol instead of the line range — line numbers in a decisions log rot on every adjacent
edit, and this is the second such citation in the entry.

**4. nit (logged) — `tests/test_matchups.py` module docstring** still says tests cover "that new
rows are appended correctly". The write path merges and overwrites now. One-line wording fix
whenever the file is next opened; not worth a round trip.

---

### Finding for the Tech Lead — not resolved here

**Does a cache-state read-modify-write belong in a `data/` module, or only in `data/cache.py`?**

This diff is the first merge-style read-modify-write on cache state to live outside the cache layer.
The two existing ones, `cache.append()` and `cache.upsert_lastmonth_cache()`, are both cache-layer
primitives holding the per-league lock. `web/routes/waiver.py:188-197` reads then writes a pool, but
that is a check-then-write where a lost update costs only a redundant fetch, not a merge of existing
state. So `_merge_into_cache` is genuinely a new shape, and it landed three days after the
2026-07-23 consult ruled that read-modify-write paths are the ones that get lock-guarded.

I considered calling this implicit-decision drift, which the persona lists as an always-blocker, and
decided it does not reach that bar **on this diff**: it is one private helper with one caller and no
reuse surface, the PM prescribed this exact mechanism in the ticket, and the persona's examples of
drift are structural conventions (a new directory, a new template-naming pattern). One private
function is thin evidence of a convention.

It becomes a convention the moment a second module copies it, and at that point the codebase will
have quietly adopted "any `data/` module may merge cache state itself" without anyone ruling on it.
The question for the Tech Lead is therefore about the next ticket, not this one:

> Should merges of cached frames be required to live in `data/cache.py` behind a lock-holding
> primitive (`merge_on`), with `data/` modules restricted to whole-frame `read`/`write`? If yes, the
> `cache.merge_on` follow-up is also the vehicle that retires `_merge_into_cache` and settles the
> orphaned `cache.append`, and it wants a DECISIONS entry. If no, the exception wants writing down,
> because it narrows a property the 2026-07-23 entry established.

I am explicitly not ruling on this, and nothing in it changes the verdict below.

---

### Verdict: APPROVED

The ticket does what it was scoped to do, stays inside a deliberately tight boundary, preserves both
DECISIONS entries it was told to preserve, and closes the assumption M1's volume sizing rests on.
The tests bite — proven by mutation from two independent directions — and they assert on the file,
which is the only place the bug was ever visible.

Two known gaps ship with it, both surfaced by the people who found them rather than buried: the
concurrency window, and the live-Yahoo authenticated walk that the off-season makes impossible.
Neither is hidden, both are logged, and the first is not fixable inside this ticket's scope.

**Logged to `docs/improvements.md`:**
- `Type: bug` — "`_merge_into_cache` read-modify-write sits outside the per-league cache lock"
  (with reproduction, root cause, and the proposed `cache.merge_on` fix; needs a Tech Lead ruling
  before scoping)
- `Type: quality` — "`cache.append()` has no production callers left"
- `Type: quality` — "`docs/DECISIONS.md` cites `data/matchups.py` line numbers that have drifted"
- `Type: quality` — "`tests/test_matchups.py` module docstring still describes the append write path"

**Owner-must-verify, carried forward from QA:** the authenticated `/overview` warm-cache walk
against live Yahoo data, once the season starts. The one-line row-count check in `038-done.md` is
sufficient. Nothing in the automated evidence depends on it.
