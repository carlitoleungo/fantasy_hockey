## Orchestration log — 045-dockerignore-secret-globs-fly-autostart

**Run started:** 2026-07-27 08:33
**Run ended:** 2026-07-27 08:55
**Outcome:** completed

### Pre-flight
- Status check: **pass** — `Status: ready`, `Type: bug` (not `audit`).
- Required-sections check: **pass** — `Status`, `Type`, `Touches`, `Why`, `Acceptance criteria`, `Out of scope`, `Notes for the Engineer`, `Verification` all present. `Touches` non-empty (`.dockerignore`, `fly.toml`).
- Audit check: **pass** — `.venv/bin/python scripts/audit_due.py` reported `3 / 5`, `AUDIT NOT DUE`. (Bare `python` is not on PATH; the venv interpreter is required.) No overdue audit to record.
- Architectural-surface coverage: **pass** — `fly.toml` is named on the `WORKFLOW.md` escalation list (under "new env var / new config knob"). Active covering decision `docs/DECISIONS.md` "Deployment: M1 shape — single pinned machine, 1 GB volume, fly.toml in repo" (2026-07-23) exists and is cited by title in the ticket's `Notes for the Engineer` first bullet, with the PM's reasoning for why the flip does not breach the one-machine pin. `.dockerignore` is not on the surface list. No Tech Lead consult owed.
- Process: no `## Process` section ⇒ **full process**. No `Skip review: yes`. Reviewer step therefore mandatory.

### Model selection
- No `## Model` section in the ticket ⇒ heuristic applied.
- **Engineer: `opus`** — `Process: full` and a `Touches` path (`fly.toml`) is on the WORKFLOW.md architectural-surface list (heuristic branch 2, clause b). The 2-path count alone would not have qualified.
- **Test Engineer: `opus`** — same branch.
- **Reviewer: `opus`** — always, never downgraded.

### Subagents spawned (in order)
1. **Engineer (round 1)** — `fh-engineer`, model `opus`
   - Inputs: `.team/engineer.md` (read from disk by the agent shim), the ticket, `docs/DECISIONS.md` 2026-07-23 "Deployment: M1 shape" and 2026-04-10 "Runtime: single uvicorn worker", `tickets/done/039-qa.md` root-coverage section, `tickets/done/039-review.md` § "On the single-machine pin".
   - Output: `tickets/045-done.md`
   - Summary: Implemented the prescribed shape exactly — `.dockerignore` lines `.env` + `.env.*` → single `**/.env*`, `*.pem` → `**/*.pem`, plus a four-line comment in the Secrets block recording that the `**/` prefix is load-bearing there and that a miss bakes a credential rather than bloating the image. `fly.toml`: one line, `auto_start_machines = false` → `true`; `auto_stop_machines` left `false`, header comment intact. Reported all five ACs passing with output: negative control ran both directions (probes PRESENT pre-change, absent after), root `./.env` and `./.env.example` both absent from the context, `CHECKED=53 MISSING_COUNT=0` on the derived runtime set, 74 files / 19 top-level entries matching QA 039, `tomllib` 11/11, `459 passed`. Close-out: `.dockerignore` improvements entry archived; `fly.toml` entry trimmed in place. Added no dependency, env var, or config knob. Stated plainly that no git baseline exists for either file.

2. **Test Engineer (round 1)** — `fh-test-engineer`, model `opus`
   - Output: `tickets/045-qa.md`
   - Verdict: **APPROVED**
   - Summary: Re-derived all five ACs from an independent harness. AC1 non-vacuous (host `./.env` 914 B and `./.env.example` 755 B exist; both absent from context). AC2 negative control: pre-change context 77 files with all three probes PRESENT, new patterns 74 files with all three ABSENT. AC3 `CHECKED=55 MISSING_COUNT=0`, both-directions tree diff 58 vs 58 IDENTICAL, no disagreement with any QA 039 number. AC4 `tomllib` 18/18 with a recursive forbidden-key walk returning `hits=[]`. AC5 `459 passed`, run twice. Cleanup gate PASS. Two deliberate divergences from the Engineer's method, both strengthening the evidence: used BuildKit's per-Dockerfile `.dockerignore` sidecar so the repo's own file was never mutated, and added a discriminator asserting pre-change semantics were genuinely in force so "probes absent" could not be a silently-ignored-sidecar false pass. Root credential `./.env` sha256 identical at start and end.

3. Engineer fix round — **not run.** QA round 1 was APPROVED.

4. Test Engineer round 2 — **not run.**

