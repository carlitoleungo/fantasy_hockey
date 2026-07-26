# Roadmap — Fantasy Hockey Waiver Wire

Likely near-term work, in rough priority order. This is a **pressure-test tool, not a
commitment** — the PM reads it during scoping to ask "does this ticket's approach still
make sense if these land?"

Keep it to ~3–7 items. If it grows past that, it's stopped being a pressure-test tool
and become a wishlist — prune.

---

## Launch milestones

The owner has defined three launch milestones. These are **approved and final** — they
are the stable definitions the ticket template's `## Milestone` field and the backlog
template's `**Milestone:**` field point at. Do not re-litigate the intent here; scope
against it.

### M1 — my league + close friends

Deployed at a stable HTTPS URL; up to ~8 authenticated users across 4–6 leagues (a mix of
several managers in the *same* league plus friends in their own leagues), each signing in
with their own Yahoo account and using Overview, Waiver, and Projection without interfering
with each other.

### M2 — strangers can sign in

A person you've never met can find the app, evaluate it via demo mode without signing in,
connect their own Yahoo account, and use it, without their usage degrading anyone else's or
exhausting the shared Yahoo rate limit.

### M3 — charging

Paid access to the entire authenticated app; demo mode stays free. All-or-nothing gate (no
free tier yet); the exact split is TBD and out of scope for now.

> **M2 and M3 are deliberately not scoped into tickets.** M2's real content depends on what
> live M1 usage teaches about the Yahoo rate limit (which is why the rate-limit fixes in
> `docs/improvements.md` are tagged M2, not M1). M3 needs a Yahoo commercial-terms check
> before any billing work is scoped. Milestone *tags* on backlog items are fine; M2/M3
> *tickets* are not, until those gates clear.

### M1 launch steps that are owner actions, not tickets

These close M1 alongside the M1 tickets but cannot be done in an Engineer session — record
them here so they are not lost:

1. **Register the production Yahoo redirect URI** in the Yahoo developer console. Yahoo
   requires HTTPS redirect URIs registered out-of-band; the app cannot self-register. Add
   `https://<prod-host>/auth/callback` in the console and set `YAHOO_REDIRECT_URI` to match
   in the Fly secrets. **Owner action, not a ticket.**
2. **Provision the Fly volume and deploy.** After ticket 039 lands `fly.toml`, run
   `fly volumes create data --size 1 --region iad`, set the Yahoo secrets via
   `fly secrets set`, then `fly deploy`. The `fly.toml` is the ticket; running the deploy is
   an owner action (needs a Fly account and auth).
3. **Decommission Streamlit Community Cloud** once the Fly app is live and validated —
   disconnect the app in the SC dashboard. See the backlog entry "Streamlit Community Cloud
   decommissioning" (tagged m1). Mostly a dashboard action; a redirect is only worth setting
   up if external links to the SC URL exist. **Owner action, not a ticket.**

---

## Next up

1. **AUDIT** — scoped into ticket **041** (2026-07-26). `scripts/audit_due.py` reports
   **AUDIT DUE at 5.5 / 5** (032, 034, 035, 036a, 036b, 037 completed since the last audit at
   031). Two themes: (A) cache + nav-shell conventions, the two surfaces that saw significant
   work; (B) **test-suite health**, added at the owner's request — the suite is 433 tests /
   8,520 lines against 3,496 lines of source, and the standard checklist has no check for
   redundancy or staleness. Theme B asks three questions: route-test bulk (`web/routes/` runs
   3.8:1), whether `auth/oauth.py` coverage is real or only apparent, and whether the four
   unratified `*_qa.py` files hold real edge cases. **This blocks architectural-surface
   scoping only** — ticket 039 (`fly.toml`) is architectural and waits on it; tickets 038 (bug
   fix) and 040 (test-only) may proceed in parallel. Run by the Reviewer directly, not the
   Orchestrator (audits are refused in orchestrator pre-flight).
2. **M1 matchups parquet-bloat fix** — scoped into ticket **038** (2026-07-25, depends on
   037). Fixes the `data/matchups.py` re-fetch loop that appends `prev_week`/`current_week`
   rows to the parquet on every page load for the rest of the day. Resolves the
   `docs/improvements.md` bug "matchups.py re-fetch loop causes parquet bloat". Kept separate
   from 037 (different file, different concern — see the report / ticket 038 Notes for the
   fold-vs-separate call).
3. **M1 deployment config** — scoped into ticket **039** (2026-07-25). Commit `fly.toml`
   (single pinned machine in `iad`, `min_machines_running = 1`, no autoscaling, 1 GB volume
   at `/data` shared by `app.db` and `cache/`) and a `.dockerignore` (the current
   `COPY . .` Dockerfile would otherwise bake `.env` secrets, `app.db` OAuth tokens, and
   `.cache/` into the production image). Covered by the Tech Lead consult 2026-07-23
   (DECISIONS "Deployment: M1 shape — single pinned machine, 1 GB volume, fly.toml in repo").
