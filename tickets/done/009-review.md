## Code Review — 009

**Files reviewed:**
- `web/templates.py` — new 2-line module exporting `Jinja2Templates` instance
- `web/templates/base.html` — new HTML5 shell with CDN tags and template blocks
- `web/templates/error.html` — new error page extending `base.html`
- `web/main.py` — two exception handlers added; `requests` and `templates` imports added
- `tests/test_error_handling.py` — new test file, 7 tests covering both handlers

### Scope: CLEAN

All four files specified in the ticket were created/modified. No extra changes beyond the spec.

### Architecture: CLEAN

No framework imports in `data/` or `analysis/`. `web/templates.py` correctly isolates the `Jinja2Templates` instance to prevent circular imports. No per-entity API loops or stat coercion concerns (this ticket touches no data layer).

### Issues

- **Must fix:** None.

- **Should fix:** The `client` fixture in `test_error_handling.py` is function-scoped (default), so `@app.get("/test/http-error")` and `@app.get("/test/unhandled")` are re-registered on the production `app` object once per test — 7 times total for this file. FastAPI/Starlette silently accumulates duplicate route entries in its route list, which is benign here but sloppy. The fixture should be `scope="module"` so routes are registered once per test run, not once per test function.

- **Nit:** `error.html` hardcodes `<h1>Something went wrong</h1>` as the heading. For the 500 handler this means the user sees "Something went wrong" in the heading *and* "Something went wrong." in the paragraph — minor duplication. Either remove the static `<h1>` and use only `{{ detail }}`, or accept the redundancy (it's fine UX-wise since the heading and paragraph could be considered different roles). Not worth blocking.

### Verdict: APPROVED

All three acceptance criteria pass, all 265 tests pass, and the Starlette 1.0 `TemplateResponse` API fix is confirmed in place. The fixture scoping issue is real but does not affect test correctness or production behavior — it can be cleaned up next time the test file is touched.
