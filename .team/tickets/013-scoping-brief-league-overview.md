# 013 — Scoping brief: League overview UI patterns

> **Status:** Scoping brief, not an implementation ticket. Hand this to the Tech Lead
> *before* the PM finalizes tickets 014/015 (weekly leaderboard + head-to-head).
> Output is decisions captured in `docs/decisions.md` and notes back to the PM for ticket
> "Notes for the engineer" sections.

## Why this brief exists

League overview is the first feature page to migrate from the Streamlit prototype to the
FastAPI/Jinja2/HTMX stack. Four cross-cutting UI decisions get silently locked in by the
first ticket whether we choose them consciously or not, and each one also shapes waiver
wire (next) and week projection (after).

We want the Tech Lead to pick (or modify) an option for each, so the ticket writer has
explicit guidance rather than an implicit precedent.

## Context the Tech Lead should re-read before deciding

- `docs/ARCHITECTURE.md` — specifies FastAPI + Jinja2 + HTMX + Alpine + Tailwind, no JS build.
  States that filter interactions should use the HTMX fragment pattern (section "Key patterns" #5).
- `docs/backlog.md` — entries "Migration: League overview page", "Migration: Waiver wire page",
  "Migration: Week projection page". The waiver wire entry describes lazy-loading per
  (position, stat) pair — a real constraint that affects Decision 1.
- `web/templates/base.html` — current shell is bare (no nav).
- `web/templates/home.html` — current landing page has its own self-contained layout.
- Ticket 011 — `user_sessions.league_key` column now holds the selected league; this
  pre-commits us toward Decision 3 Option B unless we reverse course.

---

## Decision 1 — Table rendering and filter interaction

Weekly leaderboard needs a week selector; head-to-head needs two team selectors. Waiver
wire (next feature) will need position filter + stat toggles + period radio + pagination,
with lazy-loaded data per (position, stat) combination.

### Options

**A — Full page re-render per selector change (query-string GETs)**
- Implementation cost: S — simplest possible.
- Future cost: waiver wire's lazy-loading and pagination will either need to be bolted on
  later, or every filter change reloads the whole shell (flickery UX).
- Good if: we want the absolute minimum first ticket and accept refactoring when waiver
  wire lands.

**B — HTMX fragment swap per selector change (ARCHITECTURE.md's stated pattern)**
- Implementation cost: M — requires splitting each page into a shell template + a
  fragment template, plus a fragment route endpoint.
- Future cost: waiver wire slots in naturally (same pattern). Locks in the "every feature
  page has `templates/<feature>/` with `index.html` + `_table.html`" convention.
- Good if: we want to stop refactoring the pattern after ticket 014 and for the rest of
  the migration.

**C — Alpine client-side filter + HTMX for data fetches**
- Implementation cost: M-L — need to ship all weeks/teams data to the browser up front,
  then filter in Alpine. Fetches only happen when new data is genuinely needed.
- Future cost: hybrid mental model ("is this filter client or server?") for every future
  page. Waiver wire can't use this path (pool data is too large to preload).
- Good if: we want fastest perceived UX at the cost of consistency.

### PM lean
**B.** The architecture doc already commits to it, waiver wire requires it, and the "shell
+ fragment" split is a small cost paid once.

---

## Decision 2 — Cell color-coding for best/worst per stat

Prototype: inline HTML in `st.html()` with inline CSS styles. New stack: Tailwind utility
classes. `analysis/team_scores.avg_ranks()` already produces per-cell ranks (1..N).

### Options

**A — Server computes Tailwind class strings in Python**
- `analysis/` or a route helper returns rows with a pre-baked class string per cell.
- Pro: one place to change the mapping. Con: couples pure-Python analysis output to
  Tailwind class names (ARCHITECTURE.md says `analysis/` has no framework deps — but
  Tailwind class strings aren't a framework dep per se, they're styling metadata).

**B — Template-side mapping keyed on the rank integer**
- Analysis returns rank (integer). Jinja macro or filter maps `rank → Tailwind class`
  (`rank-1 → bg-green-100`, `rank-N → bg-red-100`, else `bg-white`).
- Pro: keeps `analysis/` free of styling concerns. Con: requires knowing team count in
  the template to compute "worst".

**C — Client-side styling via Alpine**
- Send raw ranks; Alpine walks each column, finds min/max, applies classes.
- Pro: fully decoupled. Con: duplicates ranking info already computed server-side; JS
  runs on every render.

### PM lean
**B.** `analysis/team_scores.py` has no framework imports today; keeping it that way is a
cheap invariant. Team count is already known at render time (it's `len(rows)`).

---

## Decision 3 — League context propagation

Ticket 011 already put the selected league in a `user_sessions.league_key` column. Routes
read it from the session row. **This is Option B below — already in place.** The question
is whether to keep it or move to path-based URLs before more feature pages cement the
session-state pattern.

### Options

**A — Path-based: `/leagues/{league_key}/overview`, `/leagues/{league_key}/waiver`**
- Implementation cost: M — every feature route takes `league_key` as a path param;
  templates build links with the current league key; league selector writes to URL not DB;
  `user_sessions.league_key` column becomes unused or a "most recently viewed" convenience.
- Future cost: bookmarkable and shareable URLs; multi-tab "different leagues in different
  tabs" works naturally. Slight ceremony in every route signature.
- Good if: we think users will reasonably want to switch leagues across tabs, link to a
  specific league's view, or have a URL structure that maps to REST conventions.

**B — Session-state (current): bare routes, league looked up from `user_sessions`**
- Implementation cost: zero (already built).
- Future cost: can't open two leagues in two tabs (they share one session row); switching
  leagues is a POST not a GET; URLs don't reflect state.
- Good if: single-league-at-a-time is the expected use case and we don't want ceremony.

**C — Query string: `/overview?league=<key>`, session as fallback**
- Implementation cost: S-M — every route tries query param first, then session.
- Future cost: hybrid mental model; two sources of truth for "which league."
- Good if: we want bookmarkable URLs without fully committing to path-based routing.

### PM lean
Genuine coin flip between **A** and **B**. B is sunk-cost-free and fast. A costs one
refactor ticket now but removes a class of future friction (bookmarking, sharing, multi-tab).
Tech Lead call — this is the kind of thing where future-cost intuition matters more than
implementation cost.

---

## Decision 4 — Page nav shell

`base.html` has no nav today. Feature pages will need some way to navigate between
Overview / Waiver / Projection, switch leagues, and log out.

### Options

**A — Build a nav shell in `base.html` now, as part of ticket 014**
- Header row with: league name (clickable to switch), feature links, logout.
- Pro: ticket 015 (head-to-head) and later waiver wire ticket inherit the nav for free.
- Con: a couple extra files touched in ticket 014; nav design decisions made before we
  know what all the pages need.

**B — Defer nav until a second feature page exists**
- Ticket 014 just has a back-link to `/`.
- Pro: avoids designing nav in a vacuum.
- Con: every subsequent ticket has to remember to retrofit, and nav design drifts.

**C — Minimal nav now: just the league label + logout in `base.html`**
- Feature links added per-ticket as pages appear.
- Pro: lowest-cost forward-compatible option.
- Con: feature links added piecemeal can look inconsistent unless a convention is set up front.

### PM lean
**C.** Low overhead, gives ticket 014 a proper header without over-designing, and the
nav grows as pages land. Option A is also reasonable if the Tech Lead wants to commit to
the full set of feature links up front.

---

## Asks of the Tech Lead

1. Pick or modify an option for each of the four decisions. For any significant choice,
   add an entry to `docs/decisions.md` so future contributors have the rationale.
2. Flag anything that conflicts with `docs/ARCHITECTURE.md` (especially if Decision 3A
   is chosen — session middleware may need adjusting).
3. Flag anything that reshapes the ticket split. Current plan is:
   - Ticket 014 — Weekly leaderboard view (data layer already ready; pure UI + whichever
     patterns are decided above).
   - Ticket 015 — Head-to-head comparison view (reuses ticket 014's patterns).
   If Decision 3A is chosen, a small routing-refactor ticket may need to precede 014.

## After the Tech Lead responds

The PM takes the decisions and writes tickets 014 and 015, citing the agreed patterns in
"Notes for the engineer."
