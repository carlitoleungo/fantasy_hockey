## Orchestration log — 039-deployment-fly-toml

**Run started:** 2026-07-26 18:04
**Run ended:** 2026-07-26 18:38
**Outcome:** halted, then completed on owner decision (Reviewer verdict APPROVED, but two
`should-fix` findings tripped the halt-and-surface rule; surfaced to the owner, who directed
promotion. Status → `done` and `tickets/039-*.md` moved into `tickets/done/` at 18:52.)

**Owner decisions after the halt (2026-07-26 18:50):**
1. Promote 039 as-is. Done.
2. Route **both** should-fix items into **one follow-up ticket** rather than splitting them or
   leaving them to the opportunistic improvements path. The orchestrator does not scope tickets, so
   the owner runs a fresh `/pm` session. Because that ticket touches `fly.toml` (architectural
   surface, `WORKFLOW.md:188`), the PM must first settle whether DECISIONS 2026-07-23 already
   covers flipping `auto_start_machines` — the Reviewer argues it does, since auto-start never
   creates a machine — or route a short Tech Lead consult. Full process, not `Process: light`.

### Pre-flight
- Type check: pass — `Type: feature`, not `audit`
- Status check: pass — `ready`
- Required-sections check: pass — all eight present (`Status`, `Type`, `Touches`, `Why`,
  `Acceptance criteria`, `Out of scope`, `Notes for the Engineer`, `Verification`)
- `Touches` non-empty: pass — `fly.toml`, `.dockerignore`
- Audit check: pass — `.venv/bin/python scripts/audit_due.py` → `AUDIT NOT DUE` (weighted 2 / 5,
  highest audited ticket 37). No overdue audit to record. (Note: bare `python` is not on PATH in
  this environment; the script must be run with `.venv/bin/python`.)
- Architectural-surface coverage: pass — `fly.toml` falls under the WORKFLOW.md surface "New
  dependency (`requirements-web.txt`), new env var (`Dockerfile`, `fly.toml`), new config knob".
  Covered by the active `docs/DECISIONS.md` entry **"Deployment: M1 shape — single pinned machine,
  1 GB volume, fly.toml in repo" (2026-07-23)**, which the ticket cites explicitly in `Notes for
  the Engineer`. The Tech Lead consult was already done and recorded under `Dependencies`
  (RESOLVED 2026-07-23). No Tech Lead spawn needed or made.

### Model selection
- Ticket has no `## Model` section and no `## Process` section (⇒ full process by default).
- Heuristic branch: `Process: full` **and** a `Touches` path (`fly.toml`) is on the WORKFLOW.md
  architectural-surface list ⇒ **`opus`** for Engineer and Test Engineer.
- Reviewer: **`opus`** (always).

### Subagents spawned (in order)
1. **Engineer (round 1)** — model `opus`
   - Inputs: `.team/engineer.md` (read from disk by the `fh-engineer` shim),
     `tickets/039-deployment-fly-toml.md`, DECISIONS 2026-07-23 "Deployment: M1 shape" and
     2026-04-10 "Runtime: single uvicorn worker", the existing `Dockerfile` (read-only),
     `.env.example`, `web/routes/health.py`
   - Output: `tickets/039-done.md`; ticket Status → `qa`
   - Summary: Created `fly.toml` (50 lines) and `.dockerignore` (45 lines). `fly.toml` implements
     the 2026-07-23 decision item for item: `primary_region = "iad"`, `min_machines_running = 1`,
     `auto_start_machines`/`auto_stop_machines` both `false`, exactly one `[[vm]]`, `[mounts]`
     `source = "data"` → `destination = "/data"`, `[env]` = exactly the `DB_PATH`/`CACHE_DIR`/
     `HTTPS_ONLY` trio (no Yahoo secrets), `internal_port = 8000`, one `GET /health` check. Header
     comment cites both decisions and forbids `--workers N`. Verified via `tomllib` assertions, a
     throwaway busybox build over the real context, `459 passed` pytest, and a live boot honouring
     env paths with `/health` → 200. Flagged two values no document specifies: `app =
     "fantasy-hockey-waiver"` and a `[[vm]]` of shared / 1 cpu / 1gb.

