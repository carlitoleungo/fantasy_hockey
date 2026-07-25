# 039 — Deployment config: fly.toml (single pinned machine, 1 GB volume) + .dockerignore

## Status
ready

## Type
feature

## Milestone
m1

## Touches
- fly.toml
- .dockerignore

## Why
M1 requires the app deployed at a stable HTTPS URL for ~8 authenticated users across 4–6
leagues. A `Dockerfile` exists but there is no `fly.toml`, so the app cannot be deployed to
Fly. Two correctness constraints must be baked into that config. First, a Fly volume is
bound to a single machine: if the app ever scales past one machine, sessions split (a
user's cookie resolves on one machine and not the other), the parquet cache forks into
divergent copies, and the `threading.Lock` from ticket 037 silently stops providing mutual
exclusion — so the machine pin is a correctness requirement, not a cost optimisation.
Second, the Dockerfile does `COPY . .` with no `.dockerignore`, which today would bake
`.env` (Yahoo secrets), `app.db` (OAuth tokens), and `.cache/` into the production image —
a secret-leak and a source of a local DB shadowing the volume-mounted one. Both close here.

## Acceptance criteria
- [ ] `fly.toml` exists at the repo root, parses as valid TOML, and sets `primary_region = "iad"`.
- [ ] `fly.toml` pins the app to exactly one machine: `min_machines_running = 1` and no configuration that would autoscale past one machine (no `auto_start_machines`/`auto_stop_machines` growth beyond a single machine; a single `[[vm]]`). One machine, no autoscaling.
- [ ] `fly.toml` declares a `[mounts]` with `destination = "/data"` and an `[env]` that sets `DB_PATH = "/data/app.db"`, `CACHE_DIR = "/data/cache"`, and `HTTPS_ONLY = "true"`; the HTTP service exposes `internal_port = 8000` with a health check targeting `/health`.
- [ ] `.dockerignore` exists and excludes at least `.env`, `app.db`, `app.db-wal`, `app.db-shm`, `.cache/`, `.git/`, and `__pycache__/` — so a `docker build` (or `fly deploy`) build context carries none of them into the image.
- [ ] `.venv/bin/python -m pytest tests/` is green (no code touched; confirms the config additions didn't disturb the tree) and the app still boots locally with `uvicorn web.main:app` reading `DB_PATH`/`CACHE_DIR` from the environment.

## Out of scope
- **Actually deploying.** `fly volumes create`, `fly secrets set`, and `fly deploy` are
  owner actions (need a Fly account and auth) recorded as M1 launch steps in
  `docs/ROADMAP.md`. This ticket delivers the committed config only.
- **Registering the production Yahoo redirect URI** — owner action in the Yahoo developer
  console (Yahoo requires HTTPS redirect URIs registered out-of-band). Recorded in ROADMAP.
- **CI** — explicitly not an M1 requirement (DECISIONS 2026-07-23 "Deployment: M1 shape").
  Do not add a GitHub Actions workflow.
- **Dockerfile changes.** The existing single-worker `uvicorn` CMD and `EXPOSE 8000` are
  correct for the single-machine shape; do not modify it. (Adding the `.dockerignore` is the
  only image-build change.)
- Multi-region, autoscaling, or a second machine — the pin is deliberate; do not make it
  configurable.

## Notes for the Engineer
- **Architectural surface — the Tech Lead consult is already done.** Implement
  `docs/DECISIONS.md` **"Deployment: M1 shape — single pinned machine, 1 GB volume, fly.toml
  in repo" (2026-07-23)** verbatim: single machine in `iad`, `min_machines_running = 1`, no
  autoscaling; a **1 GB** volume at `/data` shared by `app.db` and `cache/`; `fly.toml`
  committed to the repo; CI not required. Cite that entry.
- The volume is created out-of-band by the owner (`fly volumes create data --size 1 --region
  iad`); `fly.toml`'s `[mounts]` references it by `source = "data"` (or the name the owner
  creates) → `destination = "/data"`. The 1 GB size lives in the volume, not `fly.toml`;
  the ROADMAP launch step records the create command.
- **Env consistency:** `.env.example` already documents the production values
  (`DB_PATH=/data/app.db`, `CACHE_DIR=/data/cache`, `HTTPS_ONLY=true`). `db/connection.py`
  reads `DB_PATH` and opens SQLite in WAL mode already (`db/connection.py:38`); `data/cache.py`
  reads `CACHE_DIR`; `web/routes/auth.py:81,100` reads `HTTPS_ONLY` for the secure-cookie
  flag. So the `[env]` block just wires these — no code change needed. Yahoo credentials
  (`YAHOO_CLIENT_ID`/`YAHOO_CLIENT_SECRET`/`YAHOO_REDIRECT_URI`) are **secrets**, set via
  `fly secrets set` by the owner, NOT in `fly.toml` `[env]`.
- **Health check:** the app already serves `GET /health` returning `{"status": "ok"}`
  (`web/routes/health.py`) — point the Fly HTTP-service health check at it.
- **Single-worker coupling:** the machine pin is load-bearing on DECISIONS 2026-04-10
  "Runtime: single uvicorn worker" and the ticket-037 cache lock. Do not add `--workers N`
  to any command; keep one worker, one machine.
- This ticket touches no `data/`/`analysis/`/`auth/` code and adds no dependency — it is
  pure deployment config plus an image-hygiene file.

## Verification
- Parse `fly.toml` (e.g. `python3 -c "import tomllib; tomllib.load(open('fly.toml','rb'))"`)
  and confirm the region, single-machine pin, `[mounts]` destination `/data`, `[env]`
  values, `internal_port = 8000`, and the `/health` check are all present.
- Confirm `.dockerignore` lists `.env`, `app.db*`, `.cache/`, `.git/`, `__pycache__/`.
  Optionally `docker build .` and confirm `.env`/`app.db` are absent from the image
  (`docker run --rm <img> ls -a` shows no `.env`).
- `uvicorn web.main:app` still boots locally; `GET /health` returns 200.
- `.venv/bin/python -m pytest tests/` green.

## Dependencies
- Tech Lead consult on the deployment shape — RESOLVED 2026-07-23 (DECISIONS "Deployment:
  M1 shape — single pinned machine, 1 GB volume, fly.toml in repo"). Independent of 037/038;
  can land in parallel. Actual `fly deploy` is an owner action (see ROADMAP M1 launch steps).
</content>
