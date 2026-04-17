# 009 — Base template and error handling

## Summary
Before any data page can render HTML, the app needs a Jinja2 template foundation and a
consistent error story. This ticket wires up `Jinja2Templates`, creates the `base.html`
shell (TailwindCSS CDN, HTMX CDN, Alpine.js CDN, named blocks), creates a minimal
`error.html` for user-facing error pages, and registers two exception handlers in
`web/main.py`: one for `requests.HTTPError` (Yahoo API failures) and one for unhandled
500s. All subsequent page tickets depend on this.

## Acceptance criteria
- [ ] `GET /health` still returns `{"status": "ok"}` (smoke test — confirms Jinja2 setup
  did not break the app factory)
- [ ] A route that raises `requests.HTTPError` returns an HTML response with HTTP status
  500 that includes a recognisable error message (e.g. "Something went wrong") rather than
  a raw FastAPI JSON error body
- [ ] `web/templates/base.html` includes TailwindCSS, HTMX, and Alpine.js CDN `<script>`/
  `<link>` tags and defines at least `{% block title %}`, `{% block content %}`, and
  `{% block head %}` blocks for child templates to override

## Files likely affected
- `web/templates/base.html` (new)
- `web/templates/error.html` (new)
- `web/main.py`
- `web/templates.py` (new — single-line module that exports the `Jinja2Templates` instance
  so routes can `from web.templates import templates` without importing from `main.py`)

## Dependencies
- None (no prior ticket required)

## Notes for the engineer
- Create `web/templates.py` with one line:
  ```python
  from fastapi.templating import Jinja2Templates
  templates = Jinja2Templates(directory="web/templates")
  ```
  All route handlers will `from web.templates import templates`. Do not define the
  `Jinja2Templates` instance in `main.py` — that creates a circular import once routes
  start importing it.
- `base.html` structure: standard HTML5 shell with `<head>` containing
  `{% block head %}{% endblock %}` for per-page `<title>` and meta overrides, TailwindCSS
  CDN (`<script src="https://cdn.tailwindcss.com">`), HTMX CDN
  (`<script src="https://unpkg.com/htmx.org@2.0.4">`), Alpine.js CDN
  (`<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer>`),
  and a `<body>` with `{% block content %}{% endblock %}`.
- `error.html` should extend `base.html`, set a `{% block title %}Error{% endblock %}`,
  and render a simple message using a `{{ detail }}` template variable. Keep it minimal —
  a heading and a paragraph is enough.
- In `web/main.py`, add two exception handlers:
  1. `@app.exception_handler(requests.HTTPError)` — returns
     `templates.TemplateResponse("error.html", {"request": request, "detail": "Yahoo API request failed. Please try again."}, status_code=502)`
  2. `@app.exception_handler(500)` — returns
     `templates.TemplateResponse("error.html", {"request": request, "detail": "Something went wrong."}, status_code=500)`
  Import `requests` and `templates` at the top of `main.py`.
- `fastapi.templating.Jinja2Templates` ships with `fastapi` — no new dependency.
- This ticket does NOT add `StaticFiles` mounting — there are no static assets yet.
  Static file mounting can be added when the first CSS override or favicon lands.
- The 4-file count (base.html, error.html, main.py, templates.py) slightly exceeds the
  3-file guideline, but templates.py is a 2-line config module, not substantive logic.
  The primary work is the two templates and the two exception handlers.

## Notes for QA
- Run the full test suite — confirm all existing tests still pass.
- Write a test in `tests/test_error_handling.py` that creates a minimal test app with a
  route that raises `requests.HTTPError` and asserts the response is 502 HTML containing
  "Yahoo API request failed".
- Inspect `base.html` and confirm all three CDN tags are present (Tailwind, HTMX, Alpine).
- Confirm `web/templates.py` exports `templates` and that importing it does not cause errors.

---

## Tech Lead Review

**Complexity: M** — four files (two HTML templates, `web/templates.py`, `web/main.py` exception handlers). Each piece is small but requires getting the Jinja2 instance wiring right so downstream routes don't hit circular imports.

**Hidden dependency:** `web/main.py` currently does not import `requests`. The `@app.exception_handler(requests.HTTPError)` handler requires adding that import. Straightforward, just easy to miss.

**Risk — exception handler for HTTP 500:** FastAPI's `exception_handler(500)` receives `Exception` not `HTTPException`, and may not fire for all unhandled exceptions depending on FastAPI version. Engineer should verify the handler actually intercepts a bare `raise Exception(...)` in a test route, not just assume it works.

**Circular import concern:** The ticket correctly flags this — `Jinja2Templates` must live in `web/templates.py`, not `web/main.py`, because routes will import it. This is the right call; no change needed.

**This ticket is a hard prerequisite for 011.** No HTML can render until `base.html` exists and `templates` is wired up.
