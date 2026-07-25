# Key Decisions Log

Historical implementation decisions, **newest first**. Read this file when you need
context on *why* something was done a particular way.

> **Scope:** This file covers **active** decisions that apply to the current FastAPI stack and the preserved data/analysis/auth layers. Entries that have been superseded by a later decision are moved to [`docs/archive/decisions-superseded.md`](archive/decisions-superseded.md) to keep this log lean — cite the active entry here, never the archived one. For decisions specific to the Streamlit prototype (session state patterns, Streamlit page structure, Streamlit token storage), see [`docs/archive/prototype-decisions.md`](archive/prototype-decisions.md).

---

### Cache: stays league-keyed; write safety comes from atomic rename + in-process locking, not per-user keying (2026-07-23)

Supersedes the "Cache: parquet cache stays on local disk (`/data/cache/`) (2026-04-10)" entry, whose `Revisit if` clause anticipated a per-user keying migration. That migration is now ruled out on the merits; the local-disk decision itself is reaffirmed and carried forward here.

**Question / context:** The M1 launch milestone puts up to ~8 authenticated users, including several managers from the *same* league, on one deployment. `data/cache.py` keys parquet paths on `{league_key}` alone, and the route handlers are sync `def`, so FastAPI runs them in the threadpool and two requests genuinely interleave. Two questions followed: is this a corruption risk, and does the `docs/backlog.md` "per-user cache storage" item belong in M1?

