## Audit Checkpoint 001 — covering tickets 015, 016, 018, 019a, 019b

**Date:** 2026-05-30

---

### Tickets reviewed

- **015** — League overview: weekly leaderboard view
- **016** — League overview: head-to-head comparison view
- **018** — Waiver Wire: shell and filter controls
- **019a** — Waiver Wire: POST handler, season path, pagination, demo mode
- **019b** — Waiver Wire: Last-30 branching and games remaining

---

### Findings

- **blocker: Ticket 016 shipped without a review file.** No `016-review.md` exists anywhere in
  the repo (checked `tickets/done/` and `tickets/`). The diff was committed directly to the
  `done/` folder with no corresponding review step. The QA verdict was APPROVED, but per the
  process defined in `reviewer.md`, the review step must run after QA approval. This is the
  only ticket in the audit window to skip the review step.

  Additionally, the 016 commit includes a change to `reference/waiver_wire_helper_refactor.ipynb`
  that is not in the ticket's `Touches` list. The change replaced what appear to be real Yahoo
  OAuth credentials (`consumer_key`/`consumer_secret`) with placeholder values. This change was
  correct and necessary, but it was unacknowledged and unreviewed. The notebook may have had
  real credentials committed to it for an extended period prior to this fix; git history should
  be audited to confirm when those values were introduced and whether they have been rotated.

- ~~**should-fix: Systematic browser verification gap across all five tickets.**~~ **RESOLVED
  2026-05-30.** Owner ran a full browser smoke test covering `/overview`, `/overview/head-to-head`,
  and `/waiver` (authenticated and demo). All HTMX fragment swaps, filter preservation, and
  pagination confirmed working. GP/GR showing zeroes on Last 30 days is expected at season end
  (no remaining games; Yahoo returns 0 GP for a closed season). Demo isolation confirmed clean
  (no outbound Yahoo API calls in server logs).

- **should-fix: `pyarrow` dependency gap accepted as "pre-existing" for two tickets.** The
  019a QA report found 34 failing tests (`test_cache.py`, `test_matchups.py`) due to missing
  `pyarrow`, and the live demo endpoint returned 500. This was accepted as a pre-existing
  environment gap. The 019b QA ran with 326 tests passing, which means `pyarrow` was
  installed in that environment — but the underlying dependency is still absent from
  `requirements-web.txt`. Any new environment following `RUNNING.md` will reproduce the 34
  failures. The gap should have been fixed in whichever ticket introduced the parquet
  dependency (pre-015), but now that it is documented it must be added to
  `requirements-web.txt`. Logging to `docs/improvements.md`.

- **should-fix: Demo coverage gap for `/overview` and `/overview/head-to-head`.** Tickets 015
  and 016 correctly noted that no new `data/` functions were introduced, so no `data/demo.py`
  counterpart was technically required per the architecture rules. However, the result is that
  the two completed feature pages in the "Overview" section have no demo path: unauthenticated
  users who navigate to `/overview` or `/overview/head-to-head` are redirected to login. The
  waiver wire pages (018/019a/019b) do have demo counterparts. This asymmetry means a visitor
  in demo mode can explore the waiver wire but cannot see the leaderboard or head-to-head view.
  The project description says "a demo mode lets unauthenticated users explore a pre-snapshotted
  dataset" — that goal is only partially met. Logging to `docs/improvements.md`.

- **nit: DECISIONS.md HTMX fragment entry references wrong ticket.** The 2026-04-19 entry
  reads "Ticket 014 is the first page to establish the convention; 015 (head-to-head) and the
  waiver wire ticket inherit it." Ticket 015 is the leaderboard; 016 is head-to-head. The
  parenthetical is swapped. Low stakes but worth correcting so the decision log is accurate.

- **nit: `18-qa.md` artifact in `tickets/done/`.** There is both `018-qa.md` and `18-qa.md`
  in `tickets/done/`. The latter appears to be an earlier draft (it predates the fix cycle and
  lacks re-verification of the corrected demo bug). The duplicate should be removed to avoid
  confusion.

