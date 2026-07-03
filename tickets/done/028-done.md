## Implementation complete — 028

**What I did:**
- Created `web/routes/common.py` as the canonical home for shared route-layer helpers (per DECISIONS.md 2026-05-30) and moved `_get_league_key` into it verbatim (same signature `_get_league_key(db, session_id: str) -> str | None`, same body, same underscore prefix).
- Removed the local `_get_league_key` definition from `web/routes/overview.py` and added `from web.routes.common import _get_league_key`.
- Changed `web/routes/waiver.py` to import `_get_league_key` from `web.routes.common` instead of `web.routes.overview`.

**Files changed:**
- `web/routes/common.py` — new file; defines the shared `_get_league_key` helper.
- `web/routes/overview.py` — removed local definition; now imports the helper from `web.routes.common`.
- `web/routes/waiver.py` — import source changed from `web.routes.overview` to `web.routes.common`.

**Acceptance criteria status (self-check):**
- [x] AC1: `web/routes/common.py` exists and defines `_get_league_key(db, session_id)` with the same signature/body it had in `overview.py` — verified: file present, `grep` shows the only definition is at `common.py:8`; body copied verbatim.
- [x] AC2: `overview.py` and `waiver.py` import `_get_league_key` from `web.routes.common` (no local definition, no import from `overview`) — verified: `grep -rn "_get_league_key" web/routes/` shows imports from `web.routes.common` in both files and no definition outside `common.py`; import smoke check confirms `_get_league_key.__module__ == "web.routes.common"`.
- [x] AC3: `GET /overview` still returns 200 for an authenticated session and renders the leaderboard — verified via `tests/test_overview_routes.py` (+ `_qa`) which exercise authenticated `/overview` and assert 200 + rendered content; full suite green. Not verified in a live browser (see limitations).
- [x] AC4: `GET /waiver` still returns 200 for an authenticated session and renders the filter form — verified via `tests/test_waiver_routes.py` which exercises authenticated `/waiver` and asserts 200 + rendered form; full suite green. Not verified in a live browser (see limitations).

**How to verify (for QA):**
- `grep -rn "_get_league_key" web/routes/` — definition only in `common.py`; `overview.py` and `waiver.py` import from `web.routes.common`, no import from `overview`.
- `python -c "from web.routes.common import _get_league_key; print(_get_league_key.__module__)"` — prints `web.routes.common`.
- `python -m pytest tests/` — 355 passed (route tests for `/overview` and `/waiver` included).
- Optional live check: `uvicorn web.main:app --reload`, log in, visit `/overview` and `/waiver` — both render as before.

**Scope notes:**
- None. Pure mechanical move as scoped; no other helpers touched.
- Pre-existing open `Type: bug` items in `docs/improvements.md` on `web/routes/overview.py` (leaderboard all-zero week; tied-worst cells not `bg-red-100`) are unrelated to this refactor and left untouched per Engineer rules (not scoped by this ticket).

**Known limitations / things I couldn't fully test:**
- Did not exercise `/overview` and `/waiver` in a live browser with a real Yahoo login — this environment has no Yahoo OAuth credentials. AC3/AC4 are covered by the existing authenticated route tests (mocked auth), which pass. This is a no-behaviour-change move, so the test coverage is the appropriate evidence.
