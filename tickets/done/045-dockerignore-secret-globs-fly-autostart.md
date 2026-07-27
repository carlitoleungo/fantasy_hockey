# 045 — Widen `.dockerignore` secret patterns to `**/`; let Fly restart the pinned machine

## Status
done

## Type
bug

## Milestone
m1

## Touches
- .dockerignore
- fly.toml

## Why
Two deployment-config defects that Review 039 found and logged rather than fixed, both of
which cost the owner something only after the app is live. First, `.dockerignore`'s secret
patterns (`.env`, `.env.*`, `*.pem`) are anchored to the build-context root while its
bytecode patterns were widened to `**/` during 039's fix round — so a bare pattern silently
excludes nothing when the matching file is nested. There is no exposure today (every match
in the repo is root-level), but this is the one place in the file where a future miss bakes a
live credential into the production image instead of merely bloating it, and it fails with no
warning. Second, `fly.toml` sets `auto_start_machines = false`, so Fly Proxy will not restart
the single pinned machine if it stops for any reason other than a process crash — a host
migration, an OOM stop, or a manual stop leaves the app down until the owner runs
`fly machine start`. `min_machines_running = 1` does not cover this; it applies only when
`auto_stop_machines` is `stop`/`suspend`, so as configured it is inert. For a public-facing
app whose whole M1 promise is "a stable HTTPS URL", an outage that needs a human to notice
and clear it is the wrong failure mode.

This ticket resolves the `docs/improvements.md` entry "`.dockerignore` secret patterns are
root-anchored while its bytecode patterns are not" in full, and the second numbered half of
"`fly.toml`'s two machine-lifecycle keys should be re-checked with `flyctl` in hand".

## Acceptance criteria
- [ ] A build context taken over the real repo root (throwaway `FROM busybox` + `COPY . /ctx`) contains no file matching `.env`, `.env.*`, or `*.pem` at **any** depth, root level included — so root-level `./.env` and `./.env.example`, which exist on this machine today, are still excluded after the widening.
- [ ] Probe files planted at nested paths (at minimum `web/.env`, `web/deep/nest/.env.local`, and `web/certs/key.pem`) are absent from that context. Under the pre-change patterns these same probes reach the context; under the new ones they do not.
- [ ] Nothing is newly over-excluded: every runtime file still reaches the context, and the context source tree still equals the host source tree minus bytecode and the excluded secrets/state — matching the property QA 039 recorded (74 files, the same 19 top-level entries).
- [ ] `fly.toml` still parses as valid TOML and now sets `auto_start_machines = true` (boolean `true`, not a string). Every single-machine-pin key is unchanged: `min_machines_running` is int `1`, `auto_stop_machines` is boolean `false`, exactly one `[[vm]]`, and no `max_machines_running`, `concurrency`, `[processes]`, `[[services]]`, or `regions` key appears anywhere in the document.
- [ ] `.venv/bin/python -m pytest tests/` is green (no code is touched; this confirms the config edits disturbed nothing).

## Out of scope
- **The `auto_stop_machines` boolean-vs-`"off"` deprecation** — numbered item 1 of the same
  improvements entry. Current flyctl treats the boolean form as deprecated in favour of
  `"off"`/`"stop"`/`"suspend"`, but the boolean is the form accepted by *both* older and newer
  flyctl, so switching blind trades a deprecation warning for an unvalidated schema risk in a
  file nothing here can lint. It can only be resolved with `flyctl` present at
  `fly config validate` time, so **it stays an improvements item** — leave the value as
  `false`. See the close-out instructions below for how to leave that half of the entry open.
- **Any `fly` command, and actually deploying.** `flyctl` is not installed. `fly config
  validate`, `fly volumes create`, `fly secrets set`, and `fly deploy` are owner actions
  recorded as M1 launch steps in `docs/ROADMAP.md`. No acceptance criterion here depends on
  running `fly`, and the restart behaviour itself is observable only post-deploy — which is
  why AC4 scopes it to TOML validity and the value being correct.
- **`docs/ARCHITECTURE.md:102`** (the stale `fly.toml # planned, not yet in repo` line, and
  the missing `.dockerignore` tree entry). Routed to a Tech Lead upkeep pass by Review 039;
  `docs/` is outside both this ticket's `Touches` and what an Engineer may edit.
- **`Dockerfile`.** `COPY . .`, `EXPOSE 8000`, and the single-worker `CMD` with no
  `--workers` are all correct for the pinned-machine shape. Do not touch it.
- **The `.streamlit/` secret patterns** (`.dockerignore` lines 8-10). Root-anchored too, but
  deliberately scoped to a single root-level directory, and the Streamlit teardown deletes
  those files outright — which resolves it better than a pattern would. The improvements
  entry does not ask for them. Leave them.
- **The `[build] dockerfile = "Dockerfile"` redundancy.** Review 039 looked at it and said
  leave it. Leave it.
- **The Streamlit prototype files still shipping into the image** (`app.py`, `pages/`,
  `requirements.txt`). Review 039 noted this and deliberately did not file it — the teardown
  ticket deletes them from the repo, which is the better fix. Do not add exclusions for them.

