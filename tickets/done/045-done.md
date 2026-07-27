## Implementation complete — 045

**What I did:**
- Widened `.dockerignore`'s secret patterns to match at any depth: `.env` + `.env.*` → a single
  `**/.env*`, and `*.pem` → `**/*.pem`. Exactly the shape the ticket prescribed; no variants.
- Added a four-line comment in the Secrets block recording that the `**/` prefix is load-bearing
  there, that a miss bakes a live credential rather than bloating the image, and that `**/`
  matches zero or more leading segments so root-level `.env` is still excluded. The existing
  bytecode comment at (old) lines 21-22 is untouched — the ticket sanctioned either placement,
  and putting it in the Secrets block keeps the explanation at the fix site.
- Flipped `fly.toml`'s `auto_start_machines` from `false` to `true` (boolean, one line), so Fly
  Proxy restarts the single pinned machine after a host migration, OOM stop, or manual stop
  rather than leaving the app down until the owner runs `fly machine start`.
- Left `auto_stop_machines = false` as-is per Out of scope, and left the `[http_service]` header
  comment block (lines 7-12) intact.
- Close-out: archived the `.dockerignore` improvements entry; trimmed the `fly.toml` entry in
  place to its `auto_stop_machines` half.

**Architectural surface:** `fly.toml` is covered by `docs/DECISIONS.md` **"Deployment: M1 shape —
single pinned machine, 1 GB volume, fly.toml in repo" (2026-07-23)**; no new Tech Lead consult.
The flip cannot breach that entry's correctness requirement (never more than one machine) because
auto-start only restarts an *existing stopped* machine and never creates one — the route Review
039 enumerated as "not a route at all … safe at either value" (`tickets/done/039-review.md`
§ "On the single-machine pin"). It touches none of the entry's other commitments (1 GB volume at
`/data`, `fly.toml` in repo, no CI) and moves an undecided implementation detail back to Fly's own
default in the direction that serves the entry's stated purpose. I added no `--workers N` and no
machine, region, or autoscaling knob — the pin also being load-bearing on DECISIONS 2026-04-10
"Runtime: single uvicorn worker".

**Files changed:**
- `.dockerignore` — two secret patterns widened to `**/`; explanatory comment added in the Secrets block.
- `fly.toml` — `auto_start_machines = true` (one line; nothing else in the file changed).
- `docs/improvements.md` — `.dockerignore` entry removed (archived); `fly.toml` entry trimmed to one key.
- `docs/archive/improvements-closed.md` — `.dockerignore` entry appended with a `**Resolved:** Ticket 045` note.

**No git baseline for either config file.** `.dockerignore` and `fly.toml` are both still
untracked, so my edits show as `??` rather than `M` and **there is nothing in git to byte-diff
against — I did not check a diff against a committed baseline, because none exists.** I copied
both files to scratch before editing and diffed against those copies, which shows the two
`.dockerignore` hunks and the one `fly.toml` line above and nothing else; that is a
same-session backup, not a VCS baseline. The stronger property AC3 actually requires (context ==
host source tree minus bytecode and excluded secrets) is verified empirically below, the same
substitution QA 039 made when it hit this limitation.

**Acceptance criteria status (self-check):**

- [x] **AC1 — no `.env` / `.env.*` / `*.pem` at any depth in a real-repo build context, root
  included.** Built `FROM busybox` + `COPY . /ctx` from the repo root with the scratch Dockerfile
  outside the repo (Docker 29.6.2):
  `docker build -q -f <scratch>/ctx.Dockerfile -t qa045ctx .`
  `docker run --rm qa045ctx find /ctx \( -name '.env' -o -name '.env.*' -o -name '*.pem' \) -print`
  → **empty**. Broader `find /ctx -name '.env*'` → **empty**. Non-vacuous: the host really has
  targets, confirmed before building (`./.env` 914 bytes, `./.env.example` 755 bytes; a repo-wide
  find returns exactly those two and no `.pem`). Per-path check: `/ctx/.env` **absent**,
  `/ctx/.env.example` **absent** — root coverage preserved, which the ticket flagged as the worst
  possible regression. Root `.env` is still intact on the host at 914 bytes, unmodified.

- [x] **AC2 — nested probes absent, with the negative control run in both directions.** Planted
  `web/.env`, `web/deep/nest/.env.local`, `web/certs/key.pem`, each containing only the string
  `PROBE_PLACEHOLDER_NOT_A_REAL_CREDENTIAL_045` (44 bytes; no real credential was ever copied into
  a probe). Build A, **pre-change patterns still in place**:
  `PRESENT /ctx/web/.env`, `PRESENT /ctx/web/deep/nest/.env.local`, `PRESENT /ctx/web/certs/key.pem`
  — and the depth sweep listed all three. Build B, **new patterns**: all three **absent**, sweep
  empty. So the probes demonstrably reach the context under the old patterns and demonstrably do
  not under the new ones; the pass is not vacuous.

