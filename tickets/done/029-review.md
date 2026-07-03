## Code Review — 029

**Files reviewed:**
- `web/routes/projection.py` (new) — `GET /projection` shell route; mirrors `waiver_shell` exactly.
- `web/templates/projection/index.html` (new) — shell template: header, team `<select>`, `#projection-matchup` container, empty-state.
- `web/main.py` (modified) — `projection_router` import + `include_router` after the waiver routers.
- `web/templates/base.html` (modified) — "Projection" nav link after "Waiver".
- `tests/test_projection_routes.py` (new) — 5 AC tests + 2 session-guard tests (authorized by the ticket's Verification section).

### Scope: CLEAN
Diff stays entirely inside `Touches` (projection.py, projection/index.html, main.py, base.html) plus the test file the ticket explicitly authorizes. No `/projection/matchup` fragment, no projection computation, no `/demo/projection` — all correctly deferred to 030/031. The `docs/improvements.md` "auth links to unauthenticated visitors" item was correctly left open (its fix requires touching route files outside this ticket) and the new Projection link inherits the same behaviour as the existing links, so it does not worsen the item.

### Architecture: CLEAN
- No framework imports in `data/`/`analysis/`/`auth/`; all orchestration is in the route.
- No new `data/` function — the shell reuses the existing `client.get_teams`, which itself uses `_as_list()` (data/client.py:177) and adds no un-coerced `stat['value']` access. No demo-counterpart obligation is triggered (demo is 031).
- No per-entity Yahoo loop: `get_teams` is a single collection call; `get_user_hockey_leagues` (one call, to resolve the league name) matches the established `waiver_shell`/overview pattern. API footprint is minimal as directed.
- `_get_league_key` imported from `web.routes.common` per ticket 028; SQL in that helper is parameterized (`?`).
- Conforms to active DECISIONS: 2026-05-30 "HTMX fragment pattern (shell + fragment split)" (shell-only here, `hx-get`/`hx-target` swap region, fragment deferred), 2026-04-19 "League context: session-state retained" (bare `/projection`, league read from session), 2026-04-19 "Nav shell: feature links per ticket" (order Overview → Waiver → Projection). `matchup_url` is parameterized as a context var (not hardcoded), so 031 can reuse `index.html` — the ticket-025 lesson is honoured.

### Verification adequacy: ADEQUATE
QA independently rendered the markup out-of-band (not just re-running the Engineer's tests), confirmed `matchup_url` appears exactly twice and both from the context var (no hardcoded third occurrence), verified nav ordering by index, and confirmed the template's `team.team_key`/`team.team_name` access resolves against the real `get_teams` dict shape. All 5 ACs plus both guards are exercised. Live HTMX swap behaviour is correctly deferred to owner-verification at 030 (the fragment endpoint doesn't exist yet).

### Security and data: CLEAN
No tokens/secrets/session IDs logged. Session guards present and correct (no cookie → 302 `/auth/login`; no league_key → 302 `/`). No new dependencies. No passwords or client-side auth introduced. No user input reaches the shell beyond the session cookie.

### Issues
- **nit:** The ticket text (Notes for the Engineer) cites the HTMX fragment decision as dated 2026-04-19; the active entry is dated 2026-05-30 (which supersedes the same-title 2026-04-19 entry). The substance is unchanged and the code conforms, so this is a ticket-text citation nit only — no code change required. Worth correcting in future ticket scoping to point at the live entry.

### Verdict: APPROVED

No code changes required. No `docs/improvements.md` entries added — the only finding is a stale DECISIONS date in the ticket text (no code impact), and the pre-existing "auth links to unauthenticated visitors" quality item is already tracked and untouched by this ticket.
