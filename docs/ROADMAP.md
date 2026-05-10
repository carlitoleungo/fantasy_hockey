# Roadmap — Fantasy Hockey Waiver Wire

Likely near-term work, in rough priority order. This is a **pressure-test tool, not a
commitment** — the PM reads it during scoping to ask "does this ticket's approach still
make sense if these land?"

Keep it to ~3–7 items. If it grows past that, it's stopped being a pressure-test tool
and become a wishlist — prune.

---

## Next up

1. **019a — Waiver wire POST handler (season path)** — core request/response cycle;
   fetches or cache-hits the player pool, ranks it, paginates it, returns an HTMX
   fragment; includes demo mode. Ticket is `ready`.
2. **019b — Waiver wire: last-30 branching + games remaining** — extends 019a with the
   Last 30 days stat period and a games-remaining column. Blocked on 019a.
3. **Audit checkpoint** — due after 019b ships (5-ticket audit cadence: last audit
   checkpoint ran around ticket 013/014; count the non-audit tickets since then).
4. **Week projection migration** — most data-intensive page; tackle after waiver wire is
   stable and the HTMX fragment pattern is validated under load.
5. **Demo mode snapshot tooling** — `data/demo.py` snapshot generation script and fixture
   data. 019a/b use `demo_module` stubs; this ticket produces the real snapshotted dataset
   so the public demo URL serves real numbers.

## Watching (maybe, not soon)

- **Per-user cache storage migration** — current `/data/cache/{league_key}/` is keyed by
  league, not user. Required before any shared deployment; not urgent for local use.
- **Deployment configuration** — Dockerfile, fly.toml, secrets handling. Blocked on
  feature pages being migrated first.
- **`matchups.py` re-fetch bug** — cosmetic parquet bloat; not urgent.

---

_Last updated: 2026-05-10. The PM maintains this file during scoping and product reviews._
