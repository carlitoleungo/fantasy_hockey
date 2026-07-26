## Orchestration log — 038-matchups-parquet-bloat-fix

**Run started:** 2026-07-26 11:39
**Run ended:** 2026-07-26 11:57
**Outcome:** completed (with owner-facing findings — see Notes for the owner)

### Pre-flight
- Type check: pass (`bug`, not `audit`)
- Status check: pass (`ready`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- `Touches` non-empty: pass (`data/matchups.py`, `tests/test_matchups.py`)
- Audit check: pass — `.venv/bin/python scripts/audit_due.py` → `AUDIT NOT DUE` (weighted 0 / 5, highest audited ticket 37)
- Architectural-surface coverage: N/A — read `WORKFLOW.md` § "Architectural-surface escalation list" from disk; neither `data/matchups.py` nor `tests/test_matchups.py` is on it (`data/cache.py` and `data/client.py` are, and both are explicitly out of scope in the ticket). Ticket cites DECISIONS 2026-05-31 and 2026-03-03 regardless.
- Dependency check: pass — ticket 037 is in `tickets/done/`
- Process: no `## Process` section ⇒ full process ⇒ Reviewer runs. No `Skip review: yes`.

### Model selection
- Engineer: **opus** — explicit PM `## Model` field (`opus`), which overrides the heuristic
- Test Engineer: **opus** — same PM field
- Reviewer: **opus** — always
(For reference, the heuristic alone would have said `sonnet` — full process, 2 `Touches` paths, non-architectural. The explicit PM field won, as prescribed.)

### Subagents spawned (in order)
1. **Engineer (round 1)** — `fh-engineer`, opus
   - Inputs: `.team/engineer.md` (read from disk by the agent shim), `tickets/038-matchups-parquet-bloat-fix.md`, DECISIONS 2026-05-31 + 2026-03-03 entries, relevant LEARNINGS entries, the `docs/improvements.md` bug entry
   - Output: `tickets/038-done.md`
   - Summary: Replaced `cache.append(...)` with a new `_merge_into_cache()` helper — reads the cached frame, concatenates fetched rows after it, `drop_duplicates(subset=["team_key","week"], keep="last")`, then `cache.write()`. This is the prescribed Option 2 (dedup-then-overwrite), not the per-week staleness alternative. Week-selection logic (`_last_cached_week`, `weeks_to_fetch`, unconditional `current_week`, prev-week same-day re-fetch) unchanged. `data/cache.py` untouched; no cache-layer change needed. Ran a mutation check (restored `cache.append`) confirming the 4 new tests fail against the bug while the 12 pre-existing ones pass. Suite: 457 passed. Flagged a concurrency window in `_merge_into_cache` for the Reviewer rather than fixing it (would require the forbidden `data/cache.py` change). Completed the DoD improvements → archive move.

2. **Test Engineer (round 1)** — `fh-test-engineer`, opus
   - Output: `tickets/038-qa.md`
   - **Verdict: APPROVED**
   - Summary: Verified all 5 ACs against their own independent fixtures (different league key, 4 teams, `current_week=8`) rather than re-running the Engineer's. Control run with `cache.append` restored grows the parquet 32→40→48→56→64→72 rows while the returned frame stays at 32 — confirming the bug was invisible from the return value and the on-disk assertion is load-bearing. Proved the on-disk check bypasses the read path by deleting the read-side `drop_duplicates` entirely (16 tests still passed). Added two further mutations (`keep="first"` fails 2 tests, so "fresh fetch wins" is genuinely guarded). Used `assert_frame_equal` pre-fix vs post-fix on 4 scenarios for AC3; test diff is 105 additions / 0 deletions, no existing test weakened. Reproduced the concurrency window empirically and confirmed it self-heals with no bloat, duplicates, or permanent loss, so no AC is affected. Substituted 5 `GET /overview` loads through the real route handler (only Yahoo HTTP faked) for the off-season-impossible authenticated walk: identical rendered table hash, parquet flat at 18 rows. Suite: 457 passed (run twice).

3. Engineer (fix round) — **not run** (QA approved on round 1)

4. Test Engineer (round 2) — **not run**

5. **Reviewer** — `fh-reviewer`, opus
   - Output: `tickets/done/038-review.md`
   - **Verdict: APPROVED**
   - Summary: Scope CLEAN, architecture CLEAN. Independently re-ran the suite (457 passed). Diff is exactly `Touches` plus the prescribed DoD move; `data/cache.py` untouched. Both cited DECISIONS entries preserved in fact, and the 2026-07-23 M1 volume-sizing assumption now holds in code (parquet bounded to `weeks × teams`). Ruled the concurrency window a **should-fix, non-blocking** on the grounds that it self-heals and the clean fix is impossible inside `Touches` (`cache._write_unlocked` is private). Ruled orphaned `cache.append()` a **should-fix** with a sequencing warning. Ruled the DECISIONS.md line-drift a **nit**. Raised one architectural question for the Tech Lead without resolving it. Set Status to `done` and moved all artifacts to `tickets/done/`.

### Files changed
- `data/matchups.py` (+32 −4)
- `tests/test_matchups.py` (+105 −0)
- `docs/improvements.md` (DoD move out, plus 4 new Reviewer-logged entries)
- `docs/archive/improvements-closed.md` (+8 — ticket-038 resolution note)
- `tickets/038-matchups-parquet-bloat-fix.md` → `tickets/done/` (Status `ready` → `done`)
- `tickets/done/038-done.md`, `tickets/done/038-qa.md`, `tickets/done/038-review.md` (new artifacts)

Cumulative source diff: 137 lines, under the ~200-line human-review heuristic.

### Halt conditions tripped (if any)
None mid-run. The sequence ran clean: no fix round, no hedged verification claims, no scope escape, no dependency/env-var/config request.

Two items reached the Reviewer's `should-fix` bar and one architectural question surfaced, both of which the halt rules direct to the owner. They arrived **with** an APPROVED verdict at the final step, so there was no subsequent step to halt before — the ticket is closed and the items are surfaced below rather than blocking. Nothing was auto-promoted past a CHANGES_REQUESTED.

### Notes for the owner

**Three items need your decision. None blocks ticket 038, which is done and approved.**

1. **Concurrency window in `_merge_into_cache` (should-fix, logged as a `Type: bug` in `docs/improvements.md`).** The `cache.read` happens outside the per-league write lock, so two concurrent `get_matchups()` calls for one league can lose one writer's freshly fetched week. QA reproduced it rather than reasoning about it: pre-fix keeps weeks `[1,2,3]`, post-fix leaves `[1,2]`, and the lost week self-heals on the next call. No bloat, no duplicates, no permanent loss. The Reviewer's argument for shipping it: the harm ticket 037's hardening was written to prevent is corruption that *persists*, and blocking here would force either scope creep the ticket prohibits or a revert to the bug M1's volume sizing depends on fixing. The clean close is a `cache.merge_on(...)` primitive holding the lock across read and write, which needs a Tech Lead ruling before it can be scoped.

2. **Architectural question for a Tech Lead session — I did not spawn one, per my rules.** `_merge_into_cache` is the first merge-style read-modify-write on cache state to live *outside* `data/cache.py`; `append` and `upsert_lastmonth_cache` are both lock-holding cache-layer primitives. It landed three days after the 2026-07-23 consult ruled that read-modify-write paths are the ones that get lock-guarded. The Reviewer decided this does not reach implicit-decision drift on this diff (one private helper, one caller, no reuse surface, PM-prescribed mechanism), but it becomes a convention the moment a second module copies it. The question to settle: must merges of cached frames live behind a lock-holding `cache.merge_on`, with `data/` modules restricted to whole-frame read/write?

3. **`cache.append()` now has zero callers outside `tests/test_cache.py` (should-fix, logged).** Do **not** delete it in isolation — ticket 037's headline AC is written against `append`, so removing it silently drops that concurrency regression test. The right vehicle is the `cache.merge_on` work, since `merge_on` is `append` plus a dedup subset. This is sequenced behind decision (2).

**Carried forward:** the ticket's manual authenticated `/overview` warm-cache walk against live Yahoo was not run — it is the NHL off-season, so an authenticated week-keyed page only reaches the empty state. Both QA and the Reviewer marked this owner-must-verify rather than claiming it, and no automated evidence depends on it. Worth re-checking once the season starts.

**Also logged by the Reviewer to `docs/improvements.md`:** a `Type: quality` nit that `docs/DECISIONS.md:248` cites "lines 44–46" of `data/matchups.py`, which the docstring change shifted to 45–47. The Reviewer's durable suggestion is to cite the symbol rather than a line range, since line numbers in a decisions log rot on every adjacent edit. That file is Tech Lead territory; the Reviewer did not edit it.

**Version control:** untouched, as per my rules. The working tree holds the full change uncommitted, including the `tickets/038-*.md` → `tickets/done/` move (git sees it as one delete plus four untracked adds).

### Round-1 QA report (archived if a round-2 ran)
N/A — QA approved on round 1, so no round-2 ran and no report was overwritten. The single QA report is at `tickets/done/038-qa.md`.