2. **Test Engineer (round 1)** — model `opus`
   - Output: `tickets/039-qa.md` (later overwritten by round 2)
   - Verdict: **NEEDS FIXES**
   - Summary: Four of five ACs passed. AC4 failed empirically: `.dockerignore` patterns are
     anchored to the build-context root with no implicit `**` prefix, so `__pycache__/` and `*.pyc`
     matched nothing (the repo has no root-level `__pycache__`) and a real `docker build` context
     carried 7 `__pycache__` directories and 32 `.pyc` files. Isolated the cause with a control
     build. Severity Minor — no secret leaked (`.env`, `app.db*`, `.cache/`, `.git/` all confirmed
     absent) — but AC4 names `__pycache__/` explicitly, so it could not be approved past. Also
     noted that `HTTPS_ONLY = "true"` must be the string form because `web/routes/auth.py:81,100`
     compares `== "true"`, and the Engineer got that right.

3. **Engineer (fix round)** — model `opus`
   - Inputs: `.team/engineer.md`, the ticket, `tickets/039-qa.md` (round-1 report)
   - Output: `tickets/039-fix.md`
   - Summary: `.dockerignore` only. Four patterns gained a `**/` prefix (`**/__pycache__/`,
     `**/*.pyc`, `**/*.pyo`, `**/.pytest_cache/`) plus a comment recording why the prefix is
     load-bearing. `fly.toml` untouched. Reproduced the failure first (7 / 32, matching QA), then
     confirmed `0 / 0 / 0 / 0` after, including a root-level probe proving `**/__pycache__/` is a
     strict superset of the literal form. `459 passed`. Probes and throwaway images cleaned up.

4. **Test Engineer (round 2)** — model `opus`
   - Output: `tickets/039-qa.md` (overwritten; round-1 substance archived below)
   - Verdict: **APPROVED**
   - Summary: AC4 fixed, verified over a real build context — host now has 8 `__pycache__` dirs and
     64 `.pyc` files, and the context build yielded `pyc=0 pyo=0 pycache_dirs=0
     pytest_cache_dirs=0` with all seven AC4-named items absent. Planted seven probes (including
     root-level `__pycache__/rootprobe.pyc`) and all were excluded, so root coverage is not lost.
     Judged AC4's stated outcome met even though the literal string `__pycache__/` no longer
     appears. No over-exclusion: 55-file empirically-derived runtime set all present, and all 58
     non-bytecode source files identical in both directions between host and context. `fly.toml`
     confirmed untouched three ways (size, mtime predating the fix, 12/12 `tomllib` assertions).
     `459 passed`; boot on env paths with `/health`, `/`, `/demo/overview` all 200.

5. **Reviewer** — model `opus`
   - Output: `tickets/039-review.md`
   - Verdict: **APPROVED**, no blockers — but with **two `should-fix`** findings and one nit
   - Summary: Re-verified both files by hash against what QA approved, re-parsed `fly.toml`, and
     ran an independent context build (secret sweep empty; 74 runtime files / 592 KB present) with
     live `.env` and `app.db` on disk as real targets. Judged the pin watertight to the limit
     config allows: auto-start creates no machine, no autoscale keys exist (asserted by exact key
     set, not grep), `bluegreen`/`canary` are refused by Fly for volume apps and no `[deploy]`
     block means default `rolling` in place; the only uncoverable route is a manual `fly scale
     count 2`, mitigated by the header comment. Endorsed both unspecified values.

### Files changed
- `fly.toml` — new, 50 lines (untracked)
- `.dockerignore` — new, 45 lines (untracked; 4 patterns revised in the fix round)
- `docs/improvements.md` (+60 −0) — three entries written by the Reviewer, in their own lane
- `tickets/039-deployment-fly-toml.md` — `## Status`: `ready` → `qa` (still `qa`; not promoted)
- Workflow artifacts: `tickets/039-done.md`, `tickets/039-fix.md`, `tickets/039-qa.md`,
  `tickets/039-review.md`

