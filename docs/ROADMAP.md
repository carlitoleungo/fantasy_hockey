# Roadmap — Fantasy Hockey Waiver Wire

Likely near-term work, in rough priority order. This is a **pressure-test tool, not a
commitment** — the PM reads it during scoping to ask "does this ticket's approach still
make sense if these land?"

Keep it to ~3–7 items. If it grows past that, it's stopped being a pressure-test tool
and become a wishlist — prune.

---

## Next up

1. **020 — Demo mode: /overview leaderboard** — add `/demo/overview` and `/demo/overview/table`
   backed by `data.demo.get_matchups()`. Closes the largest demo coverage gap. Ticket is `ready`.
2. **021 — Demo mode: /overview/head-to-head** — add `/demo/overview/head-to-head` and its
   fragment endpoint. Completes demo parity for the entire Overview section. Blocked on 020.
3. **Week projection migration** — most data-intensive page; tackle after demo coverage is
   complete and the HTMX fragment pattern is fully validated across all existing pages.
4. **Demo mode snapshot tooling** — `data/demo.py` snapshot generation script and fixture
   data refresh. The current demo dataset is static; this ticket produces tooling to regenerate
   it from a live season so the public demo URL serves current-looking numbers.

## Watching (maybe, not soon)

- **Per-user cache storage migration** — current `/data/cache/{league_key}/` is keyed by
  league, not user. Required before any shared deployment; not urgent for local use.
- **Deployment configuration** — Dockerfile, fly.toml, secrets handling. Blocked on
  feature pages being migrated first.
- **`matchups.py` re-fetch bug** — cosmetic parquet bloat; not urgent.
- **DECISIONS.md housekeeping** — Tech Lead to ratify three implicit decisions from audit 001
  (shared route helpers, per-stat cache loop, web-layer demo route pairing) and add `Revisit if`
  clauses to existing entries. Prerequisite before the next architectural-surface ticket.

---

_Last updated: 2026-05-30. The PM maintains this file during scoping and product reviews._