## Notes for the Engineer
- **Architectural surface (`fly.toml`) — no new Tech Lead consult needed; the covering
  decision is `docs/DECISIONS.md` "Deployment: M1 shape — single pinned machine, 1 GB
  volume, fly.toml in repo" (2026-07-23). Cite that entry by title in your done note.**
  The PM's reasoning, so the next reader can check it rather than trust it: that entry's
  correctness requirement is *never more than one machine*, because a Fly volume binds to one
  machine (a second machine splits sessions, forks the parquet cache, and voids the
  per-league `threading.Lock`). `auto_start_machines = true` cannot breach that pin —
  auto-start only restarts an **existing stopped** machine and never creates one, which
  Review 039 confirmed by enumerating every route to a second machine independently
  (`tickets/done/039-review.md` § "On the single-machine pin"). The flip also touches none of
  the entry's other commitments (1 GB volume at `/data`, `fly.toml` in repo, no CI), and it
  moves the key **toward** Fly's own default: `false` was never a decided value — no
  DECISIONS entry, no 039 acceptance criterion, and no ROADMAP step names it, so this is
  correcting an undecided implementation detail back to the platform default in the direction
  that actually keeps the pinned machine up, which serves the entry's stated purpose ("M1
  requires the app deployed at a stable HTTPS URL"). Supporting but not load-bearing: the
  `WORKFLOW.md` surface list names `fly.toml` for a *new env var or new config knob*, and
  this adds neither — it changes the value of a knob already in the file.
- **Do not add `--workers N` anywhere, and do not add a machine, region, or autoscaling
  knob.** The pin is load-bearing on DECISIONS 2026-04-10 "Runtime: single uvicorn worker"
  and the ticket-037 cache lock. `fly.toml`'s header comment (lines 7-12) already states this
  for future editors; leave that comment intact.
- **The prescribed `.dockerignore` shape** — implement exactly this, don't invent variants.
  Replace the two lines `.env` and `.env.*` (lines 6-7) with a single `**/.env*`, and `*.pem`
  (line 32) with `**/*.pem`. Extend the existing explanatory comment at lines 21-22 (or add a
  matching one in the Secrets block) so the next reader knows the `**/` prefix is load-bearing
  on the secret patterns too, not just the bytecode ones.
