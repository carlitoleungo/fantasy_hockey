# Key Decisions Log

Historical implementation decisions, **newest first**. Read this file when you need
context on *why* something was done a particular way.

> **Scope:** This file covers decisions that apply to the current FastAPI stack and the preserved data/analysis/auth layers. For decisions specific to the Streamlit prototype (session state patterns, Streamlit page structure, Streamlit token storage), see [`docs/archive/prototype-decisions.md`](archive/prototype-decisions.md).

---

### matchups.py: current_week always re-fetched to reflect intra-week stats (2026-05-31)

Supersedes the "matchups.py: current week is included in delta fetch; won't refresh mid-week (2026-03-03)" entry.

**Question / context:** The `bug-week23-all-zeroes` fix discovered that once `current_week` was cached, subsequent same-session calls fetched nothing new — intra-week stat updates were invisible until the cache was manually cleared. The fix changed the delta-fetch guard to always include `current_week` in `weeks_to_fetch`, regardless of what is already cached.

**Options considered:**
- **A (cache once, manual clear):** Original behaviour. `current_week` is fetched on first call; subsequent calls skip it. Zero extra API calls after first. Requires manual cache clear to see intra-week updates — unacceptable for a daily-use tool where Yahoo updates scores as games are played.
- **B (always re-fetch current_week, chosen):** Unconditionally append `current_week` to `weeks_to_fetch` on every call. Costs 1 extra Yahoo API call per session. Guarantees intra-week stats are always current.

**Decision:** Option B — `current_week` is appended unconditionally on every `get_matchups()` call (see `data/matchups.py` lines 44–46). Introduced in the `bug-week23-all-zeroes` fix; correct ongoing behaviour.

**Why:** The app is used to make same-day waiver decisions. Stats update as games are played throughout the week; a tool that shows stale intra-week numbers is unreliable for its core use case. One extra API call per session is an acceptable and negligible cost.

**Revisit if:** Yahoo rate-limit warnings appear in practice; at that point, a time-based TTL on `current_week`'s cache entry (e.g. refresh at most once per hour) would reduce calls without fully reverting to cache-once behaviour.

---

### Team process: Engineer owns automated test coverage; QA does not fill gaps (2026-05-31)

**Question / context:** Tickets 022 and 023 both shipped with missing automated test coverage for acceptance-criteria paths; the Test Engineer wrote the missing tests during the QA pass. This is a positive outcome for coverage but creates an incentive for Engineers to ship under-tested implementations. No policy existed for how to handle the gap.

**Options considered:**
- **A (QA fills gaps):** Codify the current pattern — if the Engineer omits tests, QA adds them. Maximum coverage; QA is never blocked. Risk: Engineers learn thin test coverage is acceptable and QA is the backstop.
- **B (ticket returned for missing tests, chosen):** If automated acceptance-criteria coverage is absent, QA returns the ticket to the Engineer before proceeding. QA may add supplementary edge-case or regression tests on top of existing AC coverage, but is not responsible for writing the primary AC test suite.

**Decision:** Option B — missing automated coverage for acceptance criteria is a return condition, not a QA responsibility. The Engineer must write tests for new code paths before QA begins.

**Why:** Test coverage for implemented behaviour is the Engineer's responsibility. Allowing QA to fill the gap shifts accountability and encourages under-tested implementations. A single returned ticket is a cheaper correction than accruing a pattern of thin coverage. This keeps QA focused on independent verification, not co-implementation.

**Revisit if:** The project moves to a model where test authorship is intentionally shared (e.g. pairing); or if ticket return overhead measurably slows delivery and an alternative quality gate is in place.

---

### Auth: optional_user dependency for semi-public routes (2026-05-30)

**Question / context:** `GET /` needs to serve unauthenticated visitors (login CTA,
logged-out banner) without redirecting to Yahoo OAuth. The existing binary model —
`Depends(require_user)` for protected routes, no session dependency for fully public
routes — does not cover routes that behave differently based on whether a session exists.

**Options considered:**
- **A (catch RequiresLogin in the route handler):** Keep `require_user` unchanged; handle
  the exception inside `home.py`. Not possible — FastAPI executes dependencies before the
  handler runs, so `RequiresLogin` is caught by the global handler in `main.py` first.