An audit of every cache call site settles the second question first. Only three data types are cached, and all three are league-scoped, not user-scoped: `matchups` (every team's weekly stats — visible to any league member), the `ww_season__{pos}__{stat}` available-player pools (the league-wide waiver pool), and `ww_lastmonth` (player stats). Rosters, projections, and team-specific data are fetched live and never written to the cache. There is no user-private data on the volume, so per-user keying buys no privacy or correctness benefit — and it would multiply both Yahoo API calls and disk usage by the number of managers per league, which is precisely backwards for M2, when strangers arrive and the shared rate-limit budget starts to matter.

The corruption risk, however, is real and is not what per-user keying would fix. Three concrete failure modes exist today:
- `write()` calls `df.to_parquet(path)` directly against the live path. There is no temp-file-and-rename, so a concurrent reader can observe a truncated file and raise `ArrowInvalid`.
- `append()` and `upsert_lastmonth_cache()` are read-modify-write sequences with no mutual exclusion — two interleaved calls lose one side's rows.
- `_write_meta()` re-reads, mutates, and rewrites `last_updated.json` with a plain `open(..., "w")`, which truncates immediately; a torn read raises `JSONDecodeError`.

Two properties make this worse than its low per-request probability suggests. A corrupted parquet or metadata file **persists on the volume** and fails every subsequent read for that league until someone deletes it by hand — it does not self-heal. And it does not require two users: a single manager rapid-firing HTMX filter changes at `/api/waiver/players` produces concurrent writes to the same pool files on their own.

**Options considered:**
- **A — Per-user cache keys (`{user}/{league_key}/`):** Removes cross-user collisions by construction; requires no locking primitive. But it does not fix same-user concurrent HTMX writes, multiplies API calls and storage per league member, and discards the cache's main benefit precisely where it is most valuable (several managers in one league sharing one warm cache).
- **B — Atomic write-and-rename + in-process locking (chosen):** Write to a temp file in the same directory and `os.replace()` onto the target, which is atomic on POSIX within a filesystem; guard the read-modify-write paths with a per-league `threading.Lock`. Fixes all three failure modes for both the multi-user and single-user cases. Roughly 20 lines, entirely inside `data/cache.py`, with no call-site or on-disk-layout changes.
- **C — File locking (`fcntl` / `filelock`):** Correct across processes too, but buys nothing we need under a single worker and adds a dependency plus a lock-file lifecycle to reason about.

**Decision:** Option B. `data/cache.py` keeps its `{league_key}/{data_type}.parquet` layout. Every write becomes temp-file-plus-`os.replace()`, including `last_updated.json`. `append()`, `upsert_lastmonth_cache()`, and `_write_meta()` are serialised by a module-level `dict[str, threading.Lock]` keyed on `league_key`. Per-user cache storage is dropped from the roadmap and the backlog, not deferred.

**Why:** An in-process `threading.Lock` is sufficient *because* of the single-uvicorn-worker decision (2026-04-10) — the two decisions are load-bearing for each other, and that coupling is now explicit. Option B fixes the actual defect, is contained in one stable module, and preserves the shared-cache property that makes several managers in one league cheap rather than expensive.

**Revisit if:** The deployment moves to multiple workers, multiple Fly machines, or any second process touching `/data/cache/` — the `threading.Lock` silently stops providing mutual exclusion at that moment, and the fix becomes `fcntl` locking or an external store. This is the same trigger as the single-worker entry's revisit clause; treat them as one decision. Also revisit if a future feature caches genuinely user-private data (a personal roster, a saved add/drop list), which would reintroduce the per-user keying question on privacy grounds rather than concurrency grounds.

### Cache: league-independent data gets a shared tier at M2; M1 only preserves the affordance (2026-07-23)

Qualifies the 2026-07-23 "Cache: stays league-keyed" entry above. That entry ruled out splitting the cache *finer* (per user); this one addresses the opposite direction — data that is coarser than a league and currently duplicated across leagues.

**Question / context:** Some cached data is not league-scoped at all. Auditing each cached type against whether its source URL carries a `league_key` separates them cleanly:

| Cached data | Source scoped to league? | Shareable |
|---|---|---|
| `ww_lastmonth` | No — `/players;player_keys=…/stats;type=lastmonth` | Yes, and we don't |
| NHL schedule (`schedule.get_remaining_games`) | No — public `api-web.nhle.com` | Yes, and it isn't cached at all |
| `ww_season__{pos}__{stat}` pools | Yes — `/leagues;league_keys={k}/players;status=A` | No |
| `matchups` | Yes | No |

Last-30-day player stats are pure NHL facts — Yahoo player keys are game-scoped (`465.p.1234`) and identical in every league that season, which is why the endpoint needs no league. We nonetheless fetch and store them once per league. The NHL schedule is fully league-independent and not cached at all, so every "Last 30 days" render makes 1–2 live third-party calls in the hot path.

The season pools are *not* a gap despite containing NHL stat values: `status=A` means "available in this league", so pool membership is genuinely league-specific, and the stat values arrive free in the same call via `out=stats`. Sharing them would save disk and zero API calls.

The structural limitation this exposes is that `_parquet_path(league_key, data_type)` has nowhere to put league-independent data — every path helper assumes a league.

**Options considered:**
- **A — Build the shared tier now (M1):** Removes the duplication immediately. But at M1 (~6 leagues, heavily overlapping top-25 pools) it saves on the order of 2–3 Yahoo calls per league per day, which does not justify a ticket, a cache migration, or the schema work below.
- **B — Defer wholesale to M2:** Zero cost now, but the M1 cache-hardening work touches exactly these path helpers, so deferring entirely means refactoring them twice.
- **C — Defer the tier to M2, add the path affordance in M1 (chosen).**

**Decision:** No shared cache tier at M1. During the M1 cache write-hardening work, `_parquet_path` (and its callers) accept a `None`/absent league and resolve to `CACHE_DIR/_shared/{data_type}.parquet`, so a later shared tier is additive. No call sites adopt it yet.

**Why:** The savings are real but small until stranger leagues multiply at M2, and the affordance is roughly five lines in a module already being opened. This buys the option without paying for the feature.

**Known hazard for whoever builds the tier:** `_parse_stats` filters lastmonth columns through the league's enabled stat categories, so today's `ww_lastmonth` frames are league-*shaped* even though the underlying facts are not. A shared tier must store raw `stat_id`-keyed values and project to league stat names at read time; merging the current league-filtered frames directly will produce inconsistent schemas.

**Revisit if:** M2 lands and distinct leagues outnumber roughly 10, or Yahoo rate-limit responses (HTTP 999/429) start appearing — at which point the shared `ww_lastmonth` tier and NHL-schedule caching become the two highest-value fixes. Note that caching `/league/{key}/settings` (tracked in `docs/improvements.md`) is a larger win than either and should be taken first.

### Deployment: M1 shape — single pinned machine, 1 GB volume, fly.toml in repo (2026-07-23)

Extends (does not supersede) the 2026-04-10 "Runtime: single uvicorn worker", "Storage: SQLite for session/nonce storage", and "Deployment: Fly.io with persistent volume" entries. Those decisions hold unchanged at M1 scale; this entry adds the deployment constraints they did not anticipate.

**Question / context:** M1 requires the app deployed at a stable HTTPS URL for ~8 authenticated users across 4–6 leagues. A `Dockerfile` exists; there is no `fly.toml` and no CI. The question was whether the 2026-04-10 runtime commitments survive M1 and how large the shared volume should be.

They survive comfortably. Eight users generate no meaningful concurrency pressure on one uvicorn worker, and SQLite in WAL mode handles the session read/write pattern at this scale without contention.

The constraint the original entries did not capture is that **a Fly volume is bound to a single machine.** If the app ever scales past one machine, each machine gets its own volume: sessions split (a user's cookie resolves on one machine and not the other) and the parquet cache forks into divergent copies. Worse, the `threading.Lock` in the 2026-07-23 cache entry silently stops providing mutual exclusion. The M1 `fly.toml` must therefore pin the app to exactly one machine, and that pin is a correctness requirement, not a cost optimisation.

**Options considered:**
- **A — Pin to one machine (chosen):** `min_machines_running = 1`, no autoscaling, single region `iad`. Preserves every assumption the current architecture rests on. Ceiling is one machine's capacity, which is far above M1 and M2 needs.
- **B — Leave scaling unpinned:** Costs nothing today and would absorb an unexpected traffic spike, but the first scale-out event silently corrupts sessions and cache with no error surfaced to anyone.

**Decision:** Pin to a single machine in `iad`. Provision a **1 GB** volume at `/data`, shared by `app.db` and `cache/`. `fly.toml` is committed to the repo. CI is not an M1 requirement.

**Why on the volume size:** Measured from the cache layout, the footprint is small. Season pools are 25-row parquets (~10 KB each); a league with every position/stat combination warmed lands well under 1 MB. `ww_lastmonth` and `matchups` are the only files that grow, and `matchups` growth is bounded once the parquet-bloat bug is fixed. SQLite with a handful of sessions is under 1 MB. Six leagues sit comfortably inside 100 MB for a full season, so 1 GB is roughly 10× headroom. Fly volumes can be extended later but never shrunk, which argues against over-provisioning now.

**Revisit if:** Sustained traffic approaches one machine's capacity (the trigger to re-open the single-worker/SQLite pair together, per their shared revisit clause), or volume utilisation passes ~50%. Add CI when the test suite stops being run reliably by hand, or at M2 when strangers make a bad deploy publicly visible.

---

### Nav shell: conditional on auth/demo state via shared shell-context; no second auth-derivation path (2026-07-03)

Extends (does not supersede) the 2026-04-19 "Nav shell: minimal league label + logout in base.html; feature links added per ticket" entry, and applies the 2026-05-30 `optional_user` decision to template context.

**Question / context:** Ticket 036. `web/templates/base.html` renders the nav (Overview / Waiver / Projection / Logout) unconditionally on every page. Demo mode now has three feature pages (`/demo/overview`, `/demo/waiver`, `/demo/projection`), and on all of them — plus the logged-out home page — every nav link points at an auth-gated route (or a no-op logout), so a demo/logged-out visitor who clicks any header link is bounced to `/auth/login`. The shell needs to know whether the current render is authenticated, demo, or logged-out-home. There is no template context-injection point today (`web/templates.py` instantiates `Jinja2Templates` with only a `rank_color` filter), and `selected_league_name` is currently threaded per-handler (8 of 9 full-page handlers pass it; the home logged-out branch omits it — an existing instance of exactly the drift this decision guards against). Nine full-page handlers across four route files render templates extending `base.html`.

**Options considered:**
- **A (per-handler boolean flags):** Each full-page handler passes `is_authenticated` / `demo_mode` inline. Reuses the already-resolved `CurrentUser` (single auth source of truth) and adds zero per-fragment cost, but repeats the keys in ~14 context dicts and relies on per-handler discipline — the same discipline that already lapsed for `selected_league_name`.
- **B (Starlette `context_processors=[...]` on `Jinja2Templates`):** One processor injects the flags into every template. *Rejected.* A context processor receives only the `Request`, not the resolved `CurrentUser`, so it must **re-derive auth from the `session_id` cookie + DB** — a second copy of session-lookup/token-refresh logic. This is the exact anti-pattern the **2026-05-30 `optional_user`** decision rejected ("duplicates security-critical logic; any future change to `require_user` must also be applied to the inline copy"). It also runs on **every `TemplateResponse`, including every HTMX fragment render** (waiver `_table`, projection `_matchup`, overview `_table`) — adding a cookie+DB read to fragment swaps that never use nav context, on a single-worker SQLite deployment. Two independent reasons to reject.
- **C (shared `shell_context()` helper, chosen):** A small helper in `web/routes/common.py` takes the resolved user (or `None`) plus a `demo` flag and returns the shell keys (`is_authenticated`, `demo_mode`, and `selected_league_name`); each full-page handler spreads it into its context. `base.html` branches on those keys.

**Decision:** Option C. Shell/nav context is assembled by a shared `shell_context(...)` helper that **reuses the user already resolved by `require_user`/`optional_user`** — never a second cookie/DB lookup — and `base.html` renders the nav conditionally on `is_authenticated` / `demo_mode`. `base.html` must default to the authenticated nav when the flags are absent, so any page not yet migrated keeps rendering as it does today (no regression, and the migration can land in stages). Option A is an acceptable lighter variant of the same principle (reuse the resolved user, no context processor) if the owner prefers no helper; Option B is rejected outright.

**Why:** Reusing the resolved user keeps one source of truth for "is this request authenticated," consistent with the 2026-05-30 `optional_user` decision, and avoids taxing every fragment render. Centralising the key *shape* in one helper fixes the existing `selected_league_name` drift and gives future feature pages one thing to copy — the same "make drift structurally impossible" philosophy as the 2026-07-03 shared compute-helper entry below, applied to context assembly. Feature-link ordering (Overview → Waiver → Projection) from the 2026-04-19 entry is preserved.

**Revisit if:** The app grows a genuinely public (non-demo, non-home) page family that needs nav state but has no user dependency in scope, making a request-only derivation unavoidable; or the number of shell-context keys grows enough that a small dataclass reads more clearly than a dict.

---

### Web routes: demo and live handlers share a single compute/render helper (2026-07-03)

**Question / context:** Ticket 031 factored the Week Projection route's compute-tally-breakdown-render tail into `_render_matchup(...)` in `web/routes/projection.py`, fed by both the authenticated handler (`_matchup_impl`) and the demo handler (`demo_projection_matchup`). The two paths differ only in *data assembly* — live Yahoo API calls vs. reading `data/demo.py`'s snapshot — while the projection math, category tally, per-player breakdown, and template render are shared, so live and demo cannot drift. The older demo routes (overview, waiver) assemble their live and demo contexts independently, with no shared compute helper, so they *could* drift. Audit 032 surfaced two competing conventions with nothing in this log saying which future feature pages should follow.

**Options considered:**
- **A (independent assembly — the overview/waiver precedent):** Each demo handler builds its own context end-to-end. Simple per-handler with no shared signature to maintain, but the live and demo renderings of the same page can silently diverge (different tally logic, different rounding, a template var set on one path but not the other). Demo mode is user-facing, so drift ships bugs to unauthenticated visitors.
- **B (shared compute/render helper — projection's precedent, chosen):** Live and demo handlers each do only their own data assembly, then hand a common set of resolved inputs to one shared helper that does all compute + render. Guarantees the two paths are identical below the assembly seam. Costs a slightly wider helper signature (resolved inputs passed as keyword args).

**Decision:** Option B — for a feature page with both an authenticated and a demo route, the two handlers should share a single compute/render helper whose only difference from either caller is data assembly (live fetch vs. snapshot read). `projection._render_matchup` is the reference implementation. The older overview/waiver demo routes are pre-pattern and are fine to leave as-is; converge them only if they are being substantially reworked for another reason.

**Why:** Demo mode is a user-facing correctness surface, not a throwaway. A shared compute path makes live/demo drift structurally impossible instead of relying on a reviewer to catch it, at the cost of one keyword-argument seam — a good trade for a single-engineer project. It also shrinks the off-season testing gap (see the past-week-testing spike entry below): because demo already runs the *real* compute+render tail, only the fetch/assembly head is authenticated-only.

**Revisit if:** A feature page's live and demo paths need genuinely different compute (not just different data assembly) — e.g. demo shows a simplified or annotated variant — at which point forcing a shared helper adds branching that is worse than two honest handlers; or the shared helper's signature grows wide enough that a small resolved-inputs dataclass reads more clearly than keyword passing.

---

### Dev/test: no runtime past-week override; use captured fixtures + demo mode instead (2026-07-03)

Resolves the ticket 033 spike ("develop & test week-keyed pages against a specific past week").

**Question / context:** We develop during the NHL off-season, when Yahoo returns empty/stale data for week-keyed features (matchups, weekly scoreboards, `type=lastmonth` rates, remaining-games schedules). Ticket 029 (Week Projection shell) could not be exercised against real matchup/projection data for this reason. The spike asked whether we can point the authenticated live-fetch paths at a specific past week — via a dev-mode `current_week` override (Option A), a seeded parquet cache (Option B), or reusing the demo snapshot in authenticated routes (Option C) — to develop and QA them with real data.

**The blocking technical fact:** Two of the projection's core inputs are inherently "as of now" and cannot be sourced for a past week from the live API: (1) `type=lastmonth` returns the last 30 days as of today only — there is no historical-window parameter (see the 2026-03-23 entry) and off-season it is empty; (2) `get_remaining_games` counts NHL games from today forward, so for a past week it returns ~0 and the projection collapses to "0 games left." A `current_week` override alone (Option A) therefore fetches only the inputs that were *never* the problem (scoreboard pairings and `teams/stats;week=N`, both already `week`-parameterized) while leaving the two that made 029 untestable unsolved. Sourcing those too means seeding lastmonth rates and remaining games from a snapshot — at which point "test against live past-week data" has collapsed into "richer demo fixtures."

**Options considered:**
- **A (runtime `week`/dev-mode override threaded through the fetches):** Rejected. Does not source the two inputs that matter, and introduces a permanent production-safety liability — a code path that reads "which week is now" from somewhere other than Yahoo, plus a config knob that must be gated out of production forever and is easy to leave on. A new config knob + a `data/client.py` convention change (two architectural surfaces) bought for coverage it cannot actually deliver.
- **B-runtime (seed `CACHE_DIR` with a captured past-week snapshot):** Rejected as a *runtime* mechanism. Fights the 2026-05-31 always-re-fetch guard for `current_week` (seeded current-week data is clobbered by the live empty fetch) and puts fake data one directory away from genuine authenticated sessions.
- **C (source authenticated routes from `data/demo.py`):** Rejected outright. Blurs the demo/authenticated boundary the team deliberately keeps clean; a data-source-swapping dev flag in the authenticated path is exactly the kind of thing left on by accident.
- **B-tests (capture a past-week raw response set as *test fixtures*, chosen):** Capture real past-week Yahoo responses once and store them in `tests/fixtures/`, then unit/integration-test the parse/cache/fetch-orchestration functions against them — the pattern CLAUDE.md's testing strategy already prescribes (fixtures in, no live calls). Combined with demo mode for the visual/compute check.

**Decision:** Do **not** build a runtime past-week override or a dev data-source swap. The two real needs are met separately: (1) *visual + compute* verification during off-season is already covered by demo mode — and because live and demo now share `_render_matchup` (2026-07-03 entry above), the demo page exercises the exact authenticated compute+render tail; (2) *coverage of the authenticated fetch/parse/cache paths* is met by capturing a past-week raw response set into `tests/fixtures/` and testing those functions directly, never by a runtime seam. Options A and C are rejected; no dev-only "current week is now X" knob enters the codebase.

**Why:** The spike's own crux question answers itself: once you seed the un-sourceable inputs, the live-override exercise *is* just demo fixtures with more risk. The fixture-in-tests route gives real, deterministic coverage of the parse/cache logic that demo mode bypasses, off-season or not, with zero production-safety surface — no knob to gate, no fake data near a live session, no boundary crossing. It is strictly better than a runtime override on every axis that matters here.

**Revisit if:** Yahoo adds an arbitrary historical-window stats parameter (removing the `type=lastmonth` limitation) *and* `get_remaining_games` gains a bounded past-week form — at which point a live past-week fetch could source all inputs and a narrowly-gated dev override might become worth its safety cost; or a future week-keyed feature depends only on inputs that *are* week-parameterizable today (scoreboard, `teams/stats;week=N`), for which a read-only past-week smoke test carries far less risk and could be reconsidered on its own.

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

**Revisit if:** Yahoo deprecates or rate-limits the bulk `teams/stats` collection endpoint, or a feature needs a single team's stats often enough that the retained per-team `get_team_week_stats()` becomes the primary path again.

### client.py: _coerce() handles None values, not just '-' (2026-03-23)
The Yahoo API can return `None` for stat values (not just the string `'-'`). `_coerce()` and the `games_played` handler now treat `None` identically to `'-'` — coerced to 0. This fixes the `float() argument must be a string or a real number, not 'NoneType'` error.

**Revisit if:** Yahoo's response format changes so stat values arrive already typed (JSON numbers/nulls) rather than strings, making the string-vs-`None` coercion in `_coerce()` unnecessary.

### players.py: type=lastmonth is the correct param for last-30-day player stats (2026-03-23)
Confirmed via validate_api.py against a live league. `date=lastmonth` and `week=lastmonth` both return season totals. `out=stats` on the league players collection endpoint also always returns season totals regardless of `sort_type`. Only `/player/{key}/stats;type=lastmonth` (and the batch form `/players;player_keys={keys}/stats;type=lastmonth`) returns the last 30 days.

**Revisit if:** Yahoo adds a parameter for an arbitrary historical N-day window, or changes what `type=lastmonth` returns — this "as of now only" limitation is what blocks past-week testing (see the 2026-07-03 past-week-testing spike entry).

### players.py: two API calls per page of 25 players (2026-03-23)
`get_available_players()` uses a two-call-per-page pattern:
1. `/leagues;league_keys={key}/players;status=A;sort=OR;sort_type=season;out=stats;start={n};count=25` — player list with season stats inline and player keys
2. `/players;player_keys={keys}/stats;type=lastmonth` — batch lastmonth stats for those same keys

This gives both stat periods in 2 API calls per page (8 total for 100 players) instead of 1+N. The batch lastmonth call returns `{player_key: stats}` only — no metadata — so metadata is taken from the season response and re-attached by the caller.

**Revisit if:** Yahoo exposes lastmonth stats inline on the players collection endpoint (removing the second batch call), or changes the 25-players-per-page limit.

### players.py: imports private helpers from data/client.py (2026-03-23)
`data/players.py` imports `_get`, `_as_list`, `_coerce`, and `BASE_URL` directly from `data/client.py`. These are intentionally shared across the data layer. The same patch-target rule applies: tests for `players.py` must patch `data.players._get`, not `data.client._get`.

**Revisit if:** The shared helpers (`_get`, `_as_list`, `_coerce`) move to a dedicated shared module, or `data.client` stops being the canonical home for the Yahoo transport layer — either would change the correct import source and patch target.

---

### Auth: yahoo_oauth not used for the OAuth flow (2026-03-03)
`yahoo_oauth`'s `OAuth2` class assumes interactive terminal input — it opens a browser and waits for the user to paste an authorisation code. The app uses a redirect-based callback: Yahoo sends the user back to the redirect URI with `?code=...`. These are incompatible. The auth flow is implemented directly with `requests` instead. The core pattern (check validity → refresh if needed → return authenticated session) is preserved in `auth/oauth.py`.

**Revisit if:** The `yahoo_oauth` library is updated to support redirect-based OAuth 2.0 flows natively, reducing the maintenance burden of the hand-rolled `auth/oauth.py` implementation.

### client.py: unknown and display-only stats silently skipped (2026-03-03)
The notebook emitted `"Unknown Stat ID: 22"` columns for unrecognised stat IDs and relied on the caller to drop them (`df.drop(columns=['Unknown Stat ID: 22'])`). `client.get_team_week_stats()` instead silently ignores any stat not in the enabled categories lookup. This keeps the DataFrame clean without requiring callers to know which IDs to drop.

**Revisit if:** A feature needs to surface unrecognised or display-only stats to the user (e.g. a debug view of raw Yahoo categories), at which point silent skipping would hide data the caller wants.

### client.py: _as_list() handles the single-item xmltodict gotcha centrally (2026-03-03)
Rather than scattering `if int(@count) == 1` checks (as the notebook did for teams), a single `_as_list(value)` helper normalises any dict-or-list value to always be a list. Used on: the stat categories list, `stat_position_type` (which can be a list when a stat applies to multiple position types), the teams list, and the per-week stat list.

**Revisit if:** The project switches from `xmltodict` to a structured XML parser or a JSON-native Yahoo API response format, in which case the single-item ambiguity disappears and `_as_list` can be removed.

### matchups.py: delta fetch uses max(week) from cache data, not last_updated timestamp (2026-03-03)
`cache.last_updated()` returns when something was written (a datetime), not which weeks are present. For the delta fetch pattern, what matters is which week numbers exist in the data. `_last_cached_week()` reads `df['week'].max()` from the cached parquet file. `cache.last_updated()` / `cache.is_stale()` are reserved for time-based staleness checks (e.g. player stats refreshed daily).

**Revisit if:** The cache layer is extended to track which week numbers are present as explicit metadata (e.g. a `cached_weeks` column in `last_updated.json`), making a full parquet read unnecessary to determine the last cached week.

### leagues.py: patch target is data.leagues._get, not data.client._get (2026-03-03)
`leagues.py` imports `_get` directly via `from data.client import _get`. This binds the name in `leagues.py`'s own namespace, so patching `data.client._get` in tests has no effect. Tests for `leagues.py` must patch `data.leagues._get`. The same rule applies to any future module that imports `_get` (or other helpers) by name from `data.client` — always patch the name in the importing module's namespace.

**Revisit if:** The data layer stops importing helpers by name from `data.client` (e.g. moves to a shared module imported as a namespace, `import data.transport as t; t._get(...)`), removing the name-binding gotcha that makes the patch target non-obvious.

### leagues.py: get_user_hockey_leagues() filters by game code, not game name (2026-03-03)
The Yahoo games endpoint returns a `code` field (e.g. `"nhl"`, `"mlb"`) that is stable across seasons. `get_user_hockey_leagues()` filters on `game_code == "nhl"`. The human-readable `name` field ("Yahoo Fantasy Hockey") is not used for filtering as it could change.

**Revisit if:** Yahoo changes or retires the stable game `code` field, or the app expands beyond NHL to other sports where a different (or parameterized) game filter is needed.

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
