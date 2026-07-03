## Code Review — 031

**Files reviewed:**
- `web/routes/projection.py` (+132/-4) — new `public_router` with `GET /demo/projection` + `GET /demo/projection/matchup`; extracted shared `_render_matchup(...)` helper from `_matchup_impl`.
- `web/main.py` (+2) — registered `projection_public_router` alongside overview/waiver public routers.
- `tests/test_demo_projection_routes.py` (new, 11 tests) — covers all four ACs + a no-Yahoo-call assertion.

### Scope: CLEAN
Diff stays within `Touches` (`web/routes/projection.py`, `web/main.py`) plus the new test file. No drift into templates, `data/`, `analysis/`, or `auth/`. The demo shell reuses `projection/index.html` and `projection/_matchup.html` unchanged, passing only `matchup_url` / `selected_league_name` context — exactly as the ticket prescribed (029/030 parameterization). The pre-existing `docs/improvements.md` item ("converge on a single team query-param name") was correctly left open, since its fix touches `projection/index.html`, which is out of scope.

### Architecture: CLEAN
- No framework imports in pure layers — all changes live in the `web/` route layer. `data.demo` accessors (framework-free, already exist) are imported lazily inside the handlers, matching the overview/waiver demo pattern.
- No new `data/` function → no missing demo counterpart. The demo accessors `get_projection_context()` / `get_projection_pair_data()` already exist.
- No per-entity Yahoo loop; the demo path makes zero API calls. `test_demo_projection_no_yahoo_calls` asserts `make_session` is never invoked on either demo route, and it passes.
- **Refactor is behaviour-preserving for the live path.** `_matchup_impl` now hands its resolved inputs to `_render_matchup(...)`; the compute/tally/breakdown/render tail is byte-for-byte the same, with `scoreboard_data["week_start"]`/`["week_end"]` passed through as `week_start`/`week_end`. The `has_matchup=False` early-return branch is intentionally left inline in `_matchup_impl` (the demo path resolves a fixed pair and never hits it). Live `/projection` and `/projection/matchup` retain `Depends(require_user)` (projection.py:33, :253) — auth dependency untouched.
- Conforms to `docs/DECISIONS.md` 2026-05-30 "demo route pairing policy": the demo counterpart ships in the same ticket, satisfying the policy with no backlog deferral required. The 2026-05-30 "per-stat bulk fetch" decision is not engaged (demo makes no API calls; live path unchanged).
- Demo-route shape matches `web/routes/overview.py` / `web/routes/waiver.py`: `public_router = APIRouter()`, lazy `from data import demo as demo_module`, `"Demo League"` label, demo URLs in context, registered in `main.py` the same way. No implicit-decision drift.

### Verification adequacy: ADEQUATE
QA ran the full suite (385 passed) and, beyond the Engineer's mocked tests, exercised every demo route against the **real committed** `demo/data/projection_*.json` via `TestClient` (no patching): 200s with no cookie, "Demo League" shell, tally 9/0/5, non-zero per-player projections, and the roster-ordering swap on opponent selection. AC4 auth-guard confirmed (302 → `/auth/login`). The only unverified item — the in-browser HTMX swap painting the fragment — is correctly flagged owner-must-verify; the emitted `hx-get`/`hx-trigger="load"`/`hx-target` attributes are identical to the known-working 029/030 shell, so risk is low.

### Issues
None.

### Verdict: APPROVED

Clean on scope, architecture, and security. Demo routes are public by design, read only committed demo JSON, never construct a Yahoo session, and expose no authenticated data or client-side auth. No new `docs/improvements.md` entries needed; the one pre-existing item was appropriately left open for a follow-up shell-convergence ticket.
