## Audit Checkpoint 032 — covering tickets 025, 027, 028, 029, 030, 031

**Date:** 2026-07-03

Weighted count 5/5 (025 light ½, 028 light ½, 027/029/030/031 full 1 each) — `AUDIT DUE`.
Theme focus: routing, template reuse, and demo parity, with a consistency check against
the demo-route pairing policy (`docs/DECISIONS.md` 2026-05-30).

---

### Tickets reviewed

- **025** (bug, light) — Parameterize hardcoded nav links in overview templates (`web/routes/overview.py`, `overview/index.html`, `overview/head_to_head.html`)
- **027** (feature) — Add tests for `/demo/overview` and `/demo/overview/table` (`tests/test_demo_overview_routes.py`)
- **028** (refactor, light) — Extract `_get_league_key` to `web/routes/common.py` (`common.py`, `overview.py`, `waiver.py`)
- **029** (feature) — Week Projection shell route + nav (`web/routes/projection.py`, `projection/index.html`, `web/main.py`, `base.html`)
- **030** (feature) — Week Projection matchup fragment (`web/routes/projection.py`, `projection/_matchup.html`)
- **031** (feature) — Week Projection demo parity (`web/routes/projection.py`, `web/main.py`)

---

### Prior audit (024) close-out — verified before proceeding

Audit 024 closed `NEEDS ATTENTION` with six actions; architectural-surface ticket 029
(new route module + new `web/templates/projection/` directory) should not have been
scoped until actions 1–3 landed. Confirmed all were resolved:

- **Action 1** (supersede stale `matchups.py` delta-fetch entry) — DONE: `DECISIONS.md`
  2026-05-31 "matchups.py: current_week always re-fetched" now supersedes the 2026-03-03 entry.