Cumulative deliverable diff is 95 lines of config, well inside the ~200-line heuristic. The diff
stayed inside `Touches` throughout — I verified this myself with `git status` after each round.

### Halt conditions tripped
- **"Reviewer raises any `blocker` or `should-fix`"** — surfaced at step 5, after the Reviewer's
  APPROVED verdict. Two findings are labelled `should-fix`, both logged to `docs/improvements.md`
  by the Reviewer and both explicitly marked "not blocking" by them:
  1. `auto_start_machines = false` leaves the pinned machine with no automatic restart path.
     `min_machines_running = 1` does not compensate (it applies only when `auto_stop_machines` is
     `stop`/`suspend`, so it is inert here). A Fly host migration, OOM stop, or manual stop leaves
     the app down until someone runs `fly machine start`; the default `on-failure` policy still
     covers process crashes. The Reviewer notes `auto_start_machines = true` would **not** breach
     the pin (auto-start only starts an existing stopped machine, never creates one), so the owner
     can flip it without re-opening DECISIONS 2026-07-23.
  2. `.dockerignore`'s secret patterns (`.env`, `.env.*`, `*.pem`) are still root-anchored while
     the bytecode patterns gained `**/` in the fix round — the same bug class QA caught, but on the
     patterns where a future miss leaks a credential rather than bloating an image. No exposure
     today: the only matches in the repo are root-level and the context build carried none of them.
- Per the persona's halt rule I did **not** promote Status to `done`, did **not** move the ticket
  or its artifacts into `tickets/done/`, and did **not** open a second fix round (the one allowed
  fix round was already spent at step 3). The owner then reviewed both findings and directed
  promotion, which I carried out under step 5 of the loop (Reviewer verdict was APPROVED). Neither
  should-fix was fixed in 039; both are tracked in `docs/improvements.md` and go to a PM-scoped
  follow-up ticket per the owner's decision above.

### Notes for the owner
- **No audit is overdue.** `audit_due.py` reports 2 / 5 weighted.
- **Owner-must-verify carry-forwards, unresolvable in this environment:** `flyctl` is not
  installed and the ticket forbids `fly` commands, so **`fly config validate` was never run** —
  Fly's schema acceptance of this file is unverified. Both `tomllib` validity and key/value
  correctness are confirmed. That the pin yields exactly one machine is likewise only observable
  post-deploy via `fly status`. Run `fly config validate` as the first deploy step.
- **`app = "fantasy-hockey-waiver"` is a placeholder** the Engineer had to invent (a `fly.toml`
  cannot deploy without an `app` key, and no document names the app). Change it to whatever
  `fly apps create` actually registers. The Reviewer notes a mismatch fails loudly, so the real
  gap is that `docs/ROADMAP.md`'s M1 launch sequence has no `fly apps create` step to reconcile it
  against — a **PM** item.
- **`auto_stop_machines = false` (boolean rather than `"off"`/`"stop"`/`"suspend"`)**: the Reviewer
  ruled this an accepted observation, not a should-fix. The boolean is accepted by both older and
  newer flyctl while `"off"` is newer-only, so changing it blind in a file nothing here can lint
  trades a deprecation warning for unvalidated schema risk. Neither value can produce a second
  machine. Resolve it with flyctl in hand at `fly config validate` time.
- **`docs/ARCHITECTURE.md:102` is stale** — still reads `fly.toml  # planned, not yet in repo`, and
  the tree listing has no `.dockerignore` entry at all. Correctly outside the Engineer's `Touches`.
  The Reviewer's routing call: a `docs/improvements.md` entry addressed to the Tech Lead (already
  written), not its own ticket — a two-line factual correction in a Tech-Lead-owned file with no
  code impact.