- [x] **AC3 — nothing newly over-excluded.** Two empirical checks, no hand-written list.
  (1) Derived the runtime set by importing `web.main` and collecting every repo-local module in
  `sys.modules`, plus every file under `web/templates`, `web/static`, `demo/data`, plus
  `requirements-web.txt`: `CHECKED=53 MISSING_COUNT=0`. (53 vs QA 039's 55 is only because my
  script does not add `Dockerfile` and `fly.toml` to the wanted set; 53 + 2 = 55.) No runtime file
  begins with `.env`: `RUNTIME_FILES_STARTING_WITH_.env=[]`.
  (2) Both-directions diff of the context source tree against the host source tree over
  `web data analysis auth db demo utils`, bytecode excluded: the **only** difference in either
  direction is the three probe files, host-only. 58 files in the context, matching QA 039's
  recorded 58. Whole-context totals match QA 039 exactly: **74 files** and the same **19
  top-level entries** (`.dockerignore .python-version .streamlit CLAUDE.md Dockerfile RUNNING.md
  analysis app.py auth data db demo fly.toml pages requirements-web.txt requirements.txt utils
  validate_api.py web`). `web/main.py` still reaches the context.

- [x] **AC4 — `fly.toml` valid TOML, `auto_start_machines` boolean `true`, pin keys unchanged.**
  A `tomllib` assertion script printed **11/11 passed**: parses; `auto_start_machines is True` and
  `isinstance(..., bool)`; `auto_stop_machines is False`; `min_machines_running == 1` with
  `type(...) is int`; `len(d["vm"]) == 1`; top-level keys exactly
  `['app','build','env','http_service','mounts','primary_region','vm']`; `[http_service]` keys
  exactly `['auto_start_machines','auto_stop_machines','checks','force_https','internal_port','min_machines_running']`;
  a recursive walk of the whole parsed document for `max_machines_running` / `concurrency` /
  `processes` / `services` / `regions` returned `hits=[]`; `[env]` still exactly
  `['CACHE_DIR','DB_PATH','HTTPS_ONLY']`. `grep -iE 'workers|autoscal|max_machines|processes|regions|concurrency|count'`
  hits only comment lines 4 and 11, the same two QA 039 recorded.

- [x] **AC5 — suite green.** `.venv/bin/python -m pytest tests/` → **`459 passed, 106 warnings in
  1.42s`**, 0 failed. Warnings are the pre-existing Starlette per-request-cookies deprecations.

- [x] **Cleanup gate.** Deleted all three probes and the directories they created (`web/deep`,
  `web/certs`); `find web \( -name '.env*' -o -name '*.pem' \)` → empty, and the repo-wide sweep
  returns only `./.env` and `./.env.example`. Removed both images (`docker images | grep qa045` →
  empty) and the scratch Dockerfile. `git status --porcelain` diffed **IDENTICAL** to the
  pre-start baseline I captured before touching anything (checked at that point, i.e. before the
  two intended improvements-tracker edits, which now correctly show as `M`). No `.env*`-named
  probe survived the session.

- [x] **"What done looks like."** `uvicorn web.main:app` boots (`Application startup complete`, no
  errors in the log) and `GET /health` returns **`200`** with body **`{"status":"ok"}`**.

**How to verify (for QA):**
1. Confirm the host has targets first, so a clean sweep means something:
   `ls -l .env .env.example` (914 / 755 bytes).
2. Write `printf 'FROM busybox\nCOPY . /ctx\n' > <scratch>/ctx.Dockerfile` **outside the repo**,
   then from the repo root: `docker build -q -f <scratch>/ctx.Dockerfile -t qa045ctx .`
3. AC1: `docker run --rm qa045ctx find /ctx \( -name '.env' -o -name '.env.*' -o -name '*.pem' \) -print`
   → expect empty; also check `/ctx/.env` and `/ctx/.env.example` by path.
4. AC2: plant `web/.env`, `web/deep/nest/.env.local`, `web/certs/key.pem` with placeholder text
   only. For the negative control, restore the pre-change patterns (`.env`, `.env.*`, `*.pem`) in a
   copy, build, and confirm the probes **are** present; then build with the committed file and
   confirm they are not. **Delete the probes and `web/deep` / `web/certs` afterwards.**
5. AC3: import `web.main`, collect repo-local `sys.modules` files + everything under
   `web/templates`, `web/static`, `demo/data` + `requirements-web.txt`, assert each is in the
   context; then diff host vs context trees both ways over
   `web data analysis auth db demo utils`. Expect 74 context files and 19 top-level entries.
