## Code Review — 022

**Files reviewed:**
- `web/routes/auth.py` — redirect target changed from `/auth/login` to `/?logged_out=1`; cookie deletion unchanged
- `web/templates/home.html` — conditional banner added above the league list heading
- `tests/test_auth_routes.py` — three location assertions updated to match new redirect
- `tests/test_home_routes.py` — three new tests (TC11–TC13) added by QA to cover banner render path
- `docs/improvements.md` — open item closed and moved to Closed section

### Scope: CLEAN

All five files are within or directly adjacent to the ticket's `Touches` list. `tests/test_auth_routes.py` was not listed in `Touches` but the ticket's "Notes for the Engineer" explicitly instructed the Engineer to update the assertions there — the omission is in the ticket's metadata, not in the diff. The `docs/improvements.md` close-out is permitted by the reviewer persona. `tests/test_home_routes.py` tests were added by QA, not the Engineer; that is a normal part of the QA process and does not constitute scope creep. No "while I'm here" changes observed.

### Architecture: CLEAN

- No framework imports in `data/`, `analysis/`, or `auth/` — the only files changed in `web/` are the route handler and a Jinja2 template.
- No Yahoo API calls introduced; no per-entity loop concerns.
- The template reads `request.query_params` directly in Jinja2; `request` is in scope because the home route calls `templates.TemplateResponse(request, ...)`. This is the correct and established pattern in this codebase.
- No new convention is introduced — the query-param approach for post-action notices is explicitly described in the ticket as the chosen approach (over flash cookies or server-side flash sessions), and is consistent with the "Out of scope" list. No `DECISIONS.md` entry is needed; this is implementation detail, not an architectural decision.
- No `DECISIONS.md` entries contradicted.

### Issues

None.

### Verdict: APPROVED

The change is minimal, correct, and scoped exactly to the problem. All five acceptance criteria pass per QA (329/329 tests). The banner conditional (`request.query_params.get("logged_out") == "1"`) is exact-value, preventing false positives on `?logged_out=0` or absent param. Cookie deletion was already correct and is unchanged. The redirect change eliminates the root cause (the OAuth round-trip on logout) cleanly.

No new improvements logged — the existing open item in `docs/improvements.md` was the source of this ticket and has been correctly moved to Closed.
