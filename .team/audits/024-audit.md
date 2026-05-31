## Audit Checkpoint 024 — covering tickets 020, bug-week23-all-zeroes, 021, 022, 023

**Date:** 2026-05-31

---

### Tickets reviewed

- **020** — Demo mode: `/overview` leaderboard (`web/routes/overview.py`, `web/templates/overview/index.html`, `web/main.py`)
- **bug-week23-all-zeroes** — Bug fix: week 23 all-zero rows (`data/matchups.py`, `tests/test_matchups.py`)
- **021** — Demo mode: `/overview/head-to-head` (`web/routes/overview.py`, `web/templates/overview/head_to_head.html`)
- **022** — Logout: confirmation banner and correct redirect (`web/routes/auth.py`, `web/templates/home.html`, `tests/test_auth_routes.py`)
- **023** — Optional auth on `GET /`: fix logged-out banner and login prompt (`web/middleware/session.py`, `web/routes/home.py`, `web/templates/home.html`, `tests/test_home_routes.py`)

---

### Findings

- **should-fix:** `DECISIONS.md` entry "matchups.py: current week is included in delta fetch; won't refresh mid-week (2026-03-03)" now directly contradicts the code. The bug fix changed the behavior so `current_week` is **always** appended to `weeks_to_fetch`, every call, regardless of cache state. The entry still reads: "Once that week is cached, the next call finds `last_cached_week == current_week` and fetches nothing new until Yahoo advances `current_week`. Intra-week stat updates are therefore not reflected until the cache is manually cleared." That is no longer true. A future engineer reading this entry may believe the current week is cached once and "fix" the always-re-fetch guard, reintroducing the original bug. The entry must be superseded with a note pointing at the bug fix. The Engineer updated the module docstring correctly but left `DECISIONS.md` untouched. The per-ticket reviewer who would normally catch this was never assigned (see process gap below). **Spans: bug-week23-all-zeroes.**

- **should-fix:** No per-ticket review exists for **bug-week23-all-zeroes**. The QA report is APPROVED but there is no `-review.md` file for this ticket. Every other ticket in this batch — 020, 021, 022, 023 — has a review. The stale `DECISIONS.md` entry above is a direct consequence: reviews explicitly check "DECISIONS.md conflict" and "implicit-decision drift," and neither check ran for the bug fix. The PM should decide whether to retroactively run the review or accept the `DECISIONS.md` superseding entry as sufficient remediation.

- **should-fix:** `ARCHITECTURE.md` Key patterns #2 was not updated to mention `optional_user`. Ticket 023 explicitly noted: "`ARCHITECTURE.md` key patterns #2 will need a one-line addition when this ticket lands... That is a Tech Lead responsibility, not the engineer's." The ticket closed without that addition. Key patterns #2 currently describes only `require_user`; `optional_user` is invisible to anyone reading the architecture reference. The `DECISIONS.md` entry for `optional_user` is correct and complete, but the architecture doc is incomplete. Tech Lead action: add one sentence to Key patterns #2: "`optional_user` is a variant that returns `None` instead of raising `RequiresLogin`; use it for routes that render in both authenticated and unauthenticated states." **Spans: 023.**

- **nit (logged to `docs/improvements.md`):** `base.html` renders "Overview", "Waiver", and "Logout" nav links unconditionally. After ticket 023, unauthenticated visitors on the home page see a "Log in with Yahoo" CTA in the content area but also three nav links that all lead to auth flows or a no-op logout. The Engineer flagged this in the 023 done note as a follow-up but did not log it to `docs/improvements.md`. Logged below.

- **nit (updating `docs/bugs.md` entry):** The open `docs/bugs.md` bug "matchups.py re-fetch loop causes parquet bloat" worsened incrementally after bug-week23-all-zeroes. Before the fix, only `prev_week` was appended on every same-day session. After the fix, `current_week` is also appended on every session, always. The existing entry covers the mechanism and fix directions; it should be updated to mention that `current_week` now participates in the bloat too. Logged to `docs/improvements.md` for the next engineer touching `data/matchups.py`.

