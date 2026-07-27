# Implementation complete — 039

**What I did:**
- Added `fly.toml` at the repo root implementing DECISIONS 2026-07-23 "Deployment: M1 shape —
  single pinned machine, 1 GB volume, fly.toml in repo" verbatim: `primary_region = "iad"`,
  one machine (`min_machines_running = 1`, `auto_start_machines`/`auto_stop_machines` both
  `false`), a single `[[vm]]`, `[mounts] source = "data"` → `destination = "/data"`, and an
  `[env]` wiring `DB_PATH`/`CACHE_DIR`/`HTTPS_ONLY` to their production values.
- Pointed the `[http_service]` at `internal_port = 8000` with `force_https = true` and one
  `[[http_service.checks]]` doing `GET /health` (the endpoint in `web/routes/health.py`).
- Wrote the header comment explaining why the single-machine pin is a correctness
  requirement (volume bound to one machine → split sessions, forked cache, void
  `threading.Lock`) and citing both DECISIONS entries, plus an explicit "do not add
  `--workers N`" instruction for future editors.
- Added `.dockerignore` so the Dockerfile's `COPY . .` cannot bake secrets or local state
  into the image: `.env` / `.env.*`, `app.db`, `app.db-wal`, `app.db-shm`, `.cache/`,
  `.git/`, `__pycache__/`, `.venv/`, Streamlit secrets/token files, `*.pem`, plus
  non-runtime directories (`tests/`, `docs/`, `tickets/`, `.team/`, `reference/`,
  `scripts/`, `team-generator/`, `.devcontainer/`, `.claude/`).
- No Dockerfile change, no dependency, no CI workflow, no code change.

**Files changed:**
- `fly.toml` — new; Fly v2 deployment config for the single-pinned-machine M1 shape.
- `.dockerignore` — new; keeps secrets, the local SQLite DB, and the local parquet cache out
  of the build context.

**Acceptance criteria status (self-check):**
- [x] AC1 — `fly.toml` exists at repo root, parses as valid TOML, `primary_region = "iad"`.
  Evidence: `.venv/bin/python` + `tomllib.load(open('fly.toml','rb'))` succeeded and asserted
  `primary_region == "iad"`.
- [x] AC2 — pinned to exactly one machine. Evidence: parsed values are
  `min_machines_running = 1`, `auto_start_machines = false`, `auto_stop_machines = false`,
  `len(vm blocks) == 1`; the parsed top-level keys are exactly
  `['app', 'build', 'env', 'http_service', 'mounts', 'primary_region', 'vm']` — no
  `[processes]`, no `[[services]]`, no concurrency/autoscale block, no second region.
- [x] AC3 — `[mounts] destination = "/data"` (`source = "data"`, matching the ROADMAP's
  `fly volumes create data …`); `[env]` parses to exactly
  `{"DB_PATH": "/data/app.db", "CACHE_DIR": "/data/cache", "HTTPS_ONLY": "true"}` (asserted
  by equality, so no Yahoo secret can be hiding in it); `internal_port` is the int `8000`;
  the only health check is `{method: GET, path: /health, interval 30s, timeout 5s,
  grace_period 10s}`.
- [x] AC4 — `.dockerignore` exists and contains all seven required patterns (checked with
  exact-line `grep -qxF` for `.env`, `app.db`, `app.db-wal`, `app.db-shm`, `.cache/`,
  `.git/`, `__pycache__/`). Verified against a real build rather than by inspection: built a
  throwaway `FROM busybox` + `COPY . .` image against the repo-root context and listed it.
  Leak check for `.env app.db app.db-wal app.db-shm .cache .git __pycache__ .venv tests docs
  tickets` printed nothing; the runtime paths (`web data analysis auth db demo utils
  requirements-web.txt`) are all present. Image removed afterwards.
- [x] AC5 — `.venv/bin/python -m pytest tests/` → **459 passed** in 1.45s. App boots with
  env-provided paths: ran
  `env DB_PATH=<tmp>/app.db CACHE_DIR=<tmp>/cache HTTPS_ONLY=true .venv/bin/python -m uvicorn
  web.main:app --host 127.0.0.1 --port 8123`; startup clean, `GET /health` → 200
  `{"status":"ok"}`, `GET /` → 200, and `app.db` was created at the env-specified path (not
  the repo root), which is the behaviour `[env] DB_PATH=/data/app.db` relies on.

**How to verify (for QA):**
1. `cd /Users/carlinleung/personal_dev/fantasy_hockey && .venv/bin/python -c "import tomllib,json;print(json.dumps(tomllib.load(open('fly.toml','rb')),indent=2))"`
   and check region / `min_machines_running` / single `[[vm]]` / `[mounts]` / `[env]` /
   `internal_port` / `/health` check.
