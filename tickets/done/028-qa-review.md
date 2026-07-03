## QA Report — 028 (combined QA + review, Process: light)

**Ticket:** Extract shared route helper to web/routes/common.py
**Engineer handoff:** tickets/028-done.md
**QA date:** 2026-07-02

### Test plan (written before reading Engineer's verification)
- AC1: Read `web/routes/common.py`; confirm `_get_league_key(db, session_id)` is defined there. Compare its body byte-for-byte against the definition in the last committed `overview.py` (via `git show HEAD:web/routes/overview.py`). Failure = missing file, missing function, or altered signature/body.
- AC2: `grep -rn "_get_league_key" web/routes/` — the only `def` is in `common.py`; both `overview.py` and `waiver.py` show `from web.routes.common import _get_league_key`; no `from web.routes.overview import _get_league_key` anywhere. Failure = a second definition, or an import from `overview`.
- AC3: Run the suite and confirm `tests/test_overview_routes.py` exercises an authenticated `/overview` returning 200 with a rendered leaderboard. (No Yahoo creds in this env, so mocked-auth route tests stand in for the live browser walk, as directed.)
- AC4: Same for `tests/test_waiver_routes.py` — authenticated `/waiver` returns 200 with the filter form.
- Scope: `git diff --stat` limited to the three `Touches` files (+ the ticket status line).

### Test results

| # | Acceptance criterion | Result | Observation |
|---|----------------------|--------|-------------|
| 1 | `common.py` exists and defines `_get_league_key(db, session_id)` with same signature/body as in `overview.py` | PASS | `web/routes/common.py:8` defines `def _get_league_key(db, session_id: str) -> str | None:`. Body is byte-for-byte identical to `git show HEAD:web/routes/overview.py` (lines 18-23): same SELECT and `row["league_key"] if row and row["league_key"] else None` return. |
| 2 | `overview.py` and `waiver.py` import from `web.routes.common` (no local def, no import from overview) | PASS | `grep -rn "_get_league_key" web/routes/` shows the only `def` at `common.py:8`; `overview.py:12` and `waiver.py:20` both `from web.routes.common import _get_league_key`. Repo-wide grep confirms no `from web.routes.overview import _get_league_key` remains (the surviving `from web.routes.overview import` lines in `web/main.py` are for `public_router`/`router`, unrelated). |
| 3 | `GET /overview` returns 200 for an authenticated session and renders the leaderboard | PASS | `tests/test_overview_routes.py::test_overview_returns_200_with_leaderboard` inserts a session with `league_key="419.l.11111"` and asserts 200 with rendered content; passes. This exercises the moved `_get_league_key` path (reads `user_sessions`). Live-browser walk not possible (no Yahoo OAuth creds in this env) — covered by mocked-auth tests per task instructions. |
| 4 | `GET /waiver` returns 200 for an authenticated session and renders the filter form | PASS | `tests/test_waiver_routes.py::test_waiver_shell_returns_200_with_controls` (TC1) inserts a `league_key` session, asserts 200; `test_waiver_form_has_htmx_attributes` asserts `hx-post="/api/waiver/players"` present. Both pass. Same live-browser caveat as AC3. |

### Automated tests
- Command: `.venv/bin/python -m pytest tests/` (system `python3` has no pytest; used the project `.venv`)
- Tests run: 355 — passed: 355, failed: 0
- Targeted run of `tests/test_overview_routes.py tests/test_overview_routes_qa.py tests/test_waiver_routes.py`: 22 passed.
- New tests added: none needed — this is a mechanical move of a helper with no dedicated tests; the existing authenticated `/overview` and `/waiver` route tests fully cover the AC behaviour, and continued green after the move confirms behaviour is unchanged.

### Manual verification
- Live-browser walk of `/overview` and `/waiver` not performed: this environment has no Yahoo OAuth credentials. As directed, coverage is provided by the mocked-authenticated route tests, which drive the exact ACs (session with `league_key` → 200 → rendered leaderboard / filter form) and pass.
- Verified the change is behaviour-neutral by diffing: `git diff HEAD -- web/routes/overview.py` shows only the block removal + one import line; `web/routes/waiver.py` shows only the import source change (`web.routes.overview` → `web.routes.common`). No call sites changed — all four `overview.py` and both `waiver.py` invocations of `_get_league_key(...)` are unchanged.
- Test patch target note: `tests/test_waiver.py` patches `web.routes.waiver._get_league_key`; because the name is bound into the `waiver` module namespace by the new `from web.routes.common import` line, this patch target still resolves correctly (consistent with LEARNINGS "patch the importing module's namespace"). Those tests pass, confirming the move didn't break patching.

### Demo mode (if applicable)
N/A — the ticket touches `web/routes/` only, not `data/`. Demo routes were not modified (confirmed in the diff), and `tests/test_waiver_routes.py::test_demo_waiver_shell_returns_200` still passes.

### Review checks (light-ticket combined mode — Reviewer always-blockers)
- Framework import in `data/`/`analysis/`/`auth/`: PASS — none; change is confined to `web/routes/`.
- Raw `stat['value']` without `_coerce()`: PASS — no stat handling touched.
- Yahoo collection indexed without `_as_list()`: PASS — no Yahoo response handling touched.
- Per-entity Yahoo API loop where a bulk endpoint exists: PASS — no API calls touched.
- New live data function with no demo counterpart: PASS — `_get_league_key` is a moved route helper, not a new data function; demo routes untouched.
- Contradiction of an active `docs/DECISIONS.md` entry: PASS — this implements exactly the 2026-05-30 "Shared route helpers: web/routes/common.py is the canonical home" decision.
- Diff escapes the ticket's `Touches` list: PASS — `git diff --stat` shows only `web/routes/common.py` (new), `web/routes/overview.py`, `web/routes/waiver.py`, plus the ticket's own `## Status` line. No out-of-scope files.

No out-of-scope quality nits to log.

### Issues found
None.

### Notes
- Engineer's `028-done.md` reports "355 passed" — matches my independent run exactly.
- Pre-existing `Type: bug` items on `web/routes/overview.py` (leaderboard all-zero week; tied-worst cells) are unrelated to this refactor and correctly left untouched.

### Verdict: APPROVED
