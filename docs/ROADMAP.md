# Roadmap — Fantasy Hockey Waiver Wire

Likely near-term work, in rough priority order. This is a **pressure-test tool, not a
commitment** — the PM reads it during scoping to ask "does this ticket's approach still
make sense if these land?"

Keep it to ~3–7 items. If it grows past that, it's stopped being a pressure-test tool
and become a wishlist — prune.

---

## Next up

1. **Waiver wire multi-position filter** — scoped into ticket **032** (2026-07-02).
   Convert the waiver page's single-select position pills to a multi-select so managers
   can find dual-eligible players (e.g. C + LW). UI-layer only: the per-position player
   pool cache is already keyed by position, so this is a route + template change (loop
   the fetch over selected positions, union the pools). Demo parity included.
2. **Week Projection roster-breakdown readability** — scoped into ticket **034**
   (2026-07-03). Presentation-only cleanup of the `_matchup.html` roster breakdown:
   separate goalie stats from skater stats, abbreviate column headers (Yahoo
   `abbreviation`) and player names to reduce horizontal scroll. Depends on 031 (demo
   parity) so the change lands consistently on both the authenticated and demo renders.
3. **Projection matchup param convergence** — scoped into ticket **035** (2026-07-03,
   `Process: light`, from audit 032). Drop the dual `team_key`/`my_team` query-param alias
   on `/projection/matchup` and `/demo/projection/matchup`, converging on `team_key` (the
   shell's existing name). Route-only cleanup + test updates.
4. **Demo-mode navigation** — Tech Lead consult **DONE** (2026-07-03; DECISIONS.md
   "Nav shell: conditional on auth/demo state via shared shell-context"), mechanism is
   Option C (shared `shell_context()` helper reusing the resolved user; `base.html` branches
   and defaults to the auth nav). Scoped into **two `ready` tickets** — **036a** (foundation:
   `common.py` helper + conditional `base.html` + `home.py` adoption; ships the logged-out-home
   nav fix and closes the "Nav header shows auth links to unauthenticated visitors"
   improvements item) and **036b** (adopt the helper in `overview.py`/`waiver.py`/`projection.py`;
   ships the demo nav fix across all three demo pages). 036b depends on 036a. The "Try the
   demo" home entry point remains a separate follow-up ticket (deliberately not bundled).
5. **Demo mode snapshot tooling** — `data/demo.py` snapshot generation script and fixture
   data refresh. The current demo dataset is static; this ticket produces tooling to regenerate
   it from a live season so the public demo URL serves current-looking numbers.

## Watching (maybe, not soon)

- **Off-season dev/test against a past week** — spike **033** RESOLVED (Tech Lead consult
  2026-07-03; DECISIONS.md 2026-07-03 "Dev/test: no runtime past-week override; use captured
  fixtures + demo mode instead"). No runtime week override / config knob / demo-in-auth swap
  is being built. The sanctioned follow-up — capture a real past-week response set into
  `tests/fixtures/` + add parse/cache tests — was reviewed by the PM (2026-07-03) and
  **deferred to `docs/backlog.md`**: the named parse/cache/orchestration paths are already
  covered by the existing synthetic-fixture suites, and the only net-new value (real-shape
  fixtures) is gated on a manual owner capture. Revive from the backlog entry when the owner
  next has live authenticated access, or fold into item 5 below.
- **Per-user cache storage migration** — required before any shared deployment; see the
  `docs/backlog.md` entry for full context.
- **Deployment configuration** — blocked on feature pages being migrated first; see the
  `docs/backlog.md` entry for full context.
- **`matchups.py` parquet bloat** — tracked as a `Type: bug` entry in
  `docs/improvements.md`; cosmetic, not urgent.

---

_Last updated: 2026-07-03 (item 4 demo-mode nav: Tech Lead consult done, split into ready
tickets 036a [foundation] + 036b [feature-page adoption]; old single 036 retired).
Prior: 2026-07-03 (spike 033 resolved: recorded the no-runtime-override decision and
deferred the optional fixture-capture + tests follow-up to backlog — parse/cache paths
already covered).
Prior: 2026-07-03 (audit 032 follow-up: removed shipped Week Projection migration
028–031; scoped param convergence into ticket 035 and demo-mode navigation into ticket 036
[blocked on Tech Lead consult]).
Prior: 2026-07-03 (scoped Week Projection roster-breakdown readability into ticket 034;
added off-season past-week dev/test spike 033 to Watching). 2026-07-02 (Waiver
multi-position filter scoped into ticket 032; week projection migration scoped into tickets
028–031; shipped 025/027 removed). The PM maintains this file during scoping and product
reviews._
