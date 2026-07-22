# Key Decisions Log — Superseded entries (archive)

> **Archived — current FastAPI stack.** These decision entries were superseded by later
> entries and moved out of [`docs/DECISIONS.md`](../DECISIONS.md) to keep the active log
> lean (it is read on every persona spawn). Each entry names the active decision that
> replaced it. This file is historical context only — never cite it as current guidance;
> cite the superseding entry in `DECISIONS.md` instead. For Streamlit-prototype decisions,
> see [`prototype-decisions.md`](prototype-decisions.md) in this directory.

---

### Feature pages: HTMX fragment pattern with shell + fragment template split (2026-04-19)

*Superseded 2026-05-30 by the entry of the same title in `DECISIONS.md` (a factual error was corrected — "015 (head-to-head)" should read 015 leaderboard / 016 head-to-head — and a `Revisit if` clause was added).*

Per scoping brief `013` Decision 1. Each feature page is split into `web/templates/<feature>/index.html` (full-page shell: layout, filter controls, initial state) plus one or more fragment templates (e.g. `_table.html`) returned by separate route handlers. Filter controls use `hx-get` / `hx-post` with `hx-target` to swap only the fragment — not the whole page. Chosen over full-page re-render (Option A) because waiver wire's per-(position, stat) lazy-loading requires fragment fetches anyway, and over Alpine-side filtering (Option C) because the hybrid "is this filter client or server?" mental model is not worth the perceived-UX gain and waiver wire's player pool is too large to preload. This also matches ARCHITECTURE.md Key patterns #5. Ticket 014 is the first page to establish the convention; 015 (head-to-head) and the waiver wire ticket inherit it.

---

### matchups.py: current week is included in delta fetch; won't refresh mid-week (2026-03-03)

*Superseded 2026-05-31 by "matchups.py: current_week always re-fetched to reflect intra-week stats" in `DECISIONS.md` — the `bug-week23-all-zeroes` fix changed this behaviour; `current_week` is now always re-fetched on every call.*

`get_matchups()` fetches up to and including `current_week`. Once that week is cached, the next call finds `last_cached_week == current_week` and fetches nothing new until Yahoo advances `current_week`. Intra-week stat updates are therefore not reflected until the cache is manually cleared. This is acceptable for a daily-use tool; a `force_refresh` flag can be added later if needed.

**Revisit if:** Users report stale intra-week data as a real problem (e.g. mid-week trade or injury decisions), at which point a `force_refresh` query parameter or a time-based TTL on the current week's cache entry should be added.
