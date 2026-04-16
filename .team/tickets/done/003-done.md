# Implementation complete — 003

**What I did:**
- Created `requirements-web.txt` with `fastapi uvicorn[standard] jinja2 itsdangerous python-multipart`
- Created `web/main.py` — FastAPI app factory that mounts the health router
- Created `web/routes/health.py` — `GET /health` returns `{"status": "ok"}`
- Created `web/__init__.py`, `web/routes/__init__.py`, `web/middleware/__init__.py` — package stubs
- Created `db/__init__.py` — placeholder; `connection.py` deferred to ticket 004a
- Created `web/templates/.gitkeep` and `web/static/.gitkeep` — empty directory placeholders
- Created `Dockerfile` — `python:3.11-slim`, installs `requirements-web.txt`, runs `uvicorn web.main:app` on port 8000

No imports from `app.py`, `pages/`, `data/`, `analysis/`, or `auth/` — the scaffold is fully isolated.

**Files changed:**
- `requirements-web.txt` — new; web framework dependencies
- `web/main.py` — new; FastAPI app factory
- `web/routes/health.py` — new; `/health` route
- `web/__init__.py` — new; package marker
- `web/routes/__init__.py` — new; package marker
- `web/middleware/__init__.py` — new; package marker
- `db/__init__.py` — new; package marker placeholder
- `web/templates/.gitkeep` — new; directory placeholder
- `web/static/.gitkeep` — new; directory placeholder
- `Dockerfile` — new; container image definition

**How to verify:**
1. In a clean virtualenv: `python -m venv .venv-web && source .venv-web/bin/activate && pip install -r requirements-web.txt` — should complete without errors.
2. Start the server: `uvicorn web.main:app --reload` (or `uvicorn web.main:app --port 8000`).
3. In another terminal: `curl -s http://localhost:8000/health` — should return `{"status":"ok"}` with HTTP 200.
4. Confirm HTTP status: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` — should print `200`.
5. In a separate terminal (original venv): `streamlit run app.py` — the existing Streamlit app must start normally, confirming no existing files were touched.

**Scope notes:**
- `db/connection.py` is explicitly deferred to ticket 004a per the Tech Lead review note.
- Route stubs for `auth.py`, `leagues.py`, `waiver.py`, `projection.py`, `demo.py` are not created here — they belong to their respective tickets.
- `fly.toml` is not created; it requires a Fly.io app name which isn't known yet. Low-cost to add when deployment is wired up.

**Known limitations:**
- I cannot run the server myself to confirm the health check end-to-end — QA must do the clean-venv verification step above.
