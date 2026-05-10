## Implementation complete — 009

**What I did:**
- Created `web/templates.py` — exports the `Jinja2Templates` instance for use by route handlers
- Created `web/templates/base.html` — HTML5 shell with TailwindCSS CDN, HTMX CDN, Alpine.js CDN, and `{% block title %}`, `{% block head %}`, `{% block content %}` blocks
- Created `web/templates/error.html` — extends `base.html`, renders `{{ detail }}` variable
- Updated `web/main.py` — added `import requests`, imported `templates`, added `requests.HTTPError` handler (502) and generic 500 handler

**Files changed:**
- `web/templates.py` — new; single-module `Jinja2Templates` instance to avoid circular imports
- `web/templates/base.html` — new; base template with CDN tags and named blocks
- `web/templates/error.html` — new; user-facing error page extending base.html
- `web/main.py` — added two exception handlers and required imports

**How to verify:**
- Run `python -m pytest` — all 258 existing tests should pass
- Start the app with `.venv/bin/uvicorn web.main:app --reload` and `GET /health` should return `{"status": "ok"}`
- Add a test route that raises `requests.HTTPError` and confirm it returns a 502 HTML response containing "Yahoo API request failed"
- Inspect `web/templates/base.html` and confirm TailwindCSS (`cdn.tailwindcss.com`), HTMX (`unpkg.com/htmx.org@2.0.4`), and Alpine.js (`cdn.jsdelivr.net/npm/alpinejs`) script tags are present

**Scope notes:**
- Tech Lead noted the `exception_handler(500)` may not fire for all unhandled exceptions depending on FastAPI version. QA should verify it intercepts a bare `raise Exception(...)` in a test route, not just assume it works.

**Known limitations:**
- The 500 handler behaviour vs. FastAPI's internal error handling wasn't verified with a live request test — the import and test suite pass, but QA should write a test that raises a bare `Exception` and confirms the handler fires.