- **B (public route with manual session lookup):** Make `GET /` a fully public route and
  re-implement session lookup and token refresh inline. Duplicates security-critical logic;
  any future change to `require_user` must also be applied to the inline copy.
- **C (optional_user dependency, chosen):** Add `optional_user` to
  `web/middleware/session.py` alongside `require_user`. Identical DB lookup and token
  refresh path; on any failure condition returns `None` instead of raising `RequiresLogin`.
  The route handler branches on `current_user is None`.

**Decision:** Option C — `optional_user` in `web/middleware/session.py` as the canonical
dependency for routes that serve both authenticated and unauthenticated users.

**Why:** Option A is mechanically impossible with FastAPI's dependency injection model.
Option B duplicates security-critical logic that must stay in sync with `require_user`.
Option C is a minimal, additive change that reuses the full session validation path
(including token refresh and stale-row cleanup) and is easy to audit. Co-locating
`optional_user` with `require_user` in the same module keeps all session concerns together
and makes the naming intent clear.

**Revisit if:** A second semi-public route is needed with meaningfully different behaviour
(e.g. a full public landing page with personalised content when logged in); confirm at that
point whether `optional_user` is still the right fit or whether a more granular approach
(e.g. a `soft_user` dependency that also injects league context) is warranted.

---

### Web routes: demo route pairing policy (2026-05-30)

**Question / context:** The architecture rules require a `data/demo.py` counterpart for every new `data/` function, but no equivalent rule existed for web routes. Tickets 015 and 016 shipped `/overview` and `/overview/head-to-head` with no `/demo/...` counterparts and no follow-up tickets; tickets 018/019a/019b built demo routes inline. Audit 001 flagged the inconsistency.

**Options considered:**
- **A (same ticket):** Every authenticated feature route gets a `/demo/...` counterpart in the same ticket. Guarantees full demo parity at all times. Too rigid — demo scaffolding for routes that reuse existing `data/demo.py` functions can add non-trivial scope mid-ticket.
- **B (explicit deferral):** Demo routes may be deferred, but only if a backlog ticket is filed in the same commit that ships the authenticated route. Deferred-with-no-ticket (what 015/016 did) is not allowed.

**Decision:** Option B — demo routes may be deferred, but deferral requires a backlog ticket filed in the same commit. Shipping an authenticated feature route with no demo counterpart and no follow-up ticket is a process violation.

**Why:** Option A is ideal but forces demo complexity into tickets where it adds churn. Option B preserves flexibility without allowing silent omission — the explicit ticket requirement ensures the gap is tracked as scoped work, not forgotten. The project description promises demo mode for unauthenticated visitors; omitting it without a clear plan violates that contract.

**Revisit if:** Demo coverage reaches 100% and is naturally maintained going forward; or the project removes demo mode entirely (e.g. all users are required to authenticate).

---

### Waiver and projection routes: per-stat bulk fetch, never per-player (2026-05-30)

**Question / context:** `_waiver_post_impl` in `web/routes/waiver.py` iterates over the selected stats and for each one checks the cache, fetches from Yahoo if stale, and writes back. This is one cache check + one bulk Yahoo API call per stat. No entry existed in DECISIONS.md, but the projection route will face the same question.

**Options considered:**
- **A (per-stat, current):** One cache read + one bulk API call per selected stat. Aligns with the Yahoo API surface: the available-players endpoint returns players sorted by one stat per call. Cache granularity is per-stat, so individual stats can expire independently.
- **B (single call, all stats):** Fetch all stats in one call and cache everything. Fewer API calls, but would require a different endpoint structure and cannot express per-stat TTLs.

**Decision:** Option A — per-stat cache reads, one bulk Yahoo API call per stat, never a per-player loop. The projection route must follow this same pattern when it is built.

**Why:** The Yahoo available-players endpoint is designed around one sort stat per request; Option B would fight the API surface. Per-stat caching also keeps TTLs tight and avoids caching data the user did not request. The per-player loop anti-pattern is explicitly prohibited by CLAUDE.md's "Minimise API calls" rule.