- **nit: `from data import demo as demo_module` remains an inline import.** The reviewer for
  ticket 018 flagged this as a nit (inconsistent with all other module-level imports) and it
  was not addressed in 019a or 019b, neither of which had the import in their Touches scope.
  The nit stands open; logging in `docs/improvements.md` is already present from 018 review
  (implicit in the 018 review nit section).

---

### Implicit decisions surfaced

The following conventions are now embodied in the codebase but have no `DECISIONS.md` entry.
The Tech Lead should ratify, amend, or reject each before the next architectural ticket.

**1. Shared route helpers imported across route modules.**
`_get_league_key` is defined in `web/routes/overview.py` and imported by (and intended for
future import by) other route modules. This cross-module import of a private-prefixed helper
is an intentional, ticket-specified design choice (ticket 015 done file, scope note), but
there is no DECISIONS.md entry for it. If the convention is "helpers shared across routes
live in the module that first needs them," that's worth capturing — especially because the
underscore prefix misleadingly signals module-private.

**2. Per-stat cache loop pattern in the waiver route.**
`_waiver_post_impl` iterates over `stats` and checks/populates a cache entry per stat name
(not per player). This is the correct pattern for the Yahoo API surface (batch call per stat,
not per player), but it is an architectural choice not captured anywhere outside the code.
When the projection route is built, its author needs to know to follow the same pattern.
Propose a DECISIONS.md entry: "Waiver and projection routes: per-stat cache reads, one bulk
API call per stat, never a per-player loop."

**3. Web-layer demo route pairing convention.**
The architecture rules in `reviewer.md` require a `data/demo.py` counterpart for every new
`data/` function. But there is no stated rule for demo routes at the web layer — whether
every authenticated feature route must have a `/demo/...` counterpart, and if so, whether
that counterpart is built in the same ticket or a follow-up. Tickets 015 and 016 deferred
demo routes with no follow-up ticket created. Tickets 018/019a/019b built demo routes inline.
The inconsistency should be resolved in DECISIONS.md so future tickets have a clear policy.

**4. `DECISIONS.md` entries lack `Revisit if` clauses.**
All entries from 2026-03-03 and 2026-04-19 document the decision but do not include a
`Revisit if` clause as the audit checklist requires. The 2026-04-19 "League context" entry
is the only one with an explicit revisit trigger ("when multi-user public deployment is
scoped"). The Tech Lead should add `Revisit if` clauses to the entries that lack them,
particularly: auth flow (yahoo_oauth not used), per-stat cache loop, and the HTMX fragment
pattern.

---

### Suggested actions

Priority order:

1. ~~**Owner (security):** Rotate Yahoo credentials.~~ **DONE 2026-05-30.**

2. ~~**Owner (process):** Write `tickets/done/016-review.md`.~~ **DONE 2026-05-30.**

3. ~~**Owner (verification):** Browser smoke test.~~ **DONE 2026-05-30.**

4. ~~**Engineer (dependency):** Add `pyarrow` to `requirements-web.txt`.~~ **ALREADY PRESENT** — `pyarrow` was already in `requirements-web.txt` on line 9; improvement item was stale and has been removed from `docs/improvements.md`.

5. **Tech Lead (DECISIONS.md):** Ratify or reject the three implicit decisions surfaced
   above, write entries for the two new ones (shared route helpers, per-stat cache loop, web
   demo route pairing), and add `Revisit if` clauses to the existing entries that lack them.

6. **PM (backlog):** Create follow-up tickets for `/demo/overview` and
   `/demo/overview/head-to-head` so the demo mode gap is tracked as scoped work, not just an
   open note.

---

### Verdict: NEEDS ATTENTION

All blockers and owner actions resolved as of 2026-05-30 (credentials rotated, 016 review
written, browser smoke test passed, pyarrow already present). Remaining open items are Tech
Lead actions: ratify the three implicit decisions in DECISIONS.md and add `Revisit if`
clauses to existing entries. The PM should scope follow-up tickets for demo coverage of the
overview pages. No further architectural tickets should be scoped until the DECISIONS.md
items are addressed.