- **Concurrent-session noise, not attributable to this run:** `docs/ROADMAP.md` and
  `docs/backlog.md` are modified, and `tickets/042-error-page-nav-free.md`,
  `tickets/043-home-demo-cta.md`, `tickets/044-base-html-default-flip.md` are new and untracked. I
  inspected the ROADMAP diff to confirm it is a PM M1-amendment (M1 now includes the UI re-design),
  unrelated to 039. Both subagent rounds were told to ignore these.
- **`.dockerignore` excludes `tests/ docs/ tickets/ .team/ reference/ scripts/`.** QA rebuilt to
  confirm this is not over-broad: nothing the runtime imports or reads lives there, and
  `web/templates` (12 files), `web/static`, `demo/data/*.json`, `demo/data/*.parquet`, and
  `requirements-web.txt` all survive into the image.
- **Reviewer nit, explicitly left alone:** `[build] dockerfile = "Dockerfile"` is redundant since
  Fly auto-detects a root Dockerfile. Harmless, arguably better explicit.

### Round-1 QA report (archived)
The round-1 `tickets/039-qa.md` was overwritten in place by the round-2 report, per the loop rule.
Its substance, as reported by the round-1 Test Engineer:

> **Verdict: NEEDS FIXES.** Four of five acceptance criteria pass. One fails, empirically and
> reproducibly.
>
> **The failure — AC4, `__pycache__/` is not actually excluded.** A real `docker build` over the
> repo-root context carries in 7 `__pycache__` directories and 32 `.pyc` files (`web/`,
> `web/routes/`, `web/middleware/`, `data/`, `db/`, `analysis/`, `auth/`). `.dockerignore` patterns
> are anchored to the context root with no implicit `**` prefix, so line 21's `__pycache__/` means
> "a `__pycache__` at the context root" — and this repo has none there, so the pattern excludes
> nothing that exists. Line 22's `*.pyc` has the same problem. Isolated the cause with a control
> build in a scratch dir: with `__pycache__/` + `*.pyc` the nested `.pyc` came through; with
> `**/__pycache__/` + `**/*.pyc` it did not. Two-line fix. `*.pyo` and `.pytest_cache/` need the
> same treatment; the remaining patterns are root-only in this repo and correct as written.
>
> Severity Minor: no secret leaked. `.env`, `app.db`, `app.db-wal`, `app.db-shm`, `.cache/`,
> `.git/` are all confirmed absent from the real context, as are any nested `.env*`/`app.db*`/
> `*.pem`/`secrets.toml`. But AC4 names `__pycache__/` explicitly and states the outcome as
> "carries none of them into the image", so the criterion is not met.
>
> **What passed:** `fly.toml` parses via `tomllib`; `primary_region == "iad"`;
> `min_machines_running` int `1`; both auto-start/stop `False`; exactly one `[[vm]]`; top-level
> keys only the expected seven (no `[processes]`, `[[services]]`, `regions` list, or concurrency
> block); `[env]` compares **equal** to the required trio so no Yahoo secret can hide in it;
> `internal_port` int `8000`; one `GET /health` check. `.venv/bin/python -m pytest tests/` →
> `459 passed, 106 warnings in 1.40s`. App booted clean on env-provided paths; `/health` → 200
> `{"status":"ok"}`, `/` → 200; the DB materialised at the env `DB_PATH` while repo-root `app.db`
> stayed byte- and mtime-identical.
>
> **Extra checks:** `HTTPS_ONLY = "true"` had to be the string form — `web/routes/auth.py:81,100`
> does `os.environ.get("HTTPS_ONLY") == "true"`, so a TOML boolean would have silently disabled
> the secure-cookie flag in production. The Engineer got this right. The `.dockerignore` is not
> over-broad despite excluding `tests/ docs/ tickets/ .team/ reference/ scripts/`.
>
> **Owner-must-verify:** `fly config validate` unreachable (no `flyctl`, `fly` commands
> forbidden). `auto_stop_machines = false` uses the boolean form current flyctl treats as
> deprecated, and `min_machines_running` is likely inert when machines never auto-stop — recorded
> as observations, not defects, since neither can create a second machine.