**Revisit if:** Yahoo exposes a bulk endpoint that returns multiple stat rankings in a single call; or the number of selected stats per request grows large enough that sequential API calls create a perceptible latency problem (at which point concurrent async fetches may be warranted).

---

### Shared route helpers: web/routes/common.py is the canonical home (2026-05-30)

**Question / context:** `_get_league_key` was defined in `web/routes/overview.py` (ticket 015) and imported by other route modules (ticket 016 and future tickets). The underscore prefix signals module-private by Python convention, but the function is intentionally shared — a contradiction ticket 015 acknowledged in its scope notes but left unresolved. Audit 001 surfaced this as an implicit decision.

**Options considered:**
- **A (status quo):** Shared helpers live in the module that first needs them. No new files. Cross-module imports of underscore-prefixed names are surprising and violate Python convention; intent is unclear to a new reader.
- **B (common.py):** Move shared route-layer helpers to `web/routes/common.py`. Explicit sharing intent; mirrors the `data/client.py` pattern where `_as_list` and `_coerce` are shared across the data layer. Requires a small refactor ticket to move `_get_league_key` and update import sites.

**Decision:** Option B — `web/routes/common.py` is the canonical home for helpers shared across route modules. The current state (helper in `overview.py`) is an interim state that should be resolved in a dedicated refactor ticket before the next feature route ships.

**Why:** Cross-module imports of underscore-prefixed names violate Python naming convention and mislead future readers into thinking the import is accidental or fragile. A dedicated `common.py` makes the sharing intent unambiguous and keeps each route module's scope clean. This mirrors the established pattern in the data layer.

**Revisit if:** The number of shared route helpers grows large enough to warrant splitting by concern (e.g. `common/auth_helpers.py`, `common/template_helpers.py`); or a helper becomes complex enough to need its own tests, at which point a sub-package may be appropriate.

---

### Feature pages: HTMX fragment pattern with shell + fragment template split (2026-05-30)

Supersedes the 2026-04-19 entry of the same title. Two changes: (1) corrects a factual error — the 2026-04-19 entry read "015 (head-to-head)" but ticket 015 is the leaderboard and ticket 016 is head-to-head; (2) adds the missing `Revisit if` clause.

**Question / context:** Per scoping brief `013` Decision 1, each feature page needs a strategy for handling filter-driven data updates without a full page reload.

**Options considered:**
- **A (full-page re-render):** Filter POST returns a full HTML response. Simple, no partial-swap complexity. Unacceptable for waiver wire's per-(position, stat) lazy-loading, which inherently requires fragment fetches.
- **B (HTMX fragment, chosen):** Each page is split into a full-page shell (`index.html`) plus one or more `_fragment.html` templates returned by dedicated fragment route handlers. Filter controls use `hx-get` / `hx-post` + `hx-target` to swap only the fragment.
- **C (Alpine.js client-side filtering):** Preload all data; filter in the browser. The hybrid "is this filter client or server?" mental model adds cognitive overhead, and the waiver wire player pool is too large to preload.

**Decision:** Option B — HTMX fragment pattern. Ticket 014 establishes the convention; ticket 015 (leaderboard) and ticket 016 (head-to-head) inherit it. All future feature pages follow the same shell + fragment split.

**Why:** Waiver wire lazy-loading makes fragment fetches unavoidable; extending the same pattern to all feature pages keeps the mental model consistent and avoids a hybrid approach. Matches ARCHITECTURE.md Key patterns #5.

**Revisit if:** A future feature page requires rich client-side interactivity beyond filter swaps (e.g. drag-and-drop, live editing) where an Alpine.js component is more natural than an HTMX round-trip; or the number of fragment endpoints per page grows large enough that a lightweight JSON API plus client-side rendering becomes simpler to maintain.

---

### Feature pages: HTMX fragment pattern with shell + fragment template split (2026-04-19)

