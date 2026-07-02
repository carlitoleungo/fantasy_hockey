# Roadmap — Fantasy Hockey Waiver Wire

Likely near-term work, in rough priority order. This is a **pressure-test tool, not a
commitment** — the PM reads it during scoping to ask "does this ticket's approach still
make sense if these land?"

Keep it to ~3–7 items. If it grows past that, it's stopped being a pressure-test tool
and become a wishlist — prune.

---

## Next up

1. **Week projection migration** — scoped into tickets **028–031** (2026-07-02). The
   data, analysis, and demo-data layers already exist and are framework-free, so this is
   a route+template exercise, not a data-layer build:
   - **028** — extract `_get_league_key` to `web/routes/common.py` (`Process: light`
     prerequisite per DECISIONS 2026-05-30).
   - **029** — `/projection` shell route, team selector, nav link.
   - **030** — `/projection/matchup` fragment: rosters + schedule + last-30 + compute.
   - **031** — `/demo/projection` parity (reuses existing `demo.get_projection_*`).
   Sequential dependency chain 028 → 029 → 030 → 031.
2. **Demo mode snapshot tooling** — `data/demo.py` snapshot generation script and fixture
   data refresh. The current demo dataset is static; this ticket produces tooling to regenerate
   it from a live season so the public demo URL serves current-looking numbers.

## Watching (maybe, not soon)

- **Per-user cache storage migration** — required before any shared deployment; see the
  `docs/backlog.md` entry for full context.
- **Deployment configuration** — blocked on feature pages being migrated first; see the
  `docs/backlog.md` entry for full context.
- **`matchups.py` parquet bloat** — tracked as a `Type: bug` entry in
  `docs/improvements.md`; cosmetic, not urgent.

---

_Last updated: 2026-07-02 (Week projection migration scoped into tickets 028–031;
shipped 025/027 removed). The PM maintains this file during scoping and product reviews._
