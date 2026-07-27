# Code Review — 039

**Reviewed:** 2026-07-26 (per-ticket review; `scripts/audit_due.py` reports AUDIT NOT DUE, 2/5
weighted, so no audit checkpoint folded in). QA verdict on `tickets/039-qa.md` is APPROVED, so
this review was in scope to start.

**Files reviewed:**
- `fly.toml` — new, 51 lines. Fly v2 config for the single-pinned-machine M1 shape. Verified
  independently with `tomllib`, not read-only: 7 top-level keys exactly, 6 `[http_service]` keys
  exactly, one `[[vm]]`, `[env]` equal to the AC-specified trio and nothing else.
- `.dockerignore` — new, 45 lines. Verified functionally against a real `docker build` context,
  not by inspection.
- `tickets/039-deployment-fly-toml.md` — `## Status` `ready` → `qa`, plus removal of a stray
  trailing `</content>` junk line. The Engineer attributes that line's disappearance to a
  concurrent session; either way it is a non-content line inside the ticket's own artifact, so it
  is not a diff finding.

File hashes on disk match the ones QA recorded (`fly.toml` `c93b4d2e…`, `.dockerignore`
`465f8a39…`), so the artifacts I reviewed are the artifacts QA approved.

### Scope: CLEAN

The diff is exactly `fly.toml` + `.dockerignore` + the ticket's own `## Status`. `Dockerfile` is
untouched (`COPY . .`, `EXPOSE 8000`, single-worker `CMD` with no `--workers`), no dependency was
added, no CI workflow appeared, no `docs/` file changed, no code changed. Every `Out of scope`
clause holds: no `fly` command was run, no `flyctl` installed, no second machine or region, no
autoscaling knob made configurable.

`docs/ROADMAP.md`, `docs/backlog.md`, and `tickets/042-*`/`043-*`/`044-*` are concurrent-session
noise and are not attributable to 039 — confirmed by inspection of the ROADMAP/backlog diffs,
which concern M1 sequencing and the Streamlit-Cloud decommission, not this ticket's files.

### Architecture: CLEAN

Nothing here is code, so the pure-layer rules (framework imports, `_coerce()`, `_as_list()`,
per-entity Yahoo loops, `data/demo.py` counterparts) have no surface to violate. The two checks
that *do* apply, I ran myself.

**DECISIONS 2026-07-23 conformance — verbatim, item for item.**

| Decision requirement | `fly.toml` | Verdict |
|---|---|---|
| Single machine in `iad` | `primary_region = "iad"`, no `regions` key, one `[[vm]]` | Conforms |
| `min_machines_running = 1` | int `1` (not bool, not string) | Conforms |
| No autoscaling | no `max_machines_running`, no `concurrency`, no `[processes]`, no `[[services]]` | Conforms |
| 1 GB volume at `/data`, shared by `app.db` + `cache/` | `[mounts] source="data" destination="/data"`; `[env]` puts both `DB_PATH` and `CACHE_DIR` under `/data` | Conforms — and correctly leaves the 1 GB *out* of `fly.toml`, since volume size lives in `fly volumes create` |
| `fly.toml` committed to the repo | at repo root | Conforms |
| CI not required | no workflow added | Conforms |

**Single-worker coupling (DECISIONS 2026-04-10).** Preserved. No `[processes]` block, so the
Dockerfile `CMD` is the only process definition and it carries no `--workers`. The header comment
names both decisions and states the "do not add `--workers N`" constraint for future editors,
which is the right place for it — the coupling is invisible from either file alone.

**Implicit-decision drift: none.** The two undocumented values are an app identifier and a
resource knob, neither of which establishes a convention a future ticket would have to follow, so
neither needs a `docs/DECISIONS.md` entry. See "On the two unspecified values" below.

### On the single-machine pin — is it watertight?

This was the load-bearing question, since the 2026-07-23 correctness argument (second machine →
split sessions, forked parquet cache, void `threading.Lock`) is what the whole ticket exists to
enforce. I enumerated every route to a second machine rather than checking the keys the ACs name:

| Route to a second machine | Covered? |
|---|---|
| Fly Proxy autostart | Not a route at all — `auto_start_machines` starts an *existing stopped* machine and never creates one. Safe at either value. |
| Machine-count autoscale from config | No such key present. `min_machines_running = 1` is a floor, not a spawner; `max_machines_running`, `concurrency`, `[processes]`, `[[services]]` are all absent (I asserted the exact key sets, so this is exhaustive, not a grep). |
| Deploy strategy | `bluegreen` and `canary` each stand up a parallel machine, and Fly refuses both for volume-mounted apps. No `[deploy]` block, so default `rolling` applies and updates the one machine in place. The omission is correct; the Engineer's note explaining why they skipped `strategy = "immediate"` is sound. |
| Multi-region | One `primary_region`, no `regions` key, no per-region `[[vm]]`. |
| Manual `fly scale count 2` / `fly machine clone` | **Not expressible in config.** No `fly.toml` can prevent it. |

So: watertight to the limit of what `fly.toml` can express, and the one uncoverable route is
mitigated the only way available — a header comment that names the failure mode, both coupled
decisions, and the instruction not to add a machine without re-opening them together. I would not
ask for more here.

### Secret hygiene: CLEAN

Verified independently, not taken from the reports.

- **`fly.toml` `[env]`** compares *equal* to `{DB_PATH, CACHE_DIR, HTTPS_ONLY}` — three keys, no
  fourth. A substring sweep of the whole parsed document for `yahoo`, `client_id`,
  `client_secret`, `secret`, `token`, `redirect_uri` returns nothing. The header comment states
  the rule ("Yahoo credentials are secrets, set with `fly secrets set` — never in `[env]` below"),
  which is worth more than the current absence of a violation.
- **Build context.** I built my own throwaway `FROM busybox` + `COPY . /ctx` image over the real
  repo root, with the Dockerfile written outside the repo so it was not itself part of the
  context. A combined sweep for `.env`, `.env.*`, `app.db*`, `.cache`, `.git`, `__pycache__`,
  `*.pyc`, `*.pem`, `secrets.toml`, `*token*.json` returned **empty**. This matters because `.env`
  (914 bytes of real Yahoo credentials) and `app.db` (20480 bytes of OAuth tokens) both exist on
  this machine right now, so the exclusions have live targets.
- The only secret-shaped file that does reach the image is `.streamlit/secrets.toml.example`. I
  read it: placeholders only (`your_client_id_here`), a committed template. Not a leak.
- `force_https = true` in `fly.toml` and `HTTPS_ONLY = "true"` in `[env]` agree, so the
  secure-cookie flag at `web/routes/auth.py:81,100` matches the transport the proxy enforces. No
  cookie-attribute regression.

### On `.dockerignore` breadth: correct, marginally under-broad

Not over-broad. I derived the check from the runtime rather than a checklist: every path the app
actually needs is present in the context (`web/main.py`, `web/templates`, `web/static`,
`db/connection.py`, `db/schema.sql`, `data/`, `analysis/`, `auth/oauth.py`, `utils/`, `demo/data`,
`requirements-web.txt`). I also grepped the runtime tree for any reference to an excluded
directory (`docs/`, `tests/`, `scripts/`, `reference/`, `WORKFLOW.md`) — the five hits are all
comments and docstrings citing decisions, no file access. Whole context: 74 files, 592 KB.

Marginally under-broad in one harmless direction: the Streamlit prototype (`app.py`, `pages/`,
`requirements.txt`, `.streamlit/config.toml`, `validate_api.py`) still ships into the production
image. At 592 KB total this is invisible in a pandas/pyarrow image, and the teardown ticket will
delete those files from the repo outright, which resolves it better than a `.dockerignore` line
would. Noted, not filed.

### Verification adequacy: strong

QA's round-2 report is the good kind. Three things raise it above a checklist pass:

