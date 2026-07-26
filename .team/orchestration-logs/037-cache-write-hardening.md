## Orchestration log — 037-cache-write-hardening

**Run started:** 2026-07-25 (session start)
**Run ended:** 2026-07-25
**Outcome:** completed

### Pre-flight
- Type check: pass (`refactor`, not `audit`)
- Status check: pass (`ready`)
- Required-sections check: pass (Status, Type, Touches, Why, Acceptance criteria, Out of scope, Notes for the Engineer, Verification all present)
- `Touches` non-empty: pass (`data/cache.py`, `tests/test_cache.py`)
- Audit check (`scripts/audit_due.py`, run with `.venv/bin/python`): **AUDIT NOT DUE** at run start (4.5 / 5). Note: completing this ticket pushes the counter to 5.5 / 5 → AUDIT DUE for the next ticket.
- Architectural-surface coverage: pass. `data/cache.py` is on the WORKFLOW.md escalation list ("Parquet cache layer"). Two active covering entries in `docs/DECISIONS.md`, both cited by the ticket's Notes for the Engineer:
  - "Cache: stays league-keyed; write safety comes from atomic rename + in-process locking, not per-user keying" (2026-07-23)
  - "Cache: league-independent data gets a shared tier at M2; M1 only preserves the affordance" (2026-07-23)
- Process: ticket has no `## Process` section ⇒ full process ⇒ Reviewer runs.
- Model selection: no `## Model` section ⇒ heuristic. `Process: full` + a `Touches` path on the architectural-surface list ⇒ **opus** for Engineer and Test Engineer. Reviewer **opus** (always).

### Subagents spawned (in order)
1. **Engineer (round 1)** — `fh-engineer`, opus
   - Inputs: `.team/engineer.md`, `tickets/037-cache-write-hardening.md`, the two 2026-07-23 DECISIONS cache entries + the 2026-04-10 single-uvicorn-worker coupling, `docs/LEARNINGS.md` "Tests must patch the importing module's namespace"
   - Output: `tickets/037-done.md`; ticket Status → `qa`
   - Summary: All writes now go to a temp file created via `mkstemp(dir=path.parent)` and land through `os.replace()`. A module-level `dict[str, threading.Lock]` keyed on `league_key` (guarded by its own module lock) serialises `append()`, `upsert_lastmonth_cache()`, `_write_meta()`, and `write()`; `read()` stays lock-free. Lock-holding bodies split into private `_write_unlocked()` / `_write_meta_unlocked()` cores to avoid self-deadlock without an `RLock`. New `_league_dir()` resolves `league_key=None` to `CACHE_DIR/_shared/{data_type}.parquet`. Full suite 453 passed (437 before, 16 new). Flagged two items for QA: (a) did not run the authenticated warm-cache route walk (no live Yahoo OAuth session), (b) AC4 "omitted or `None`" implemented as `None` only.

2. **Test Engineer (round 1)** — `fh-test-engineer`, opus
   - Output: `tickets/037-qa.md`
   - Verdict: **APPROVED**
   - Summary: Re-verified all 5 ACs with independently written harnesses rather than re-running the Engineer's assertions — 16 barrier-released appends → exactly 16 rows; 490 reads across 60 alternating writes → only complete frames, 0 exceptions; 16 concurrent `_write_meta` → valid JSON, 16/16 keys; `None` league round-trips through `_shared/`; `453 passed`. Judged the Engineer's route-check substitute inadequate (route tests mock the cache module) and closed the gap themselves with an authenticated harness leaving `data/cache.py` unmocked against a tmp `CACHE_DIR`: cold `/overview` and `POST /api/waiver/players` wrote real parquet, warm requests returned 200 with zero refetches, 8 concurrent authenticated requests all 200 with no `.tmp` debris. Adjudicated AC4 as met. Confirmed non-vacuity by reverting the two hardening mechanisms in-place via a pytest plugin (8 failed with real `ArrowInvalid` / `JSONDecodeError`; all 26 pre-existing tests still passed). Confirmed on-disk layout, all 11 call sites, and dependency/env/config surface unchanged; pre-037 parquet files still readable, so the Fly volume needs no clearing. 13 repeat runs, no flakes.

