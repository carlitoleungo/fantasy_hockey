# Roadmap — Fantasy Hockey Waiver Wire

Likely near-term work, in rough priority order. This is a **pressure-test tool, not a
commitment** — the PM reads it during scoping to ask "does this ticket's approach still
make sense if these land?"

Keep it to ~3–7 items. If it grows past that, it's stopped being a pressure-test tool
and become a wishlist — prune.

---

## Next up

1. **024 — Audit checkpoint** — Reviewer reads tickets 020, bug-week23, 021, 022, 023 end-to-end. Mandatory before 025/026.
2. **025 — Fix "Back to Leaderboard" link** — pass `overview_url` from both `head_to_head` and `demo_head_to_head` handlers; use `{{ overview_url }}` in `head_to_head.html`. Blocked on 024.
3. **026 — Fix "Compare two teams" link in demo leaderboard** — pass `head_to_head_url` from both `overview` and `demo_overview` handlers; use `{{ head_to_head_url }}` in `index.html`. Blocked on 024. Can run in parallel with 025.
4. **Week projection migration** — most data-intensive page; tackle after demo coverage is
   complete and the HTMX fragment pattern is fully validated across all existing pages.
5. **Demo mode snapshot tooling** — `data/demo.py` snapshot generation script and fixture
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

_Last updated: 2026-05-31. The PM maintains this file during scoping and product reviews._