Per scoping brief `013` Decision 1. Each feature page is split into `web/templates/<feature>/index.html` (full-page shell: layout, filter controls, initial state) plus one or more fragment templates (e.g. `_table.html`) returned by separate route handlers. Filter controls use `hx-get` / `hx-post` with `hx-target` to swap only the fragment — not the whole page. Chosen over full-page re-render (Option A) because waiver wire's per-(position, stat) lazy-loading requires fragment fetches anyway, and over Alpine-side filtering (Option C) because the hybrid "is this filter client or server?" mental model is not worth the perceived-UX gain and waiver wire's player pool is too large to preload. This also matches ARCHITECTURE.md Key patterns #5. Ticket 014 is the first page to establish the convention; 015 (head-to-head) and the waiver wire ticket inherit it. *(Superseded 2026-05-30 — factual error corrected and `Revisit if` added; see entry above.)*

### Feature pages: rank → Tailwind class mapping lives in templates, not analysis (2026-04-19)

Per scoping brief `013` Decision 2. `analysis/team_scores.avg_ranks()` continues to return integer ranks (1..N). A Jinja filter or macro — added in ticket 014 alongside the first page that needs it — maps `(rank, team_count) → Tailwind class` (best rank → `bg-green-100`, worst rank → `bg-red-100`, otherwise no background). Chosen over server-computed class strings (Option A) to preserve the ARCHITECTURE.md invariant that `analysis/` has no framework or styling dependencies, and over client-side Alpine styling (Option C) because shipping raw ranks only to re-derive min/max in JS duplicates information already computed server-side. Team count is `len(rows)` at render time, so the template has everything it needs.

### League context: session-state propagation retained; path-based URLs deferred (2026-04-19)

Per scoping brief `013` Decision 3. Kept the existing `user_sessions.league_key` session-state approach (ticket 011). Feature routes stay bare (`/overview`, `/waiver`, `/projection`) and look up the selected league from the session row via the `require_user` dependency. Rejected path-based URLs (`/leagues/{key}/overview`, Option A) for now because (a) the project is explicitly single-user local use per CLAUDE.md "Out of scope," making multi-tab and URL-sharing speculative future needs, and (b) ticket 011 already built the session-state plumbing, so Option A would cost a preceding refactor ticket before ticket 014 can proceed. **Revisit trigger:** when multi-user public deployment is scoped (alongside per-user cache storage, already on the roadmap), re-evaluate — bookmarkable league URLs and multi-tab become more valuable in a shared deployment. Not chosen: Option C (query-string + session fallback) — hybrid sources of truth are worse than either pure approach.

### Nav shell: minimal league label + logout in base.html; feature links added per ticket (2026-04-19)

Per scoping brief `013` Decision 4. Ticket 014 adds a minimal header to `web/templates/base.html` showing the selected league name (linking back to `/` for league switching) and a logout link. Feature-page links (Overview, Waiver, Projection) are added to the header as each page lands, not up front. Chosen over building the full nav now (Option A) because designing links for pages that don't exist risks drift, and over deferring nav entirely (Option B) because every subsequent ticket would have to retrofit the shared header. Convention for adding feature links: each feature page ticket appends its own nav entry in the same block; ordering matches the roadmap order (Overview → Waiver → Projection).

---

### Stack: FastAPI over Flask or Django as the backend framework (2026-04-10)

**Question / context:** Choosing the backend framework for the public rebuild of the Streamlit prototype.

**Options considered:**
- **Flask:** Synchronous by default; OAuth callback handling and sessions require extra libraries (Flask-Login, Blueprints) to reach feature parity.
- **Django:** ORM, admin, and templating are heavy for a thin API-proxy app; its opinionated project layout conflicts with the existing `data/`/`analysis/` module structure.
- **FastAPI (chosen).**

**Decision:** FastAPI.

**Why:** Async-native request handling supports concurrent per-user Yahoo OAuth callbacks without threading configuration; automatic OpenAPI docs aid single-engineer maintenance; Pydantic validation integrates cleanly with the existing Python data stack.

