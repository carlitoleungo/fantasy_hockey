# 003 — New project scaffold

## Summary

After the Tech Lead (ticket 001) selects the stack, set up the bare minimum new project structure: install the chosen framework and its dependencies into a new manifest, create the folder skeleton described in `docs/ARCHITECTURE.md`, and implement a single `/health` route that returns `{"status": "ok"}`. No auth, no database connection, no data calls — just "the framework is installed and the app starts." The existing Streamlit app (`app.py`, `requirements.txt`, `pages/`) is left completely untouched.

## Acceptance criteria

- [ ] A new dependency manifest exists at the path specified in `docs/ARCHITECTURE.md` (e.g. `requirements-web.txt`, `pyproject.toml`, or `package.json`). Installing from it in a clean virtualenv completes without errors.
- [ ] Running the framework's start command (documented in `docs/ARCHITECTURE.md` and/or a `README` update) starts a server without errors, and `curl -s -o /dev/null -w "%{http_code}" http://localhost:PORT/health` returns `200`. The response body contains the string `"ok"`.
- [ ] The folder structure matches the skeleton specified in `docs/ARCHITECTURE.md`. At minimum: an entry-point file, a routes (or views/controllers) directory, and a placeholder directory for the auth layer. These can be empty `__init__.py` files or framework-equivalent stubs.
- [ ] `streamlit run app.py` still starts without errors, confirming the scaffold did not damage the existing app.

## Files likely affected

- New framework entry-point (path per `docs/ARCHITECTURE.md`, e.g. `web/main.py` or `server/app.py`)
- New dependency manifest (path per `docs/ARCHITECTURE.md`)
- New folder skeleton (`__init__.py` stubs or equivalent)

## Dependencies

Requires 001 — `docs/ARCHITECTURE.md` must exist and name the framework, entry-point path, port, and health route URL before any file is created.

## Notes for the engineer

The exact files depend entirely on the framework named in ticket 001. Common patterns:

- **FastAPI**: entry point is `web/main.py` with `app = FastAPI()` and a `@app.get("/health")` route returning `{"status": "ok"}`.
- **Flask**: entry point is a `create_app()` factory in `web/__init__.py`; health route in a blueprint at `web/routes/health.py`.
- **Django**: `manage.py` + `web/settings.py`; health view added to `urls.py`.

Follow whatever ARCHITECTURE.md specifies — do not invent structure beyond what it describes.

**One hard invariant regardless of framework**: the new entry point must NOT import anything from `app.py` or `pages/`. Those are Streamlit files and will raise errors outside the Streamlit runtime. The preserved `data/`, `analysis/`, and `auth/` packages will be imported in later tickets once the auth and DB layers exist — do not import them here either. Keep the scaffold minimal.

## Notes for QA

Verify in a clean virtualenv: `python -m venv .venv-web && source .venv-web/bin/activate && pip install -r <new manifest>` must complete without errors. Start the server and confirm the health endpoint. Then in a separate terminal: `source .venv/bin/activate && streamlit run app.py` — the existing Streamlit app must load its login page without errors, confirming no existing files were touched.

## Tech Lead Review

**Files likely affected — corrected.** The ticket's list is correct in principle. Based on `docs/ARCHITECTURE.md` the concrete files are:
- `web/main.py` — FastAPI app factory with `/health` route
- `web/routes/health.py` — health route (or inline in `main.py`)
- `web/routes/__init__.py`, `web/middleware/__init__.py`, `web/templates/` — skeleton stubs
- `db/__init__.py` — placeholder (connection.py comes in 004a)
- `requirements-web.txt` — `fastapi uvicorn[standard] jinja2 itsdangerous python-multipart`
- `Dockerfile` — optional at this stage but low-cost to add

Do **not** create `db/connection.py` here — that belongs to ticket 004a.

**Complexity: S** (< 15 min). Stack is now named; this is file creation + a 5-line FastAPI app. The main risk is accidentally importing from `app.py` or `pages/` — the hard invariant in the ticket notes prevents that.

**No hidden dependencies.** Can run in parallel with 002 immediately after 001.