- **Root coverage is preserved, and it is the thing most worth proving.** `**/` matches zero
  or more path segments, so `**/.env*` matches `.env` at the root as well as nested. This is
  not theory here: QA 039 planted a root-level `__pycache__/rootprobe.pyc` against
  `**/__pycache__/` and it was excluded (`tickets/done/039-qa.md` § "The root-coverage
  question … is settled empirically"). The PM also pre-checked the exact two patterns this
  ticket prescribes, in a throwaway scratch context (Docker 29.6.2, never touching the repo):
  with only `**/.env*` and `**/*.pem` in `.dockerignore`, all six probes were excluded — root
  `.env`, root `.env.example`, root `root.pem`, `web/.env`, `web/deep/nest/.env.local`, and
  `web/certs/key.pem` — while `web/main.py` still came through. So the fix is known-good in
  principle; your job is to prove it over the **real** repo context. Confirm root coverage
  again there regardless — root-level `.env` holds 914 bytes of real Yahoo credentials, so a
  regression on that one file is the worst outcome this ticket could produce.
- **No git baseline exists for either file.** Both `.dockerignore` and `fly.toml` are still
  untracked (039 landed them and they were never committed), so your edits will not appear as
  `M` in `git status` and there is nothing to byte-diff against. QA 039 hit this exact
  limitation and substituted the stronger property (context == host tree minus bytecode);
  state the same thing plainly in your done note rather than implying a diff was checked.
- **Yahoo API gotchas: none apply.** This ticket touches no `data/`, `analysis/`, or `auth/`
  code, adds no dependency, and adds no route, so the pure-layer rules, `_coerce`/`_as_list`,
  bulk-endpoint, and demo-parity requirements have no surface here.
- **No `docs/LEARNINGS.md` append is required.** Considered and declined: QA 039 already
  judged the `.dockerignore` anchoring gotcha too narrow for LEARNINGS (this repo has exactly
  one such file), and after this ticket both pattern groups carry the `**/` prefix with the
  comment at the fix site as the durable record. Do not add one.
- **Open `docs/improvements.md` items on files in `Touches`:**
  - "`.dockerignore` secret patterns are root-anchored while its bytecode patterns are not"
    (`Type: quality`, `.dockerignore:6-7,32`) — **this is the item this ticket resolves, in
    full.** Move it to `docs/archive/improvements-closed.md` with a `**Resolved:**` note
    naming ticket 045 and what changed, per your DoD.
  - "`fly.toml`'s two machine-lifecycle keys should be re-checked with `flyctl` in hand"
    (`Type: quality`, `fly.toml:36-38`) — **half in scope, so do not archive this entry.**
    Numbered item 2 (`auto_start_machines`) is resolved here; numbered item 1
    (`auto_stop_machines` deprecation) stays open and is out of scope above. Trim the entry
    in place: delete numbered item 2, keep numbered item 1, and adjust the entry's title and
    lead-in so they describe one remaining key rather than two (e.g. "`fly.toml`'s
    `auto_stop_machines` boolean form should be re-checked with `flyctl` in hand"), with a
    one-line note that ticket 045 resolved the `auto_start_machines` half. Leaving the entry
    untrimmed would leave the tracker asserting `auto_start_machines = false` after you have
    changed it, which is worse than a partial edit. Flag the trim in your done note so the
    Reviewer, who curates this file, can confirm the re-curation.
  - "`docs/ARCHITECTURE.md` directory listing is stale on the two files ticket 039 landed"
    (`Type: quality`) — mentions both of your files in its text, but it is filed against
    `docs/ARCHITECTURE.md`, which is not in `Touches` and is Tech-Lead-owned. **Out of
    scope**; leave it open.
  - No `Type: bug` item is open on either file.

## Verification
Reuse QA 039's empirical method — `.dockerignore` behaviour is verifiable locally, and
inspection of the pattern list is not sufficient evidence for any of AC1-AC3.

- **Build-context harness.** Write a throwaway `FROM busybox` + `COPY . /ctx` Dockerfile into
  a scratch directory **outside the repo** (so the Dockerfile is not itself part of the
  context), then build from the repo root:
  `docker build -q -f <scratch>/ctx.Dockerfile -t qa045ctx .`. That context is exactly what
  `fly deploy` would send. Inspect with `docker run --rm qa045ctx find /ctx …`.
- **AC1** — sweep the context for `.env`, `.env.*`, and `*.pem` at every depth; expect empty.
  Confirm first that the host really has targets (`./.env`, `./.env.example` both exist), so a
  clean result is meaningful rather than vacuous.
- **AC2 — plant the probes, and run the negative control.** A passing build over a context
  that never contained the file proves nothing. Create `web/.env`,
  `web/deep/nest/.env.local`, and `web/certs/key.pem`, each containing a placeholder string
  only — **never copy real credentials into a probe.** Build once with the pre-change
  patterns (keep a copy of the original `.dockerignore`) and confirm the probes **do** reach
  the context; build again with the new patterns and confirm they do not. Both directions are
  the evidence.
- **AC3 — over-exclusion check.** Derive the runtime file set empirically rather than from a
  hand-written list: import `web.main`, collect every repo-local module in `sys.modules`, add
  every file under `web/templates`, `web/static`, and `demo/data`, plus
  `requirements-web.txt`, and assert each is present in the context. Then diff the whole
  context source tree against the host source tree in both directions. Nothing needed may be
  missing; nothing unexpected may be present. Watch specifically for anything beginning
  `.env` that the runtime needs — there should be none.
- **AC4** — re-run a `tomllib` assertion script over `fly.toml`: `auto_start_machines is
  True`, `auto_stop_machines is False`, `min_machines_running == 1` and is an `int`,
  `len(doc["vm"]) == 1`, the top-level and `[http_service]` key sets are exactly what QA 039
  recorded plus no additions, and no `max_machines_running` / `concurrency` / `processes` /
  `services` / `regions` key exists.
- **AC5** — `.venv/bin/python -m pytest tests/`.
- **Cleanup gate, and treat it as a criterion.** Delete every probe file and the directories
  they created (`web/deep`, `web/certs`), remove the throwaway image
  (`docker images | grep qa045` → empty) and the scratch Dockerfile, and confirm
  `git status --porcelain` is byte-for-byte what it was before you started. Probe files named
  `.env*` must not survive the session.
- **Close-out** — confirm the `.dockerignore` improvements entry now sits in
  `docs/archive/improvements-closed.md`, and that the `fly.toml` entry remains in
  `docs/improvements.md` trimmed to its `auto_stop_machines` half.
- **What "done" looks like:** nothing changes in the running app. `uvicorn web.main:app` still
  boots and `GET /health` still returns `200` `{"status":"ok"}`; the deliverable is a build
  context that cannot carry a nested credential and a `fly.toml` that lets Fly bring the one
  pinned machine back by itself.

## Dependencies
- **Ticket 039 — done** (`tickets/done/039-deployment-fly-toml.md`). This ticket follows on
  from its two deliverables and cannot start before them; they are in place at the repo root.
- Tech Lead consult — **not required.** Covered by `docs/DECISIONS.md` "Deployment: M1 shape
  — single pinned machine, 1 GB volume, fly.toml in repo" (2026-07-23); see the first bullet
  of "Notes for the Engineer" for why.
- No file overlap with tickets 042, 043, or 044 — they can run in any order relative to this
  one. **But run 045 early in that batch, ideally first.** `scripts/audit_due.py` reads
  3.0 / 5.0 today; 045 is full-process (1.0). Once completions since the last audit reach
  5.0 an audit is due, and an overdue audit blocks *architectural-surface* scoping and
  orchestrator pre-flight — which is this ticket and not 042/043/044. Tickets 042 (1.0) and
  044 (1.0) alone reach 5.0, so if the whole batch lands first, 045 is blocked behind an
  audit for no good reason.