---

### Implicit decisions surfaced

- **QA engineer writes missing tests.** Tickets 022 and 023 both shipped with test coverage gaps from the Engineer; QA added the missing tests during the QA pass (3 tests for 022's banner render path; 3 tests + a renamed test for 023's unauthenticated paths). This is a positive outcome but it is now a consistent pattern — QA is partly acting as co-implementer when test coverage is thin. No policy exists for this. The Tech Lead should decide: either (a) this is fine and the expectation is that QA fills gaps, or (b) the Engineer should be returned the ticket when automated AC coverage is missing. Without a ruling, Engineers will keep shipping under-tested implementations knowing QA will close the gap. **Spans: 022, 023.**

- **Open `improvements.md` items accruing without follow-up tickets.** As of this audit, two items have been open since code review 020: "No automated tests for `/demo/overview` and `/demo/overview/table` routes" and "'Compare two teams' link hard-codes `/overview/head-to-head` in shared template." The second item is now unblocked (ticket 021 shipped the prerequisite route). Per the demo route pairing policy (DECISIONS.md 2026-05-30), deferred work requires an explicit ticket. These are improvements-level items rather than features, but they have been sitting without action through an entire audit cycle. PM should review open improvements items at each audit and decide whether any graduate to tickets or get assigned to an in-flight ticket's scope.

---

### DECISIONS.md hygiene

The following pre-existing entries (predating audit 001's scope) lack a `Revisit if` clause. Flagged for Tech Lead to add clauses when these entries are next touched — not urgent, low-priority hygiene:

- "client.py: unknown and display-only stats silently skipped" (2026-03-03)
- "leagues.py: patch target is data.leagues._get, not data.client._get" (2026-03-03)
- "leagues.py: get_user_hockey_leagues() filters by game code, not game name" (2026-03-03)
- "client.py: bulk teams/stats endpoint replaces per-team fetching" (2026-03-23)
- "client.py: _coerce() handles None values, not just '-'" (2026-03-23)
- "players.py: type=lastmonth is the correct param for last-30-day player stats" (2026-03-23)
- "players.py: two API calls per page of 25 players" (2026-03-23)
- "players.py: imports private helpers from data/client.py" (2026-03-23)

---

### Suggested actions (priority order)

1. **(Tech Lead)** Supersede the "matchups.py: current week is included in delta fetch; won't refresh mid-week (2026-03-03)" entry in `DECISIONS.md`. New entry should document that `current_week` is always appended to `weeks_to_fetch` to ensure intra-week stat updates are reflected on every app visit, and reference the bug fix.
2. **(PM)** Decide how to handle the missing review for bug-week23-all-zeroes — retroactive review or accept action 1 as sufficient remediation.
3. **(Tech Lead)** Add the `optional_user` sentence to `ARCHITECTURE.md` Key patterns #2.
4. **(PM)** File tickets for the two long-open improvements.md items from code review 020: demo overview test coverage and the hardcoded compare-teams link (the latter is now unblocked, shipped as tickets 025 and 026).
5. **(Tech Lead)** Rule on the QA-writes-tests pattern — document the team norm either way.
6. **(Tech Lead, low priority)** Add `Revisit if` clauses to the eight pre-2026-04-19 `DECISIONS.md` entries listed above.

---

### Verdict: NEEDS ATTENTION

The code shipped in all five tickets is correct and architecturally clean — no framework imports in the data layer, no per-entity Yahoo API loops, no security issues, no scope creep. The NEEDS ATTENTION verdict is driven by: (1) a stale `DECISIONS.md` entry that now actively contradicts the code (regression risk), (2) an `ARCHITECTURE.md` update assigned to the Tech Lead in ticket 023 that never landed, and (3) a missing per-ticket review for the bug fix. PM should not scope further architectural-surface tickets until actions 1–3 above are resolved.
