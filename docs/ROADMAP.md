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
with each other — **on re-designed pages, not the current functional markup.**

**Amended 2026-07-26 (owner):** M1 is no longer functional-only. The owner's designs must be
applied to the app's pages before M1 is called done, so the UI re-design is M1 work
alongside deployment. This reverses the earlier reading that "M1's definition is functional,
not styled, so polish does not block M1" (recorded in the `docs/backlog.md` entry "UX
cleanup and design application", now superseded there too).

**M1 work list:**

1. **Deployment config** — ticket **039** (`fly.toml` + `.dockerignore`). The gate. **SHIPPED
   2026-07-26.**
2. **Deployment config follow-ups** — ticket **045**, from Review 039's two should-fix
   findings: widen `.dockerignore`'s secret patterns to `**/.env*` / `**/*.pem` (root-anchored
   today, so a future nested `.env` or cert would be baked into the production image with no
   warning), and flip `auto_start_machines` to `true` so Fly Proxy restarts the pinned machine
   after a host migration, OOM stop, or manual stop instead of leaving the app down until the
   owner runs `fly machine start`. **Run this early in the 042/044/045 batch** — it is the only
   architectural-surface ticket among them, so it is the only one an overdue audit blocks, and
   042 + 044 alone push `scripts/audit_due.py` from 3.0 to 5.0.
3. **UI re-design applied to the pages** — **not yet scopeable.** Blocked on two owner
   inputs: the design assets/mockups themselves, and the priority order of pages. Scope one
   ticket per page when those arrive (`docs/backlog.md` "UX cleanup and design application"
   recommends per-page tickets over one cross-page ticket, and that recommendation stands).
4. **Error-page nav fix** — ticket **042** (logged-out and demo visitors currently get an
   authenticated nav on 500/502 pages, every link of which dead-ends at `/auth/login`).
5. Owner actions 1–4 below (Yahoo redirect URI, `fly apps create`, Fly volume + deploy,
   Streamlit decommission).

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
2. **Create the Fly app, and reconcile its name with `fly.toml`.** Ticket 039 had to invent an
   app name (nothing in DECISIONS or this file named one) and shipped
   `app = "fantasy-hockey-waiver"`. Run `fly apps create fantasy-hockey-waiver`, or create it
   under another name and edit `fly.toml`'s `app` key to match. A mismatch fails loudly
   (`fly deploy` cannot find the app) rather than quietly, so this is a sequencing note, not a
   risk. **Owner action** (routed here by Review 039).
3. **Provision the Fly volume and deploy.** After the app exists, run `fly config validate`
   (the first deploy step — `flyctl` was unavailable when 039 was built, so the Fly schema has
   never been checked), then `fly volumes create data --size 1 --region iad`, set the Yahoo
   secrets via `fly secrets set`, then `fly deploy`. The `fly.toml` is the ticket; running the
   deploy is an owner action (needs a Fly account and auth). Post-deploy, `fly status` /
   `fly scale show` is the only place the single-machine pin becomes observable, and it is also
   where the `auto_stop_machines` boolean-vs-`"off"` question in `docs/improvements.md` can
   finally be settled.
4. **Decommission Streamlit Community Cloud** once the Fly app is live and validated —
   disconnect the app in the SC dashboard. See the backlog entry "Streamlit Community Cloud
   decommissioning" (tagged m1). Mostly a dashboard action; a redirect is only worth setting
   up if external links to the SC URL exist. **Owner action, not a ticket.**

---

## Next up

