# Roadmap — Fantasy Hockey Waiver Wire

Likely near-term work, in rough priority order. This is a **pressure-test tool, not a
commitment** — the PM reads it during scoping to ask "does this ticket's approach still
make sense if these land?"

Keep it to ~3–7 items. If it grows past that, it's stopped being a pressure-test tool
and become a wishlist — prune.

---

## Next up

1. **025 — Parameterize overview nav links** (`Process: light`) — pass
   `head_to_head_url` and `overview_url` context variables from the four overview
   handlers; templates use `{{ ... }}`. Merges former tickets 025 + 026 (same root
   cause, same fix pattern).
2. **027 — Test demo overview routes** — unit/integration tests covering demo overview
   and head-to-head routes.
3. **Week projection migration** — most data-intensive page; tackle after 025/027 land.
   Expect 3–4 tickets (data layer, UI, demo parity).
4. **Demo mode snapshot tooling** — `data/demo.py` snapshot generation script and fixture
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

_Last updated: 2026-07-02. The PM maintains this file during scoping and product reviews._
