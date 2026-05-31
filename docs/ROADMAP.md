# Roadmap — Fantasy Hockey Waiver Wire

Likely near-term work, in rough priority order. This is a **pressure-test tool, not a
commitment** — the PM reads it during scoping to ask "does this ticket's approach still
make sense if these land?"

Keep it to ~3–7 items. If it grows past that, it's stopped being a pressure-test tool
and become a wishlist — prune.

---

## Next up

1. **025 — Fix "Back to Leaderboard" link** — pass `overview_url` from both `head_to_head` and `demo_head_to_head` handlers; use `{{ overview_url }}` in `head_to_head.html`.
2. **026 — Fix "Compare two teams" link in demo leaderboard** — pass `head_to_head_url` from both `overview` and `demo_overview` handlers; use `{{ head_to_head_url }}` in `index.html`. Can run in parallel with 025.
3. **027 — Test demo overview routes** — unit/integration tests covering demo overview and head-to-head routes.
4. **Week projection migration** — most data-intensive page; tackle after 025–027 land. Expect 3–4 tickets (data layer, UI, demo parity).
5. **Demo mode snapshot tooling** — `data/demo.py` snapshot generation script and fixture
   data refresh. The current demo dataset is static; this ticket produces tooling to regenerate
   it from a live season so the public demo URL serves current-looking numbers.

## Watching (maybe, not soon)

- **Per-user cache storage migration** — current `/data/cache/{league_key}/` is keyed by
  league, not user. Required before any shared deployment; not urgent for local use.
- **Deployment configuration** — Dockerfile, fly.toml, secrets handling. Blocked on
  feature pages being migrated first.
- **`matchups.py` re-fetch bug** — cosmetic parquet bloat; not urgent.

---

_Last updated: 2026-05-31. The PM maintains this file during scoping and product reviews._
