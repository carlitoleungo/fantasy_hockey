# Scoping Brief 046 — Cache `/league/{key}/settings` (league settings + stat categories)

**From:** PM
**To:** Tech Lead
**Re:** Storage form and TTL for season-invariant league metadata

## Status
blocked

(Blocked on a Tech Lead consult. This is deliberately a scoping brief, not an
implementation ticket: the fix lands on two architectural surfaces and **no active
`docs/DECISIONS.md` entry covers the two choices it requires**. See "The gap" below.
It is also blocked by the audit gate — `scripts/audit_due.py` reads 5.5 / 5, `AUDIT
DUE`, and an overdue audit blocks architectural-surface scoping.)

## Type
bug

## Milestone
m2

(`docs/ROADMAP.md` § Watching, "Yahoo rate-limit hardening" names this item explicitly
as M2, not M1: "At M1's ~6 leagues the budget is generous, so these are deliberately out
of M1 scope. The settings-cache item also touches `data/client.py` (an architectural
surface needing its own Tech Lead consult) — do not fold it into the M1 cache work.")

## Touches
- (none yet — no implementation is authorised by this brief)

Expected `Touches` for the follow-on ticket, once the consult settles the questions
below: `data/client.py`, `data/cache.py`, plus tests. `data/matchups.py` and
`web/routes/waiver.py` should need **no** change if the cache sits behind the existing
client function signatures.

## Why

Every authenticated page render costs at least 2 Yahoo API calls that return
season-invariant data. `get_league_settings()` (`data/client.py:65`) and
`get_stat_categories()` (`data/client.py:94`) GET the same
`/league/{league_key}/settings` URL and neither consults the cache. On the waiver page
these are the *only* remaining calls once the parquet pools are warm, so they set the
floor on the steady-state API budget — the exact budget M2 ("strangers can sign in
without exhausting the shared Yahoo rate limit") is gated on. `docs/DECISIONS.md`
2026-07-23 "Cache: league-independent data gets a shared tier at M2" says so directly:
"caching `/league/{key}/settings` (tracked in `docs/improvements.md`) is a larger win
than either and should be taken first."

This brief resolves the `docs/improvements.md` entry **"League settings and stat
categories re-fetched from Yahoo on every request"** (Type: bug, discovered 2026-07-23).
The entry stays open until the follow-on implementation ticket ships; the follow-on
ticket must name it and move it to `docs/archive/improvements-closed.md` on handoff.

## The gap — what is not decided

Two active entries bear on this work, and neither settles it.

1. **`docs/DECISIONS.md` 2026-07-23 "Cache: stays league-keyed; write safety comes from
   atomic rename + in-process locking, not per-user keying"** settles *keying* (league
   key) and *write safety* (temp file + `os.replace`, per-league `threading.Lock`). It
   says nothing about storage form for non-tabular data or about TTL policy.
2. **`docs/DECISIONS.md` 2026-07-23 "Cache: league-independent data gets a shared tier at
   M2; M1 only preserves the affordance"** flags this item as the higher-value win and
   adds the `CACHE_DIR/_shared/` path affordance, but explicitly defers the settings
   cache itself and prescribes nothing about it.

The two genuinely undecided choices:

**Q1 — Storage form.** `data/cache.py` is a parquet/DataFrame store. The settings
response is a dict plus a list of dicts, not a frame. There is no active decision on how
non-tabular league metadata is stored on disk, and the on-disk layout under
`CACHE_DIR` is an architectural surface. Candidates: a JSON-blob tier reusing the
existing `_atomic_write` / `_write_json` helpers (`data/cache.py:85`, `:107`); a
coerced one-row parquet; or an in-process TTL memo with no disk at all.

**Q2 — Whether `current_week` may be served from cache, and at what TTL.**
`docs/DECISIONS.md` **2026-05-31 "matchups.py: current_week always re-fetched to reflect
intra-week stats"** is active and decides the opposite of what the improvements entry
proposes: caching `current_week` was tried, broke intra-week freshness, and Option A
("cache once") was rejected as "unacceptable for a daily-use tool". Its Revisit-if
clause names a ≤1 h TTL as the remedy *if Yahoo rate-limit warnings appear* — a revisit
trigger, not a standing decision. A ticket that caches the whole settings payload
therefore strains an active decision and needs the Tech Lead either to supersede it or
to bless a split (cache the stable half, keep `current_week` live).

There is also a **layer-rule question**: `data/client.py`'s module docstring states "no
Streamlit, no pandas, **no cache logic here**". Putting a cache check inside
`get_league_settings()` / `get_stat_categories()` is the seam that fixes all callers at
once, but it contradicts that stated rule. The alternative is a caching wrapper in a
separate module with every call site updated, which is a much larger diff.

## Options

**Option A — Split the payload: cache stat categories, keep `current_week` live**

One fetch populates a per-league JSON cache holding only the stable half (stat
categories, `start_week`, `end_week`). `get_league_settings()` continues to hit Yahoo
because `current_week` is in its return shape.

- Implementation cost: **S**
- Future cost: **Low** — preserves 2026-05-31 unmodified; no decision superseded.
- Saving: 1 of 2 calls per render on the waiver page; on `data/players.py:50` and `:109`
  it removes the repeat `get_stat_categories()` calls entirely, which the improvements
  entry's call-site list misses.
- Good if: intra-week freshness is non-negotiable and a 50% cut is worth shipping now.

**Option B — Cache the whole settings payload behind a short TTL (1–6 h)**

One cached fetch serves both functions, as `docs/improvements.md` proposes. Requires
superseding or qualifying 2026-05-31 with a dated entry that sets the TTL and states
the accepted staleness at a week boundary.

- Implementation cost: **M**
- Future cost: **Medium** — a TTL is now load-bearing for `get_matchups()` correctness;
  a wrong TTL reintroduces the `bug-week23-all-zeroes` class of failure. The TTL must
  stay well under a week.
- Saving: both calls per render.
- Good if: the Tech Lead judges a ≤1 h TTL indistinguishable from live for the
  same-day-waiver-decision use case.

**Option C — Request-scoped memo only (no disk)**

Memoise the parsed response for the life of one request (or one session), so the two
functions and `data/players.py`'s repeat calls collapse to one. Nothing is written to
disk; no TTL exists; no decision is touched.

- Implementation cost: **S**
- Future cost: **Low**, but it is a partial fix — the floor drops from 2 calls per render
  to 1, never to 0, and a mutable module-level memo cuts against the stateless route
  pattern (2026-07-03 "Web routes: demo and live handlers share a single compute/render
  helper").
- Good if: the Tech Lead wants zero staleness risk before M2 usage data exists.

Note that `data/client.py:128` already has `get_settings_and_categories()`, which
returns both halves from a single call. Whichever option is chosen, that function is the
natural single cached fetch the improvements entry asks for ("Both functions should share
one cached fetch rather than each caching separately"); the other two should become thin
wrappers over it rather than three independent `_get()` calls.

## PM's initial read

Option A looks like the right first move, with B revisited once M2 usage produces real
rate-limit evidence. A ships a real saving without superseding an active decision that
was itself written to fix a shipped bug, and it removes the repeat
`get_stat_categories()` calls in `data/players.py` that nothing has costed yet. But the
call is the Tech Lead's — I am not inventing a TTL.

## Questions for the Tech Lead

1. Q1 — storage form for non-tabular league metadata under `CACHE_DIR`. JSON tier,
   one-row parquet, or memory only?
2. Q2 — may `current_week` be served from cache at all? If yes, supersede 2026-05-31
   with a dated entry naming the TTL.
3. Does the cache check belong inside `data/client.py` (contradicting its "no cache
   logic here" docstring), or in a wrapper module? If inside, the docstring and
   `docs/ARCHITECTURE.md`'s layer rules should be amended in the same pass.
4. Confirm the shared-vs-league-keyed question is a non-issue here: the settings URL
   carries a `league_key`, so this is league-scoped data and the `CACHE_DIR/_shared/`
   affordance does not apply.

## Out of scope

- The related `docs/improvements.md` item **"Cross-league duplication: `ww_lastmonth` and
  NHL schedule are cached per league or not at all"**. It stays a separate item: it is
  already covered by its own active decision (2026-07-23 "Cache: league-independent data
  gets a shared tier at M2"), it touches different modules (`data/players.py`,
  `data/schedule.py`), and it carries its own hazard (raw `stat_id`-keyed storage with
  read-time projection). Folding it in would breach the 2–3 file rule and mix two
  decisions in one diff.
- Any change to the parquet pool caches or their 24 h TTLs.
- Demo mode — `data/demo.py:72` serves stat categories from a snapshot and makes no API
  call, so it is unaffected.

## Notes for the Engineer

No implementation is authorised yet. For whoever writes the follow-on ticket:

- **Active DECISIONS.md entries this work must conform to or supersede:**
  - 2026-07-23 "Cache: stays league-keyed; write safety comes from atomic rename + in-process locking, not per-user keying" — any new write path uses `_atomic_write` and the per-league lock.
  - 2026-07-23 "Cache: league-independent data gets a shared tier at M2; M1 only preserves the affordance" — names this item as the higher-value win, taken first.
  - 2026-05-31 "matchups.py: current_week always re-fetched to reflect intra-week stats" — the entry Option B would have to supersede.
  - 2026-03-03 "client.py: `_as_list()` handles the single-item xmltodict gotcha centrally" and 2026-03-03 "client.py: unknown and display-only stats silently skipped" — any re-parse of the settings payload keeps both behaviours.
- **Call sites are wider than `docs/improvements.md` records.** Beyond `data/matchups.py:37`/`:84` and `web/routes/waiver.py:171`, `get_stat_categories()` is called at `web/routes/waiver.py:74`, `data/players.py:50` and `data/players.py:109`. Caching behind the client functions fixes all of them with no call-site churn.
- **Test patch targets (`docs/LEARNINGS.md`).** `data/players.py:26` imports `get_stat_categories` by name, so tests patch `data.players.get_stat_categories`; `web/routes/waiver.py:12` likewise patches `web.routes.waiver.get_stat_categories`; `tests/test_matchups.py` patches `client.get_league_settings`. Roughly 60 existing test patches assume the current signatures — keeping them stable is a design constraint, not a nicety.
- **Open `docs/improvements.md` items on the expected `Touches` files:**
  - `data/client.py`, `data/cache.py` — "League settings and stat categories re-fetched from Yahoo on every request" (Type: bug). **This is the item the follow-on ticket is scoped from**; it must be closed on handoff.
  - `data/cache.py` — "Cross-league duplication: `ww_lastmonth` and NHL schedule are cached per league or not at all" (Type: quality, lists `data/cache.py` path helpers). **Out of scope** — deferred to M2 by its own decision; the Engineer mentions it, does not sweep it, and the follow-on ticket should say so explicitly so the input-#6 sweep does not pull it in.
  - No other open items name `data/client.py` or `data/cache.py`.

## Verification

Not applicable — no code changes. This brief is done when the Tech Lead has answered the
four questions, logged a dated `docs/DECISIONS.md` entry for Q1 and Q2, and the PM has
turned the answers into an implementation ticket.

## Dependencies

- Tech Lead consult (Q1–Q4 above) must complete first.
- The due audit checkpoint (`scripts/audit_due.py` = `AUDIT DUE`, 5.5 / 5) must run
  before any architectural-surface ticket derived from this brief is orchestrated.
