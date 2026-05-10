# Roadmap — Fantasy Hockey Waiver Wire

Likely near-term work, in rough priority order. This is a **pressure-test tool, not a
commitment** — the PM reads it during scoping to ask "does this ticket's approach still
make sense if these land?"

Keep it to ~3–7 items. If it grows past that, it's stopped being a pressure-test tool
and become a wishlist — prune.

---

## Next up

1. **Ticket 014 — Nav shell in base.html** — prep before the first feature page; adds
   the minimal shared header (app name, league label, logout) so ticket 015 isn't
   carrying three first-time conventions at once.
2. **Ticket 015 — Weekly leaderboard view** — first feature page on the new stack;
   establishes the shell/fragment template split and the `rank_color` Jinja filter
   that waiver wire and projection will inherit.
3. **Ticket 016 — Head-to-head comparison view** — second view on the overview page;
   reuses patterns from 015, adds no new conventions.
4. **Waiver wire migration** — the main attraction; heavy filter + lazy-load surface.
   Validates whether ticket 015's shell/fragment split holds under a harder case.
5. **Demo mode port** — unlocks a public demo URL; conditional data loading
   (`data/demo.py` instead of `data/client.py`) wrapped around the new route handlers.
6. **Week projection migration** — most data-intensive page; tackle after simpler pages
   have validated the UI patterns. Underlying data layer also incomplete (see backlog).

## Watching (maybe, not soon)

- **Per-user cache storage migration** — current `.cache/{league_key}/` is keyed only by
  league, not user. Fine for single-user local use; required before any shared deployment.
- **Deployment configuration** — Dockerfile, fly.toml, secrets handling. Blocked by
  feature pages being migrated first.
- **`matchups.py` re-fetch bug fix** — cosmetic parquet bloat; not urgent.

---

_Last updated: 2026-04-19. The PM maintains this file during scoping and product reviews._