4. **Nav shell test hardening** — scoped into ticket **040** (2026-07-25). Ticket 036a
   (nav shell foundation, m1) and **036b** (demo nav adoption, m2) both **SHIPPED** — the
   demo pages now render a coherent demo nav and the logged-out home nav is fixed. 040
   closes the regression-guard gap the 036b review found: nav assertions cover 7 of the 12
   migrated `shell_context()` branches, and the 5 uncovered ones (all in `overview.py`
   empty-state and head-to-head branches) fail silently if a future edit drops the spread.
   Test-only, no milestone. Resolves two `docs/improvements.md` items. The "Try the demo"
   home entry point remains a separate follow-up (improvements item, m2-leaning).
5. **Demo mode snapshot tooling** — `data/demo.py` snapshot generation script and fixture
   data refresh. The current demo dataset is static; this ticket produces tooling to
   regenerate it from a live season so the public demo URL serves current-looking numbers.
   Not M1 (M1 friends sign in; demo freshness is an M2 concern), and unblocks fixture-based
   QA for several deferred waiver ideas — see backlog.

## Watching (maybe, not soon)

- **Off-season dev/test against a past week** — spike **033** RESOLVED (Tech Lead consult
  2026-07-03; DECISIONS.md 2026-07-03 "Dev/test: no runtime past-week override; use captured
  fixtures + demo mode instead"). No runtime week override / config knob / demo-in-auth swap
  is being built. The sanctioned follow-up — capture a real past-week response set into
  `tests/fixtures/` + add parse/cache tests — was reviewed by the PM (2026-07-03) and
  **deferred to `docs/backlog.md`**: the named parse/cache/orchestration paths are already
  covered by the existing synthetic-fixture suites, and the only net-new value (real-shape
  fixtures) is gated on a manual owner capture. Revive from the backlog entry when the owner
  next has live authenticated access, or fold into item 6 above.
- **Per-user cache storage migration** — **DROPPED** (Tech Lead consult 2026-07-23;
  DECISIONS.md "Cache: stays league-keyed; write safety comes from atomic rename +
  in-process locking, not per-user keying"). The cache holds no user-private data, and
  per-user keys would multiply API calls and storage without fixing the concurrency
  defect they were assumed to address. Do not scope this. The real work is cache
  write-hardening — now scoped as ticket **037** (Next up item 1).
- **Historical player-performance store for analysis / ML** — owner intent recorded
  2026-07-26; filed in `docs/backlog.md` as "Historical player-performance store for analysis
  / ML". The owner wants fetched player data to accumulate into a durable dataset for their
  own analysis and modelling, rather than being overwritten by the TTL cache. **Not scoped,
  and not scopeable yet:** it lands on the cache/on-disk-layout architectural surface (needs a
  Tech Lead consult), it is gated behind the due audit, and it reverses the `CLAUDE.md`
  "Multi-season historical data — out of scope" line, which is an owner decision. Post-M1;
  it serves no launch milestone. The backlog entry carries the consult brief, the sampling-bias
  problem (today's pool data is top-25-available-only), and the two schema hazards.
- **Yahoo rate-limit hardening** — **M2**, not M1. Two `docs/improvements.md` items cut
  steady-state Yahoo call volume: caching `/league/{key}/settings` (2 calls per authenticated
  render today) and the shared `ww_lastmonth` / NHL-schedule tier (DECISIONS 2026-07-23
  "Cache: league-independent data gets a shared tier at M2"). Both matter when strangers
  multiply leagues and the shared rate budget tightens — the M2 gate. At M1's ~6 leagues the
  budget is generous, so these are deliberately out of M1 scope. The settings-cache item also
  touches `data/client.py` (an architectural surface needing its own Tech Lead consult) — do
  not fold it into the M1 cache work.

---

_Last updated: 2026-07-26 (scoped the due audit as ticket **041**, with a second
owner-requested theme on test-suite health; ticket **037 cache write-hardening SHIPPED** —
removed from Next up; pruned the stale duplicate 036a entry [036a/036b shipping is already
recorded under the 040 item]; added the owner's historical player-data / ML idea to Watching
and to `docs/backlog.md`).
Prior: 2026-07-25 (036a and 036b shipped; scoped ticket 040 nav-shell test
hardening from the 036b review's two should-fix findings; noted the audit cadence sits at
4.5/5 weighted, so the ticket after 040 completes is an audit).
Prior: 2026-07-25 (added the approved Launch milestones section [M1/M2/M3 +
owner-action launch steps]; scoped the M1 ticket set — 037 cache write-hardening, 038
matchups parquet-bloat fix, 039 deployment fly.toml/.dockerignore; tagged 036a m1 / 036b m2;
pruned shipped 032/034/035 from Next up; recorded Yahoo rate-limit work as M2).
Prior: 2026-07-03 (item 4 demo-mode nav: Tech Lead consult done, split into ready
tickets 036a [foundation] + 036b [feature-page adoption]; old single 036 retired).
Prior: 2026-07-03 (spike 033 resolved: recorded the no-runtime-override decision and
deferred the optional fixture-capture + tests follow-up to backlog — parse/cache paths
already covered).
Prior: 2026-07-03 (audit 032 follow-up: removed shipped Week Projection migration
028–031; scoped param convergence into ticket 035 and demo-mode navigation into ticket 036
[blocked on Tech Lead consult]). The PM maintains this file during scoping and product
reviews._
</content>
</invoke>