3. **Reviewer** — `fh-reviewer`, opus
   - Output: `tickets/done/037-review.md`
   - Verdict: **APPROVED** — scope CLEAN, architecture CLEAN, security CLEAN. No blockers, no should-fixes; 4 nits not worth a round trip.
   - Summary: Traced locking statically — `_lock_for` is called at exactly 4 public entry points, nothing reachable under a held lock re-enters it, and the registry guard is released before the league lock is acquired, so the non-reentrant `Lock` and the `_unlocked` split are correct rather than a masked `RLock` need. `mkstemp(dir=path.parent)` has 2 callers, both preceded by `_ensure_dir` on the same directory; `.tmp` cleanup covers failures in both write and rename. Agreed AC4 is met as implemented. Confirmed the `_shared/` tier is provably unreachable from production call sites. Re-ran the full suite independently: 453 passed. Logged one `Type: quality` item to `docs/improvements.md` (no `fsync` on temp file before rename or on the directory after — durability, explicitly out of 037's scope). Per its own persona contract and WORKFLOW.md step 5, the Reviewer set Status → `done` and moved the artifacts to `tickets/done/` (my spawn prompt had told it not to; its persona overrides, and the end state is the intended one).

### Files changed
- `data/cache.py` (+139 −31)
- `tests/test_cache.py` (+243 −0)
- `docs/improvements.md` (Reviewer's quality entry)
- `tickets/037-cache-write-hardening.md` → moved to `tickets/done/` with Status `done`; `037-done.md`, `037-qa.md`, `037-review.md` created in `tickets/done/`

### Halt conditions tripped (if any)
- None halted the run. One heuristic noted and consciously not halted on: **cumulative diff ~350 lines vs. the ~200-line heuristic.** Source churn is +139/−31 (~108 net) in a single `Touches` file; the remaining +243 is the concurrency test suite the ticket explicitly required. The Reviewer was asked to judge whether any of that bulk was unwarranted and found none. Surfaced here and in the owner report so the size is a human decision, not a silent one.

### Notes for the owner
- **An audit is now due (5.5 / 5).** Ticket 039 (`fly.toml` deployment) is on an architectural surface, so per the cadence rule the audit should run before 039 is scoped or orchestrated. Ticket 038 is a non-architectural bug fix and is not blocked.
- **One genuinely manual check remains:** a browser walk of `GET /waiver` and `GET /overview` against a live Yahoo OAuth session. QA covered everything reachable without live OAuth (real-disk cache I/O through authenticated routes) and rated the residue low risk, since the OAuth handshake never touches `data/cache.py`. Owner-verify.
- **AC4 phrasing:** "omitted or `None`" is unsatisfiable as written — defaulting the first positional argument would force defaults onto `data_type`/`df`, a caller-visible signature change the ticket's own Out of scope forbids. Engineer, QA, and Reviewer independently converged on implementing the `None` form (which matches both of the AC's own examples). Suggest the PM drop "omitted" from future phrasing.
- **Recorded for M2:** a `None` league key used to fail loudly with `TypeError`; it now silently resolves to `_shared/`. Inherent to the affordance and accepted by the decision, but the fail-fast net is gone.
- **New improvements entry:** `_atomic_write()` does no `fsync` on the temp file before the rename or on the directory after, so a Fly machine restart could leave the rename durable while data blocks are not. Correctly scoped out of 037 (the decision covers reader atomicity, which `os.replace()` delivers in full); it is a durability concern for a future ticket.
- Nothing was committed — the working tree holds all changes for your review, per the no-git rule.

### Round-1 QA report (archived if a round-2 ran)
N/A — no fix round was needed; QA returned APPROVED on round 1. The full report is at `tickets/done/037-qa.md`.