2. `grep -n . .dockerignore` and confirm the seven required patterns.
3. Optional real-context check (docker is running on this machine):
   build any `FROM busybox` + `COPY . .` image with `-f <dockerfile outside the repo> .` from
   the repo root and confirm `ls -a` in the image shows no `.env`, `app.db*`, `.cache`, or
   `.git`.
4. `.venv/bin/python -m pytest tests/` → green.
5. `uvicorn web.main:app` (or the env-prefixed form above) and `curl -s localhost:8000/health`
   → `{"status":"ok"}`.
6. No demo-mode steps: this ticket touches no `data/` code.

**Scope notes:**
- **One value the ticket did not specify: the Fly app name.** `fly.toml` needs an `app` key to
  deploy, and nothing in the ticket, DECISIONS, or ROADMAP names the app, so I set
  `app = "fantasy-hockey-waiver"`. It is not covered by any AC and the owner should change it
  to whatever they actually create with `fly apps create` before the first deploy (or override
  with `fly deploy -a <name>`). Flagged rather than assumed silently.
- **Machine size is also unspecified** by the decision. I used the `fly launch` default shape
  (`cpu_kind = "shared"`, `cpus = 1`) with `memory = "1gb"` rather than 512 MB, because the
  image imports pandas + pyarrow. One `[[vm]]` either way, so AC2 holds; the owner can scale
  it down if Fly billing matters more than headroom.
- `docs/ARCHITECTURE.md:102` still says `fly.toml  # planned, not yet in repo` — now stale.
  `docs/` is outside my `Touches` and outside what the Engineer may edit, so it needs a
  one-line follow-up (Tech Lead owns ARCHITECTURE upkeep).
- `docs/ROADMAP.md` M1 launch step 2 ("after ticket 039 lands `fly.toml`, run
  `fly volumes create data --size 1 --region iad` …") is now unblocked. Deploy remains an
  owner action; I ran no `fly` command and installed no `flyctl`.
- I did not add `[deploy] strategy = "immediate"`. Fly's default rolling strategy restarts the
  single machine in place, so it is not required; noting it only because a future editor may
  wonder.
- **Working tree note:** `git status` shows two changes that are not mine and appeared during
  my session — `docs/ROADMAP.md` and `tickets/039-deployment-fly-toml.md` each lost a stray
  trailing tag line (`</invoke>`, `</content>`), and `tickets/042-error-page-nav-free.md` is
  new/untracked. Some concurrent session made those. My diff is `fly.toml`, `.dockerignore`,
  this file, and the ticket's `## Status` line only.

**Improvements items closed:**
- None. This ticket was not scoped from a `docs/improvements.md` item (its Why cites the
  missing `fly.toml` and the `COPY . .` secret leak, not a tracker entry), and there is no
  open item on `fly.toml` or `.dockerignore` — neither file existed before this ticket.
  Related but deliberately untouched: the open item "Atomic cache write is crash-safe against
  concurrent readers but not against machine restart" (`docs/improvements.md:246`) is about
  `data/cache.py` `fsync`, which is outside my `Touches`.

**Known limitations / things I couldn't fully test:**
- **I did not validate the file against Fly's own schema.** `flyctl` is not installed on this
  machine and the ticket forbids running `fly` commands, so `fly config validate` was not run.
  What I verified is that the file is valid TOML and that every key/value the ACs name is
  present with the right type. The key *names* follow the current Fly v2 schema
  (`[http_service]` with `[[http_service.checks]]`, `[[vm]]`, `[mounts]`), but only
  `fly config validate` or an actual deploy can confirm Fly accepts them — worth running as
  the first step of the owner's deploy.
- **Nothing here is exercised by the test suite**, by nature: `fly.toml` and `.dockerignore`
  are consumed by Fly and Docker, not by Python. There is no new code path to unit-test, so I
  added no tests; the AC evidence is the `tomllib` parse assertions, the `grep -qxF` checks,
  and the real busybox build-context check above. The pytest run is a regression check only.
- **The single-machine pin is unverifiable locally.** That it actually results in one machine
  can only be observed post-deploy via `fly status` / `fly scale show`; I verified only that
  the config contains no key that would produce more than one.
- I did not build the real `Dockerfile` image (pip-installing pandas/pyarrow), only a busybox
  image over the same build context. The context is what `.dockerignore` governs, so this
  tests the right thing, but the production image itself was not built.