1. **AC4 was verified functionally, and the negative case was constructed.** A passing build over
   a context that never contained the file proves nothing, and QA said so and planted probes for
   every pattern with no on-disk target (root-level `__pycache__/`, nested `*.pyo`, nested
   `.pytest_cache/`, `app.db-wal`, `app.db-shm`, `.env.*`), including one three levels deep.
2. **The over-exclusion regression was checked empirically** — runtime set derived by importing
   `web.main` and walking `sys.modules`, then a two-way diff of the context tree against the host
   tree, rather than a hand-written list of files someone thought mattered.
3. **`fly.toml`'s "untouched" claim was not taken on the Engineer's word.** Size, an mtime that
   *predates* both handoffs, and a re-run of all 12 assertions. QA also stated the one honest
   limitation plainly: `.dockerignore` is untracked and was edited in place, so there is no git
   baseline to byte-diff, and QA substituted the stronger property (context == host tree minus
   bytecode) instead of hiding the gap.

**On QA's AC4 literal-wording ruling, I agree.** AC4 names `__pycache__/` as a pattern but states
its requirement as an outcome ("so a `docker build` (or `fly deploy`) build context carries none
of them into the image"). `**/__pycache__/` is a proper superset — the root-level probe settles
that empirically — so nothing AC4 asked for was given up. Reading the pattern as a literal string
to `grep -qxF` would fail the *fix* for the defect the same grep was used to miss in round 1,
which is the wrong reading. The outcome is the criterion.

No fixture-based tests were added, and that is correct rather than a gap: `fly.toml` and
`.dockerignore` are consumed by Fly and Docker, and there is no importable code path to assert
against. This is not a DECISIONS 2026-05-31 coverage miss — the ACs are not assertable from
pytest at all. Independently confirmed the suite is green.

### On the two unspecified values

I was asked for my own view rather than QA's. I endorse both, with one routing note.

**`app = "fantasy-hockey-waiver"` — accept.** The key is mandatory for a deployable `fly.toml`
and nothing in the ticket, DECISIONS, or ROADMAP names the app, so a value had to be invented;
inventing it and flagging it beats omitting it and shipping a file that cannot deploy. It is also
the safest class of unspecified value: if the owner creates the app under a different name, the
mismatch fails **loudly** (`fly deploy` cannot find the app) rather than doing something quiet and
wrong. The gap is not in `fly.toml`, it is that nothing the owner reads at deploy time tells them
to reconcile the two. `docs/ROADMAP.md`'s M1 launch step 2 currently jumps straight to
`fly volumes create` → `fly secrets set` → `fly deploy`, with no `fly apps create` step. **PM
should add that step**, naming `fantasy-hockey-waiver` or instructing the owner to edit the `app`
key. Not a change to this ticket's files.

**`[[vm]]` `shared` / 1 cpu / `1gb` — accept, and the memory choice is the right one.** AC2 only
requires "a single `[[vm]]`", which holds. Sizing has no architectural consequence at ~8 users and
no DECISIONS entry constrains it, so this is an owner cost knob, not a decision the Engineer
usurped. On the merits, 1 GB over 512 MB is correct: pandas + pyarrow cost a few hundred MB of RSS
on import alone, before any parquet is materialised, and an OOM-killed machine on a
single-machine app is a full outage. The one hazard is cosmetic and the Engineer pre-empted it —
`memory = "1gb"` sitting near a decision that also says "1 GB volume" invites a reader to conflate
the two, and the header comment already states the volume's size lives in
`fly volumes create`, not here.

### Issues

- **should-fix (logged to `docs/improvements.md`, not blocking):** `auto_start_machines = false`
  leaves the pinned machine with no automatic restart path. Fly's default is `true`, and
  `min_machines_running = 1` does not compensate — it applies only when `auto_stop_machines` is
  `stop`/`suspend`, so it is inert here (QA spotted the inertness; the corollary is mine). If the
  machine ever stops for a reason other than a process crash (Fly host migration, OOM stop, manual
  stop), Fly Proxy will not bring it back on the next request and the app is down until someone
  runs `fly machine start`. The default `on-failure` restart policy still covers crashes, so the
  window is narrow but real for a public app. Worth naming clearly: `auto_start_machines = true`
  would **not** breach the pin, because auto-start only starts an existing stopped machine and
  never creates one, so the owner can flip it without re-opening DECISIONS 2026-07-23. Not
  requested as a fix here because it satisfies AC2 as written, the ticket had already spent its
  one fix round, and I cannot validate any alternative without `flyctl`.
- **should-fix (logged to `docs/improvements.md`, not blocking):** `.dockerignore`'s secret
  patterns (`.env`, `.env.*`, `*.pem`) are still root-anchored while the bytecode patterns got the
  `**/` treatment in the fix round. Same bug class QA caught, but on the patterns where a future
  miss leaks a credential instead of bloating an image. No exposure today — I confirmed by `find`
  that the only matches in the repo are root-level (`./.env`, `./.env.example`, `./app.db`) and my
  context build carried none of them — which is why this is logged rather than requested.
- **nit:** `[build] dockerfile = "Dockerfile"` is redundant (Fly auto-detects a root Dockerfile).
  Harmless and arguably better as explicit. Leave it.

**On `auto_stop_machines = false`: accepted observation, not a should-fix.** QA is right that
current flyctl treats the boolean as deprecated in favour of `"off"`/`"stop"`/`"suspend"`. But the
boolean form is the one accepted by *both* older and newer flyctl, while `"off"` is accepted only
by newer — so switching blind, in a file no tool here can lint, trades a deprecation warning for
an unvalidated schema risk. That is a worse trade, and "recommend a change I cannot verify" is not
a standard I want to set on deployment config. It also cannot produce a second machine at either
value, so no correctness argument attaches. Resolve it at `fly config validate` time, with flyctl
in hand and the answer available in one second. Logged alongside the `auto_start_machines` item as
one improvements entry so the pair gets looked at together.

The `flyctl`-absent / `fly config validate`-unrun limitation I accept as recorded: the ticket
forbade `fly` commands, both handoffs and the QA report state it plainly rather than papering over
it, and it is already on the owner-must-verify list as the first deploy step. That is the correct
disposition for a constraint the ticket imposed on itself.

### Routing call — `docs/ARCHITECTURE.md:102`

Line 102 still reads ``fly.toml  # planned, not yet in repo…``, which this ticket makes false.
Correctly outside the Engineer's `Touches`, and correctly not fixed by them.

**My call: a `docs/improvements.md` entry addressed to the Tech Lead, not its own ticket.** It is
a factual two-line correction in a Tech-Lead-owned file with zero code impact, so a ticket would
carry more process than content; and there is precedent in the same tracker (the
`docs/DECISIONS.md` line-drift item routes a doc fix to the Tech Lead exactly this way). Filed
with the suggested replacement text. I widened it by one line while I was there: the tree listing
has **no `.dockerignore` entry at all**, and 039 landed that file at the repo root too, so the
same upkeep pass should add it beside the `Dockerfile` line.

### Verdict: APPROVED

No blockers. Scope is clean, the pin conforms to DECISIONS 2026-07-23 verbatim and is watertight
to the limit config allows, secret hygiene is verified against a real build context rather than by
reading the file, and both unspecified values are defensible with the app-name reconciliation
routed to the ROADMAP.

**New `docs/improvements.md` entries written by this review (3):**
- `docs/ARCHITECTURE.md` directory listing is stale on the two files ticket 039 landed
- `fly.toml`'s two machine-lifecycle keys should be re-checked with `flyctl` in hand
- `.dockerignore` secret patterns are root-anchored while its bytecode patterns are not

**Not this review's to do, flagged for routing:**
- **PM** — add a `fly apps create` step to `docs/ROADMAP.md`'s M1 launch sequence, reconciling the
  app name with `fly.toml`'s `app = "fantasy-hockey-waiver"`.
- **Owner** — `fly config validate` remains the first deploy step; `fly status` / `fly scale show`
  after deploy is the only place the single-machine pin becomes observable.

Status left at `qa` and artifacts left in place — the orchestrator handles promotion on an
APPROVED verdict.
