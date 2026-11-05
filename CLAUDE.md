# Fantasy Hockey Waiver Wire

A FastAPI + HTMX web app that helps Yahoo Fantasy Hockey managers make waiver add/drop
decisions. Each user signs in with their own Yahoo account; a demo mode (`/demo/*`) serves a
static snapshot to logged-out visitors. Audience today: the owner and a handful of friends.

## Commands

```bash
uv venv .venv --python 3.11 && uv pip install -r requirements-web.txt   # first time
.venv/bin/python -m uvicorn web.main:app --reload                        # run (needs .env, see RUNNING.md)
.venv/bin/python -m pytest tests/                                        # test (bare python has no pytest)
fly deploy                                                               # ship (fly.toml in repo)
```

Local OAuth needs an HTTPS tunnel (ngrok); see `RUNNING.md`. Env vars are listed in `.env.example`.

## Layout

- `web/` FastAPI routes, session middleware, Jinja2 templates. Route handlers are the only
  place HTTP meets the data stack.
- `data/` Yahoo API client, parsers, parquet cache, demo loader. `analysis/` ranking and
  projection maths. `auth/` OAuth helpers. `db/` SQLite sessions.
- `app.py`, `pages/`, `utils/`, `validate_api.py`, `requirements.txt`: the legacy Streamlit
  prototype. Don't extend it; delete once the Fly app is live.

More detail: `docs/ARCHITECTURE.md` (structure, data flow, storage) and `docs/DECISIONS.md`
(the rules below, with reasons).

## Rules that matter

1. **`data/`, `analysis/`, `auth/` stay framework-free.** No `fastapi`, `streamlit`, or DB
   imports; they take inputs and return DataFrames or dicts.
2. **Read `docs/LEARNINGS.md` before touching `data/` or `analysis/`.** It lists the Yahoo and
   xmltodict quirks (`_as_list`, `_coerce`, lastmonth GAA, patch targets in tests).
3. **Minimise Yahoo calls.** Use collection endpoints over per-entity loops, and go through
   the cache in `data/cache.py`. Rate limits are shared across all users of the app.
4. **Demo parity.** Every live data function needs a `data/demo.py` counterpart, and live and
   demo routes share one compute/render helper (see `web/routes/projection.py`).
5. **One machine, one worker.** Sessions and cache live on a single Fly volume; never add
   `--workers N` or a second machine.
6. **Secrets only from env vars.** Never commit `.env`, tokens, or certs.

## Definition of done

- Tests added or updated for the change; `pytest tests/` passes. Tests use fixtures in
  `tests/fixtures/`, never live API calls. Name test modules for the feature they cover.
- UI changes checked in a browser, including the `/demo/*` version of the page.
- New gotchas go in `docs/LEARNINGS.md`; new architectural choices go in `docs/DECISIONS.md`.
- Work happens on a branch and lands through a PR. Don't create git worktrees unless asked.

## Check with the owner first

Changes to the OAuth flow or session storage, the cache's on-disk layout, new dependencies
or env vars, or anything that adds Yahoo calls per request. Otherwise, use your judgement and
explain choices in the PR.

## Where work is tracked

`docs/TODO.md` holds launch steps, open work, known issues, and ideas. Detailed specs for
upcoming features are in `docs/specs/`. The UI direction is in `docs/ui-brief.md`.

Out of scope for now: trade analysis, multi-season history, notifications, native apps.