- **Action 3** (`optional_user` sentence in `ARCHITECTURE.md` Key patterns #2) — DONE:
  `docs/ARCHITECTURE.md:114`.
- **Action 5** (rule on QA-writes-tests) — DONE: `DECISIONS.md` 2026-05-31 "Engineer owns
  automated test coverage; QA does not fill gaps." **And it is being followed this cycle** —
  every ticket's Engineer shipped AC tests; QA added only *supplementary* edge coverage
  (030: `test_projection_matchup_qa.py`, 2 tests for correct-column highlight + tie), never
  primary AC suites. Positive.
- **Actions 2 & 4** (retroactive bug-week23 review; file tickets for long-open improvements
  items) — DONE: `bug-week23-all-zeroes-review.md` now exists in `tickets/done/`; the two
  action-4 items shipped as tickets 025 (compare-teams link) and 027 (demo-overview tests).

The `NEEDS ATTENTION` gate was respected. Good.

---

### Findings

- **should-fix (improvements-tracker hygiene, spans 027):** The `docs/improvements.md`
  item "No automated tests for `/demo/overview` and `/demo/overview/table` routes" is
  annotated *"(Scoped as ticket 027.)"* and ticket 027 shipped `tests/test_demo_overview_routes.py`
  containing the exact three required test names — **yet the item is still under `## Open`,
  not moved to `## Closed`.** This is precisely the audit-024 finding recurring: the
  follow-up ticket landed but no one closed the tracker item. The Engineer persona rules
  allow closing an improvements item a ticket resolves (025 did this correctly for the
  compare-teams link), but 027's done note never mentioned it and QA/Reviewer didn't flag
  the omission. Move it to `## Closed` with a ticket-027 resolution note. **Root cause is
  process, not code** — closing the resolved item should be an explicit step in the DoD for
  any ticket that was itself scoped off an improvements entry.

- **should-fix (demo-parity nav gap, spans 025, 029 — the batch's clearest cross-ticket
  pattern):** `web/templates/base.html:22-25` renders the nav — `/overview`, `/waiver`,
  `/projection`, `/auth/logout` — **unconditionally, on every page including every `/demo/*`
  route.** All four targets are auth-gated (or a no-op logout), so a demo visitor who clicks
  *any* header link is bounced to `/auth/login`. Ticket 025 fixed the analogous *in-content*
  links (compare / back) so demo overview navigation round-trips correctly — but the nav
  header was left untouched, and **ticket 029 then added a third bouncing link (Projection)**,
  deepening the gap in the same batch that fixed its sibling. The tracked item ("Nav header
  shows auth links to unauthenticated visitors", `improvements.md`, Source: Audit 024) still
  frames this narrowly as a *home-page* concern; the sharper, growing reality is that
  **demo mode now has three feature pages and zero working header navigation.** Combined with
  the still-open "Add demo mode entry point on home page" item, demo mode is reachable and
  internally functional but has no coherent way in or across. This has now survived two audit
  cycles as an improvements note with no ticket. Recommend the PM graduate it to a real
  ticket (conditional nav via an `is_authenticated`/demo-mode context flag), scoped to touch
  `base.html` plus the route contexts that must supply the flag.

- **should-fix (interface drift, spans 029 → 030 → 031):** The Week Projection matchup
  route permanently accepts **two** query-param names for the same value —
  `selected = team_key or my_team` — on *both* the live (`projection.py:249`,
  `_matchup_impl`) and demo (`demo_projection_matchup`) handlers. This exists only because
  ticket 030's AC1 specified `?my_team=<team_key>` while the ticket-029 shell it depends on
  had already shipped `<select name="team_key">` and `hx-get="...?team_key=..."`. The Engineer
  reconciled correctly (accept both, don't edit the out-of-scope shell) and both QA and the
  Reviewer signed off as a sound pragmatic choice — but the underlying cause is a **ticket-
  scoping verification gap**: 030's acceptance criteria contradicted the shipped interface of
  its own stated dependency (029), and the mismatch wasn't caught until implementation. It is
  logged to `improvements.md` (Code review 030) but, like the items above, has **no
  convergence ticket** — so the dual-param interface is currently permanent. Recommend a
  small 029-shell follow-up ticket to converge on one name (`team_key`, matching the shell)
  and drop the `my_team` alias from both routes.

- **nit (recurring AC imprecision, spans 029, 031):** Both tickets' ACs describe the
  logged-out guard as "redirects to `/`", but the actual logged-out path redirects to
  `/auth/login` (via `require_user` → `RequiresLogin` → the `main.py` handler); `/` is only
  the *authenticated-but-no-league* target. QA correctly dispositioned this both times
  (031-qa has a clear write-up), so no code issue — but it's a repeated ticket-authoring
  imprecision. PM should write redirect ACs against the actual guard target.

- **nit (ticket-text citation staleness, 029):** The 029 ticket cites the HTMX fragment
  decision as "2026-04-19"; the live entry is 2026-05-30 (which supersedes the same-title
  2026-04-19 entry). Code conforms; flagged in 029-review as a nit. PM scoping hygiene —
  cite the live DECISIONS entry.

---

### Demo-route pairing policy (2026-05-30) — CONSISTENT this cycle (positive)

The theme check passes. The projection feature followed the policy exactly, and is the
corrective opposite of the 015/016 violation that prompted the policy:

- **029** shipped the authenticated `/projection` shell with no demo counterpart, but the
  deferral was **explicitly tracked** — Out of scope names "Demo route `/demo/projection` —
  that is ticket 031", a scoped, sequenced ticket (stronger than the policy's "backlog
  ticket" minimum).
- **031** shipped the demo counterpart (`/demo/projection`, `/demo/projection/matchup`),
  reusing `index.html`/`_matchup.html` unchanged via the `matchup_url` / `selected_league_name`
  context parameterization that 029/030 built in for exactly this — the ticket-025 lesson
  applied end-to-end. No template edits were needed in 031, confirming the parameterization
  design held.
- Template reuse is clean: one shell, one fragment, one shared `_render_matchup(...)` compute
  path feeding both live and demo. No hardcoded route URLs in the reused templates.

This is the healthiest demo-parity execution the project has shipped. The one gap is
navigation (finding 2), which is orthogonal to the pairing policy.

---

### Implicit decisions surfaced

- **Shared live/demo compute helper (`_render_matchup`).** Ticket 031 factored the
  compute+tally+breakdown+render tail into a single helper fed by both the live and demo
  handlers, so the two paths are guaranteed identical — a cleaner pattern than the
  overview/waiver demo routes, which assemble context more independently. This is a good
  precedent but is currently a one-off. Worth a light `DECISIONS.md` note (or an
  `ARCHITECTURE.md` Key-patterns mention) that **demo and live route handlers should share a
  single compute/render helper where the only difference is data assembly**, so future
  feature pages copy projection's shape rather than overview/waiver's. Tech Lead to decide
  whether to ratify.

- **Matchup route accepts dual param names.** Undocumented convention drift (finding 3) —
  not a decision anyone made deliberately. Should be resolved by convergence, not ratified.

---

### DECISIONS.md hygiene

No new gaps this cycle — the four 2026-05-30 entries and both 2026-05-31 entries all carry
`Revisit if` clauses. The eight pre-2026-04-19 entries flagged in audit 024 still lack
`Revisit if` clauses; that remains an open low-priority Tech Lead item (unchanged, not
re-litigated here).

---

### Suggested actions (priority order)

1. **(Reviewer, immediate)** Move the "No automated tests for `/demo/overview`…" item to
   `docs/improvements.md` `## Closed` with a ticket-027 resolution note — it is resolved.
2. **(PM)** Graduate the demo-mode navigation gap to a real ticket: conditional nav in
   `base.html` driven by an auth/demo-mode context flag, covering all three feature links,
   plus the "Try the demo" home-page entry point. Two audit cycles as an unactioned note is
   enough. (Not architectural-surface-blocking, but user-visible in demo mode today.)
3. **(PM)** File the query-param convergence ticket (029-shell scope): standardize on
   `team_key`, drop the `my_team` alias from both `/projection/matchup` and
   `/demo/projection/matchup`, close the `improvements.md` item.
4. **(PM, process)** Add "close any `improvements.md` item this ticket was scoped from" to
   the ticket Definition of Done, so resolved items don't linger under `## Open`.
5. **(PM, process)** Write logged-out-redirect ACs against the real guard target
   (`/auth/login`), and cite the live (not superseded) `DECISIONS.md` entry when scoping.
6. **(Tech Lead, low priority)** Decide whether to ratify the shared live/demo
   `_render_matchup` helper pattern as the standard for future feature pages.

---

### Verdict: HEALTHY

The shipped code across all six tickets is correct, in-scope, and architecturally clean:
no framework imports in `data/`/`analysis/`/`auth/`, no per-entity Yahoo loops (projection
uses the bulk `get_all_teams_week_stats` + batched `get_players_lastmonth_stats`), no raw
`stat['value']`, no security or secrets issues, no scope creep, and full AC test coverage
authored by Engineers per the new coverage policy. The demo-route pairing policy — the
focus of this checkpoint — was followed exemplarily by the 029→030→031 sequence. All
audit-024 blocking actions were resolved before the architectural-surface projection work
proceeded.

The verdict is HEALTHY rather than NEEDS ATTENTION because every finding is a `should-fix`
or `nit`, none blocks merging or contradicts an active decision, and the one genuinely
user-visible gap (demo nav) is a pre-existing tracked item that this batch surfaced more
sharply rather than introduced. The recurring thread worth the PM's attention is **process,
not code**: resolved improvements items aren't being closed, and tracked-but-unticketed
items (demo nav, param convergence) accrue across audit cycles — the same pattern audit 024
flagged. Actions 1, 3, and 4 above address that thread directly.
