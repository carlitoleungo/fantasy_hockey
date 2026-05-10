# Scoping Brief 017 — Waiver Wire Migration

**From:** PM
**To:** Tech Lead
**Re:** In-session player pool strategy for waiver wire migration

---

## Background

Tickets 001–016 are done. The overview page (nav shell, weekly leaderboard, head-to-head) is fully migrated and QA-approved. The next feature is the waiver wire migration — the main user-facing feature. Before scoping tickets, we need a Tech Lead call on one architectural question.

## The question

The Streamlit prototype manages two cache layers for the player pool:

1. **In-session (memory):** `st.session_state["ww_season_pool"]` accumulates merged DataFrames as the user toggles stat categories. Prevents redundant disk reads within a session.
2. **Disk (24h TTL):** `cache.write_player_pool(league_key, position, stat)` persists each per-(position, stat) pool to parquet. Prevents Yahoo API calls on repeat visits.

The disk layer already works in `data/cache.py` (`read_player_pool`, `write_player_pool`, `is_player_pool_stale`) and requires no changes. The question is only about replacing the in-session layer.

**Key HTMX difference from Streamlit:** Each filter change sends a `POST /api/waiver/players` with *all currently-selected stats* (not incremental additions). There's no concept of "we just toggled one more stat" — every request is a full re-render of the current filter state. The handler reads whatever pools it needs and merges on the fly.

---

## Options

**Option A — Stateless + disk cache only**

Each request to `POST /api/waiver/players` receives the full filter state (`position`, `stats[]`, `period`). The handler loops over selected stats, checks the disk cache for each `(league_key, position, stat)` combination, fetches from Yahoo on a miss, writes to disk, then merges all pools and ranks.

- Implementation cost: **S** — matches existing overview route pattern; no new surface
- Future cost: **Low** — disk cache already handles per-(position, stat) persistence; no in-process state to reason about; survives restarts; no SQLite changes needed
- Performance: first cold request per (position, stat) pair is slow (~2–3s per Yahoo API call). Every subsequent request — including later in the same session — is a fast parquet read. The 24h TTL means the slow path only happens once per day per combination.
- Good if: we trust the disk cache as the accumulation layer (it already does this job)

**Option B — In-process accumulation dict (global `dict[session_id → DataFrame]`)**

A module-level dict in `web/routes/waiver.py` accumulates merged DataFrames keyed by session_id. Avoids re-reading parquet on each request within a session.

- Implementation cost: **M** — new singleton, session lifecycle management, memory growth under concurrent users
- Future cost: **High** — process memory grows with user count; data lost on restart (uvicorn restarts happen on deploys); a mutable global contradicts the stateless HTMX pattern every other route follows; harder to test
- Good if: parquet read latency were a bottleneck — but it isn't; `read_player_pool` is a sub-millisecond local disk read once populated

**Option C — Serialize accumulated DataFrame to SQLite `user_sessions`**

Parquet bytes stored as a BLOB in the session row.

- Implementation cost: **L** — schema migration, serialization/deserialization, blob size management
- Future cost: **High** — parquet BLOBs in SQLite are unusual; the existing disk cache already handles this more cleanly; adds coupling between the session layer and the data layer
- Good if: you needed true cross-device/cross-restart continuity — you don't; the disk cache handles that already

---

## PM's initial read

Option A looks right. The disk cache is already the accumulation layer for this data. The HTMX "send full state with every request" pattern means the handler just reads whatever pools it needs from disk and merges — no cross-request memory required. This keeps `web/routes/waiver.py` consistent with how `overview.py` works.

One flag for ticketing: the `_merge_pool` logic from `pages/03_waiver_wire.py` (lines 131–143) should live in `web/routes/waiver.py` or a small helper, not in `data/` or `analysis/`. It's a presentation-layer merge, not a data-layer concern.

---

## Questions for the Tech Lead

1. Does Option A hold up against the existing architecture and prior decisions in `docs/decisions.md`?
2. Any implications for likely near-term work (demo mode port, week projection, per-user cache migration) that would change the recommendation?
3. Is there a fourth option we haven't considered?
4. If Option A, any concerns about the `_merge_pool` placement?

---

## Files to read first

- `pages/03_waiver_wire.py` — full Streamlit implementation; pool accumulation logic at lines 130–348
- `data/cache.py` — `read_player_pool`, `write_player_pool`, `is_player_pool_stale` at lines 140–175
- `web/routes/overview.py` — the stateless route pattern to match
- `docs/decisions.md` — "Feature pages: HTMX fragment pattern" and "League context: session-state propagation retained"
- `docs/roadmap.md` — for near-term pressure-test

---

## Tech Lead response (2026-04-26)

**Decision: Option A — Stateless + disk cache only.**

**Q1 — Consistency with prior decisions**

Option A is the logical completion of the HTMX fragment pattern decision (2026-04-19), which explicitly noted that waiver wire's per-(position, stat) lazy-loading "requires fragment fetches anyway" and rejected full preloading because the player pool is too large. The stateless handler convention in `web/routes/overview.py` confirms the idiom: each request fetches from the data layer, computes, returns — no cross-request in-memory state. Option B introduces a mutable module-level global that directly contradicts that convention. Option C adds a serialization layer the disk cache already handles more cleanly. Neither B nor C has a compensating benefit.

**Q2 — Near-term implications**

- **Demo mode port (next after waiver wire):** Option A handles this cleanly. `data/demo.py` provides drop-in replacements for all data functions; the route handler swaps data sources at the top rather than special-casing session state throughout. The Streamlit prototype's demo path (lines 271–278) was messier precisely because it had to short-circuit pool accumulation logic scattered across session state. Option A collapses that to a single conditional.
- **Per-user cache migration:** The disk cache is currently keyed by `(league_key, position, stat)` via `_pool_key()`. Adding per-user isolation becomes a one-line change in `cache.py`. Option B would require also migrating the session dict; Option C would require a schema migration on top of the cache-key change.
- **Scoping gap to address before ticketing:** The brief doesn't spec how the `period` parameter branches between cache paths. Season and last-30-day data use different cache functions (`read_player_pool`/`write_player_pool` vs. `read_lastmonth_cache`/`upsert_lastmonth_cache`) and different cache keys (per-stat slices vs. a single cumulative cache). The route handler needs to branch on `period` and the ticket acceptance criteria should make this explicit — it's not hard, but it's the one non-trivial detail that could cause rework mid-ticket.

**Q3 — Fourth option**

Not warranted. Option A has no non-obvious gotcha. The tempting alternative — caching the merged result for a given (position, stat_set) — is premature optimisation: parquet reads are sub-millisecond once warm and the `pd.concat` merge over ~100-row DataFrames is negligible.

**Q4 — `_merge_pool` placement**

PM's instinct is correct: `_merge_pool` belongs in `web/routes/waiver.py` or a small co-located helper. It has no business in `data/` (no I/O) or `analysis/` (no statistical computation). One detail to carry forward: the same merge function applies to both the season pool and the last-month pool — use one shared function, not two copies.