**Revisit if:** The app grows needs FastAPI serves poorly (e.g. a heavy admin/CMS surface where Django's batteries pay off), or a framework change is already forced by an infrastructure migration.

### Stack: FastAPI + HTMX + Jinja2; no JS build pipeline (2026-04-10)

**Question / context:** Choosing the frontend approach for a single-engineer Python team building a UI that is tables and filters, not a rich SPA.

**Options considered:**
- **React + FastAPI:** Adds a build pipeline and a language context switch.
- **Vue:** Same trade-offs as React at smaller scale.
- **Server-rendered Jinja2 + HTMX (chosen).**

**Decision:** Jinja2 templates + HTMX (+ Alpine.js and TailwindCSS via CDN); no JS build pipeline.

**Why:** HTMX handles partial-page updates without a JS framework or build step; the whole UI stays in Python-adjacent territory the owner can maintain alone.

**Revisit if:** The UI grows rich client-side interactivity (drag-and-drop, live editing, offline state) that HTMX round-trips can't express cleanly — see also the 2026-05-30 HTMX fragment entry's revisit clause.

### Platform: responsive web only; PWA deferred (2026-04-10)

**Question / context:** Whether mobile use requires a native app or PWA.

**Options considered:**
- **React Native:** Rejected — two codebases and app-store friction for marginal UX gain.
- **PWA:** Deferred — a `manifest.json` can be added later without architecture change.
- **Responsive web (chosen).**

**Decision:** Responsive web only.

**Why:** The waiver wire UX (select filters, scan table, pick player) fits a mobile browser without native code.

**Revisit if:** Users ask for offline access or home-screen install — the PWA path is additive and cheap at that point.

### Runtime: single uvicorn worker (2026-04-10)

**Question / context:** How many worker processes to run given SQLite as the session store.

**Options considered:**
- **Multiple workers with Postgres:** Adds managed-DB cost and ops complexity.
- **Single uvicorn worker (chosen).**

**Decision:** Single uvicorn worker.

**Why:** SQLite is not safe for concurrent writes across multiple processes; a single worker eliminates write-lock contention with no throughput cost at the expected scale (dozens–low hundreds of concurrent users).

**Revisit if:** Sustained concurrency outgrows one worker — any move to multiple workers must be scoped together with a Postgres (or equivalent) migration, never independently.

### Storage: SQLite for session/nonce storage (2026-04-10)

**Question / context:** Where to store OAuth session tokens and CSRF nonces.

**Options considered:**
- **Redis:** Adds a second service to operate.
- **Postgres:** Adds cost and managed-DB complexity.
- **SQLite (chosen).**

**Decision:** SQLite at `/data/app.db` (tables `oauth_states`, `user_sessions`).

**Why:** Zero infrastructure; single file; WAL mode handles concurrent reads; `DELETE … WHERE state = ?` is atomic within one process.

**Revisit if:** The deployment moves to multiple processes or machines (shared write access breaks the single-worker assumption above).

### Deployment: Fly.io with persistent volume (2026-04-10)

**Question / context:** Choosing a hosting platform for the public app.

**Options considered:**
- **Railway:** Similar DX, less mature persistent-volume support.
- **AWS ECS:** Excessive operational overhead for a single engineer.
- **Fly.io (chosen).**

**Decision:** Fly.io, single region (`iad`), 1 container + 1 persistent volume at `/data`.

**Why:** Container-based one-command deploys; the persistent volume solves cache ephemerality without adding an object-storage SDK; North American single-region is sufficient for the audience.

**Revisit if:** Fly.io pricing/free-tier changes materially, or the audience grows to need multi-region.

### Cache: parquet cache stays on local disk (`/data/cache/`) (2026-04-10)

**Question / context:** Whether the prototype's parquet cache layer needs a new storage backend for the deployed app.

**Options considered:**
- **S3 / Cloudflare R2:** Would require modifying `cache.py` and adding an SDK dependency.
- **Local disk on the persistent volume (chosen).**

**Decision:** `data/cache.py` unchanged; `CACHE_DIR` env var points at `/data/cache/` on the Fly.io volume.

**Why:** Zero code changes to a stable module; the persistent volume makes disk storage durable across deploys.

**Revisit if:** Per-user cache storage is scoped for shared deployment (already on the roadmap) — the keying scheme changes then, and object storage should be re-evaluated at the same time.

### Auth: server-side session — tokens in DB, session_id in cookie (2026-04-10)

**Question / context:** Where OAuth tokens live between requests.

**Options considered:**
- **Signed cookie with tokens embedded:** Simpler, but tokens leave the server on every request.
- **Server-side session (chosen).**

**Decision:** Tokens stored in the `user_sessions` table; the browser holds only an opaque `session_id` cookie (`HttpOnly; Secure; SameSite=Lax`).

**Why:** Long-lived OAuth tokens are sensitive credentials; keeping them in the DB limits exposure if a cookie is stolen or leaked.

**Revisit if:** Horizontal scaling requires a shared session store (see the SQLite entry's revisit clause) — the cookie contract can stay the same while the backing store changes.

---

### client.py: bulk teams/stats endpoint replaces per-team fetching (2026-03-23)
`get_all_teams_week_stats()` uses `/league/{key}/teams/stats;type=week;week={w}` to fetch every team's stats for a week in a single API call. This replaces the previous pattern of calling `get_team_week_stats()` once per team per week. For a 12-team league over 20 weeks, this reduces API calls from ~240 to ~20 (plus setup calls). `matchups.py` now uses this bulk endpoint exclusively. The per-team `get_team_week_stats()` is retained in `client.py` for cases where only one team's stats are needed.

### client.py: _coerce() handles None values, not just '-' (2026-03-23)
The Yahoo API can return `None` for stat values (not just the string `'-'`). `_coerce()` and the `games_played` handler now treat `None` identically to `'-'` — coerced to 0. This fixes the `float() argument must be a string or a real number, not 'NoneType'` error.

### players.py: type=lastmonth is the correct param for last-30-day player stats (2026-03-23)
Confirmed via validate_api.py against a live league. `date=lastmonth` and `week=lastmonth` both return season totals. `out=stats` on the league players collection endpoint also always returns season totals regardless of `sort_type`. Only `/player/{key}/stats;type=lastmonth` (and the batch form `/players;player_keys={keys}/stats;type=lastmonth`) returns the last 30 days.

### players.py: two API calls per page of 25 players (2026-03-23)
`get_available_players()` uses a two-call-per-page pattern:
1. `/leagues;league_keys={key}/players;status=A;sort=OR;sort_type=season;out=stats;start={n};count=25` — player list with season stats inline and player keys
2. `/players;player_keys={keys}/stats;type=lastmonth` — batch lastmonth stats for those same keys

This gives both stat periods in 2 API calls per page (8 total for 100 players) instead of 1+N. The batch lastmonth call returns `{player_key: stats}` only — no metadata — so metadata is taken from the season response and re-attached by the caller.

### players.py: imports private helpers from data/client.py (2026-03-23)
`data/players.py` imports `_get`, `_as_list`, `_coerce`, and `BASE_URL` directly from `data/client.py`. These are intentionally shared across the data layer. The same patch-target rule applies: tests for `players.py` must patch `data.players._get`, not `data.client._get`.

---

### Auth: yahoo_oauth not used for the OAuth flow (2026-03-03)
`yahoo_oauth`'s `OAuth2` class assumes interactive terminal input — it opens a browser and waits for the user to paste an authorisation code. The app uses a redirect-based callback: Yahoo sends the user back to the redirect URI with `?code=...`. These are incompatible. The auth flow is implemented directly with `requests` instead. The core pattern (check validity → refresh if needed → return authenticated session) is preserved in `auth/oauth.py`.

**Revisit if:** The `yahoo_oauth` library is updated to support redirect-based OAuth 2.0 flows natively, reducing the maintenance burden of the hand-rolled `auth/oauth.py` implementation.

### client.py: unknown and display-only stats silently skipped (2026-03-03)
The notebook emitted `"Unknown Stat ID: 22"` columns for unrecognised stat IDs and relied on the caller to drop them (`df.drop(columns=['Unknown Stat ID: 22'])`). `client.get_team_week_stats()` instead silently ignores any stat not in the enabled categories lookup. This keeps the DataFrame clean without requiring callers to know which IDs to drop.

### client.py: _as_list() handles the single-item xmltodict gotcha centrally (2026-03-03)
Rather than scattering `if int(@count) == 1` checks (as the notebook did for teams), a single `_as_list(value)` helper normalises any dict-or-list value to always be a list. Used on: the stat categories list, `stat_position_type` (which can be a list when a stat applies to multiple position types), the teams list, and the per-week stat list.

**Revisit if:** The project switches from `xmltodict` to a structured XML parser or a JSON-native Yahoo API response format, in which case the single-item ambiguity disappears and `_as_list` can be removed.

### matchups.py: delta fetch uses max(week) from cache data, not last_updated timestamp (2026-03-03)
`cache.last_updated()` returns when something was written (a datetime), not which weeks are present. For the delta fetch pattern, what matters is which week numbers exist in the data. `_last_cached_week()` reads `df['week'].max()` from the cached parquet file. `cache.last_updated()` / `cache.is_stale()` are reserved for time-based staleness checks (e.g. player stats refreshed daily).

**Revisit if:** The cache layer is extended to track which week numbers are present as explicit metadata (e.g. a `cached_weeks` column in `last_updated.json`), making a full parquet read unnecessary to determine the last cached week.

### matchups.py: current week is included in delta fetch; won't refresh mid-week (2026-03-03)
*(Superseded 2026-05-31 — the `bug-week23-all-zeroes` fix changed this behaviour; `current_week` is now always re-fetched on every call. See the 2026-05-31 entry above.)*

`get_matchups()` fetches up to and including `current_week`. Once that week is cached, the next call finds `last_cached_week == current_week` and fetches nothing new until Yahoo advances `current_week`. Intra-week stat updates are therefore not reflected until the cache is manually cleared. This is acceptable for a daily-use tool; a `force_refresh` flag can be added later if needed.

**Revisit if:** Users report stale intra-week data as a real problem (e.g. mid-week trade or injury decisions), at which point a `force_refresh` query parameter or a time-based TTL on the current week's cache entry should be added.

### leagues.py: patch target is data.leagues._get, not data.client._get (2026-03-03)
`leagues.py` imports `_get` directly via `from data.client import _get`. This binds the name in `leagues.py`'s own namespace, so patching `data.client._get` in tests has no effect. Tests for `leagues.py` must patch `data.leagues._get`. The same rule applies to any future module that imports `_get` (or other helpers) by name from `data.client` — always patch the name in the importing module's namespace.

### leagues.py: get_user_hockey_leagues() filters by game code, not game name (2026-03-03)
The Yahoo games endpoint returns a `code` field (e.g. `"nhl"`, `"mlb"`) that is stable across seasons. `get_user_hockey_leagues()` filters on `game_code == "nhl"`. The human-readable `name` field ("Yahoo Fantasy Hockey") is not used for filtering as it could change.

### team_scores.py: avg_ranks uses method='min' for ties (2026-03-03)
When two teams score identically on a stat in the same week, both receive the lower (better) rank and the next rank is skipped. This matches standard sports ranking convention (two teams tied for 1st → both rank 1, next team ranks 3rd).

**Revisit if:** A league's scoring rules explicitly define ties differently (e.g. split-point ties resolved by a secondary stat), requiring a caller-supplied tie-breaking strategy rather than a fixed ranking method.

### team_scores.py: LOWER_IS_BETTER covers both full name and abbreviation (2026-03-03)
Yahoo stat column names in the matchups DataFrame are the full `stat_name` strings returned by the API (e.g. "Goals Against Average"), not abbreviations. `LOWER_IS_BETTER` includes both the full names and common abbreviations ("GA", "GAA") for defensive breadth. If a league uses non-standard stat names, callers can pass an explicit `lower_is_better` set to `avg_ranks()`.

### Notebook dead ends: do not port (2026-03-03)
The following notebook sections are explicitly marked dead ends or are broken and should not be ported without explicit confirmation:
- "Get matchups for matchup analyser" — incomplete implementation
- "Get rosters and player stats per roster" — has a variable-shadowing bug, extremely slow (1 API call per player)
- "Calculating expected stats" — uses deprecated `statsapi.web.nhl.com` URL and removed `df.append()` API
- "Player Roster & Stats Testing Grounds" — unfinished pagination experiments