1. **M1 deployment config follow-ups** — ticket **045** (2026-07-26), from Review 039's two
   should-fix findings. `.dockerignore`'s secret patterns (`.env`, `.env.*`, `*.pem`) are
   anchored to the build-context root while its bytecode patterns were widened to `**/` during
   039's fix round, so a future nested `.env` or certificate would be baked into the production
   image with no warning (no exposure today — every match in the repo is root-level). And
   `fly.toml`'s `auto_start_machines = false` leaves the pinned machine with no automatic
   restart path: Fly Proxy will not bring it back after a host migration, OOM stop, or manual
   stop, so the app stays down until the owner runs `fly machine start`
   (`min_machines_running = 1` does not cover this — it applies only when `auto_stop_machines`
   is `stop`/`suspend`, so it is inert as configured). Covered by the same Tech Lead consult
   2026-07-23 (DECISIONS "Deployment: M1 shape — single pinned machine, 1 GB volume, fly.toml
   in repo"): auto-start only restarts an *existing stopped* machine and never creates one, so
   the flip cannot breach the single-machine pin and needs no new consult. **Ticket 039 itself
   SHIPPED 2026-07-26** (QA + review both APPROVED, artifacts in `tickets/done/`), so the M1
   gate is clear. **Run 045 early in the 042/043/044/045 batch** — it is the only
   architectural-surface ticket of the four, so it is the only one an overdue audit blocks;
   `scripts/audit_due.py` reads 3.0 / 5.0 today and 042 + 044 alone reach 5.0. The
   `auto_stop_machines` boolean-vs-`"off"` deprecation is deliberately **not** in 045: it needs
   `flyctl` at `fly config validate` time, so it stays a `docs/improvements.md` item and is
   settled at the owner's deploy (launch step 3 above).
2. **M1 UI re-design** — **owner scope change 2026-07-26: this is now M1 work** (see the M1
   definition above). **Not scoped, and not scopeable yet** — the owner must supply the design
   assets/mockups and name the priority page order first. One ticket per page when they
   arrive, per `docs/backlog.md` "UX cleanup and design application" (re-tagged m1).
3. **Nav shell follow-ups** — scoped 2026-07-26 into three tickets from `docs/improvements.md`:
   **042** error pages declare auth state unknown and render nav-free (m1, implements
   DECISIONS 2026-07-25); **043** "Try the demo" CTA on the logged-out home page (m2, light —
   demo mode is built but nothing links to it); **044** flip `base.html`'s absent-flag default
   from the authenticated nav to nav-free (no milestone, implements the same decision's
   "Forward commitment" paragraph, unblocked now that 036b has shipped). **044 depends on 042**
   — both edit the same `base.html` branch block. 043 is independent of both.
4. **Demo mode snapshot tooling** — `data/demo.py` snapshot generation script and fixture
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
  next has live authenticated access, or fold into the demo-snapshot-tooling item above.
- **Per-user cache storage migration** — **DROPPED** (Tech Lead consult 2026-07-23;
  DECISIONS.md "Cache: stays league-keyed; write safety comes from atomic rename +
  in-process locking, not per-user keying"). The cache holds no user-private data, and
  per-user keys would multiply API calls and storage without fixing the concurrency
  defect they were assumed to address. Do not scope this. The real work was cache
  write-hardening, shipped as ticket **037**.
- **Historical player-performance store for analysis / ML** — owner intent recorded
  2026-07-26; filed in `docs/backlog.md` as "Historical player-performance store for analysis
  / ML". The owner wants fetched player data to accumulate into a durable dataset for their
  own analysis and modelling, rather than being overwritten by the TTL cache. **Not scoped,
  and not scopeable yet:** it lands on the cache/on-disk-layout architectural surface (needs a
  Tech Lead consult) and it reverses the `CLAUDE.md`
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

_Last updated: 2026-07-26 (**ticket 039 SHIPPED — the M1 deployment gate is clear**; scoped its
two review should-fix findings into one ticket **045** [`.dockerignore` `**/` secret globs +
`fly.toml` `auto_start_machines = true`], accepted DECISIONS 2026-07-23 "Deployment: M1 shape" as
the covering decision so no new Tech Lead consult was needed, and added 045 to the M1 work list;
added the missing **`fly apps create`** owner launch step reconciling the app name with
`fly.toml`'s invented `app = "fantasy-hockey-waiver"`, and `fly config validate` as the first
deploy command, both routed to the PM by Review 039).
Prior: 2026-07-26 (**owner scope change: the UI re-design is now part of M1** —
amended the M1 definition, added an M1 work list, and re-tagged the `docs/backlog.md` entry
"UX cleanup and design application" from `none` to m1 with the superseded reasoning preserved;
scoped three tickets from `docs/improvements.md` — **042** error-page nav-free, **043** demo
CTA [light], **044** `base.html` default flip [depends on 042]; pruned shipped 038/040 and
completed audit **041** from Next up).
Prior: 2026-07-26 (scoped the due audit as ticket **041**, with a second
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