5. **Reviewer** — `fh-reviewer`, model `opus`
   - Output: `tickets/done/045-review.md`
   - Verdict: **APPROVED** — no `blocker`, no `should-fix`.
   - Summary: Reconstructed and diffed the change independently from the pre-edit scratch copies, anchored to sizes QA 039 recorded (873 B / 1587 B). Re-derived the load-bearing architectural question rather than assuming it: Fly Proxy autostart wakes an existing stopped machine and cannot provision one (creation requires `fly scale count`, `fly machine clone`, or a deploy), a restarted machine reattaches the same volume, so none of the three failure modes DECISIONS 2026-07-23 names can arise; `true` is also Fly's own default. No superseding entry or Tech Lead consult owed. Ran its own busybox build, nested-probe test with control, `tomllib` 11/11, and `459 passed`. Verified all nine out-of-scope boundaries by inspection. Confirmed both tracker moves and closed QA's un-closable limitation by showing `git show HEAD:docs/improvements.md` contains none of Review 039's three entries, which fully explains the additions-only diff. Close-out done: Status `done`, all four artifacts moved to `tickets/done/`.

### Files changed
- `.dockerignore` — untracked, no committed baseline. Two pattern rewrites (`.env` + `.env.*` → `**/.env*`; `*.pem` → `**/*.pem`) plus 4 inserted comment lines. 873 → 1141 bytes.
- `fly.toml` — untracked, no committed baseline. One line changed (`auto_start_machines`). 1587 → 1586 bytes.
- `docs/improvements.md` — `.dockerignore` entry removed (archived); `fly.toml` entry trimmed in place to its `auto_stop_machines` half; one new entry filed by the Reviewer (see owner notes).
- `docs/archive/improvements-closed.md` — `.dockerignore` entry added with a `**Resolved:** Ticket 045` note.
- Ticket artifacts: `tickets/done/045-dockerignore-secret-globs-fly-autostart.md`, `045-done.md`, `045-qa.md`, `045-review.md`.

Cumulative source-surface diff is well under the ~200-line heuristic. I verified the working tree myself after each spawn: no file outside `Touches` plus the two prescribed tracker files was touched, no stray probe files, no `.ORIG` scratch copies, and no `qa045`/`ctx` Docker images survive.

### Halt conditions tripped (if any)
None.

### Notes for the owner
- **Ticket 045 is `done` and its four artifacts are in `tickets/done/`.** Nothing in the running app changed; the deliverable is a build context that cannot carry a nested credential and a `fly.toml` that lets Fly bring the one pinned machine back by itself.
- **Two things remain unverifiable locally, by the ticket's own design, and are yours at deploy time:** `fly config validate` never ran (`flyctl` is not installed), and the restart behaviour itself is observable only post-deploy. QA also noted Fly's remote builder was not confirmed to apply `**/` identically to local Docker 29.6.2, and the production image was never built (busybox over the context is the correct surface for AC1–AC3). None of these are hedges on an acceptance criterion — AC4 was deliberately scoped to TOML validity and value correctness.
- **The Reviewer filed one new `docs/improvements.md` entry** (`min_machines_running = 1` is inert as configured, and DECISIONS 2026-07-23 names it as the pin mechanism, `fly.toml:38` / `docs/DECISIONS.md:170`), because the prescribed trim removed the last record of it. Nothing is broken — the pin actually comes from the absent autoscaling keys plus the single `[[vm]]` — but a future reader could read the DECISIONS text as a guarantee that one machine is always up. It is routed to the Tech Lead alongside the existing `docs/ARCHITECTURE.md:102` upkeep item. **That means there are now two DECISIONS/ARCHITECTURE upkeep items waiting on a Tech Lead session you have to start yourself.**
- **The `auto_stop_machines` boolean-vs-`"off"` deprecation stays open** in `docs/improvements.md`, correctly. It can only be resolved with `flyctl` in hand at `fly config validate` time, so it is a natural companion to your first deploy.
- **Audit budget:** `scripts/audit_due.py` now reads `4 / 5`, `AUDIT NOT DUE`. Tickets 042 (1.0) and 044 (1.0) are both open and full-process, so **the next completion crosses the threshold and the one after it is blocked behind an audit checkpoint.** 045 was sequenced first for exactly this reason, per its Dependencies section, and that worked — but 042/043/044 are non-architectural, so an overdue audit will not block them the way it would have blocked this one.
- **Process nit the Test Engineer disclosed rather than glossed:** my spawn prompt directed them to read `045-done.md` before the ticket, which is what `.team/orchestrator.md` step 2 prescribes but runs against their own persona's Step 1 ordering. They named the conflict in their report and mitigated it with a fully independent harness. Worth reconciling the two persona files so the next run does not have to; the orchestrator persona and `.team/test-engineer.md` currently disagree on read order.
- No commits were made. Both `.dockerignore` and `fly.toml` are still untracked from 039, which is why neither this run nor 039's could byte-diff against a baseline. **Committing them would remove that limitation for every future ticket on these files** — the third such ticket in a row to work around it.

### Round-1 QA report (archived if a round-2 ran)
No round-2 ran; QA round 1 returned APPROVED. The report is intact at `tickets/done/045-qa.md`.