6. AC4: `tomllib.load` `fly.toml` and assert the key set and values listed under AC4 above.
7. AC5: `.venv/bin/python -m pytest tests/`.
8. Boot check: `.venv/bin/python -m uvicorn web.main:app --port <free>` then `curl /health`.
9. Close-out: `grep "secret patterns are root-anchored" docs/improvements.md` → 0 hits;
   same grep against `docs/archive/improvements-closed.md` → 1 hit.

No demo-mode steps apply — this ticket touches no `data/` code and no route.

**Scope notes:**
- I stayed inside `Touches` (`.dockerignore`, `fly.toml`) plus the two improvements-tracker files
  the ticket's close-out bullet prescribes. I did **not** touch `Dockerfile`,
  `docs/ARCHITECTURE.md`, the `.streamlit/` patterns, the `[build] dockerfile` redundancy, or the
  Streamlit prototype files — all explicitly out of scope.
- **I added no dependency, no env var, and no new config knob.** The `fly.toml` change is the
  value of a knob already in the file; the `.dockerignore` change is pattern text only. I never
  wanted to add one.
- No `docs/LEARNINGS.md` entry added, per the ticket's explicit instruction. No Yahoo API gotchas
  apply — no `data/`, `analysis/`, or `auth/` code was touched, so the pure-layer,
  `_coerce`/`_as_list`, bulk-endpoint, and demo-parity rules have no surface here.
- Still open and correctly out of scope: the `auto_stop_machines` boolean-vs-`"off"` deprecation
  (needs `flyctl`), and `docs/ARCHITECTURE.md:102`'s stale `fly.toml # planned, not yet in repo`
  line plus its missing `.dockerignore` tree entry (Tech-Lead-owned).
- Observation, not a request: `**/.env*` also excludes a hypothetical `.envrc` (direnv). Nothing
  in the repo matches and no runtime file starts with `.env`, so there is no effect today. Noted
  only because it is a slightly wider glob than the three literals it replaces — it is the shape
  the ticket prescribed, so I implemented it as written.

**Improvements items closed:**
- "`.dockerignore` secret patterns are root-anchored while its bytecode patterns are not"
  (`Type: quality`, `.dockerignore:6-7,32`) — the item this ticket resolves in full. Moved to
  `docs/archive/improvements-closed.md` with a `**Resolved:** Ticket 045` note describing the
  pattern change and the empirical verification. Removed from the active tracker; no `## Closed`
  items section was created (the pre-existing `## Closed` pointer paragraph at the file's foot is
  untouched).
- **Trim flagged for the Reviewer, who curates this file:** "`fly.toml`'s two machine-lifecycle
  keys should be re-checked with `flyctl` in hand" was **not** archived, per instruction. I
  trimmed it in place: deleted numbered item 2, kept item 1, retitled it to
  "`fly.toml`'s `auto_stop_machines` boolean form should be re-checked with `flyctl` in hand",
  narrowed the `File:` line from `fly.toml:36-38` to `fly.toml:36`, rewrote the lead-in to
  describe one remaining key rather than two, and appended a one-line `**Update —**` note that
  ticket 045 resolved the `auto_start_machines` half. The tracker therefore no longer asserts
  `auto_start_machines = false`. Please confirm the re-curation.

**Known limitations / things I couldn't fully test:**
- **The restart behaviour itself is not observable locally.** `flyctl` is not installed and the
  ticket forbids `fly` commands, so `fly config validate` never ran and I could not confirm Fly
  accepts the document or that Fly Proxy actually restarts a stopped machine. AC4 scopes this to
  TOML validity and the value being correct, which is what I verified. Whether `auto_start_machines
  = true` produces the intended restart is only observable post-deploy, as an owner action.
- **No git baseline for `.dockerignore` or `fly.toml`** (both untracked). I cannot prove
  line-by-line from VCS that nothing else in either file moved. My evidence is the scratch-copy
  diff plus the stronger context-equals-host-tree property for `.dockerignore` and the exact
  key-set assertions for `fly.toml`.
- **`.dockerignore` semantics are Docker's, not Fly's.** The context was built with local Docker
  29.6.2. `fly deploy` uses the same `.dockerignore` format, but I did not verify Fly's builder
  applies `**/` identically; I have no way to without deploying.
- The empty parent directories `web/deep`, `web/deep/nest`, `web/certs` appeared in Build B's
  context as directories carrying zero files — Docker excludes the matched file, not its
  ancestors. Same cosmetic artifact QA 039 recorded, existed only because of my probes, and gone
  now that the probe directories are deleted.
