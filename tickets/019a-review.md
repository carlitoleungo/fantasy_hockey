## Code Review — 019a

**Files reviewed:**
- `web/routes/waiver.py` — new helpers and POST handlers added
- `web/templates/waiver/_table.html` — new HTMX fragment (untracked new file)
- `tests/test_waiver.py` — new test file, 13 tests (untracked new file)

---

### Scope: CLEAN

The diff is strictly contained to the three files listed in `Touches`. No unrelated files were modified. The Engineer self-noted the `_is_rate_stat` private-import flag per the ticket's own instruction — no action required until `projection.py` is next touched. No "while I'm here" cleanup was introduced.

---

### Architecture: CLEAN

Checked all architecture invariants:

- **Framework imports in `data/`, `analysis/`, `auth/`:** None introduced by this diff. The pre-existing lazy `import streamlit` lines in `auth/oauth.py` are unrelated to this ticket.
- **Per-entity Yahoo API loop:** `fetch_season_pool` is called once per *stat*, not once per *player*. This is correct — the ticket spec explicitly prescribes the per-stat cache loop pattern, and no bulk alternative exists for this API surface.
- **Raw `stat['value']` without `_coerce()`:** Not present — the new code operates on already-coerced DataFrames returned from `fetch_season_pool`.
- **Yahoo array without `_as_list()`:** Not applicable — no raw Yahoo XML/dict parsing in the new code.
- **Missing demo counterpart:** The new live-data function (`_waiver_post_impl`) is a route-layer helper, not a `data/` function. The ticket's "Out of scope" clause explicitly confines all `data/`, `analysis/`, and `auth/` changes. `data/demo.py` already has `load_season_pool()` and `get_stat_categories()` — no new `data/` functions were added.
- **DECISIONS.md conformance:**
  - *HTMX fragment pattern (2026-04-19):* `_table.html` is the fragment swapped into `#waiver-table-container` in the shell. `hx-include="#waiver-filters"`, `hx-target="#waiver-table-container"`, and `hx-post="{{ form_action }}"` on pagination buttons all match the established convention. Shell IDs (`waiver-filters`, `waiver-table-container`) confirmed present in `web/templates/waiver/index.html`.
  - *League context (2026-04-19):* `league_key` resolved via `require_user` → `_get_league_key(db, current_user.session_id)`. Route is bare (`/api/waiver/players`, not `/leagues/{key}/...`). Fully conformant.
- **Implicit-decision drift:** No new directories, template-naming patterns, or session-handling conventions introduced. The `_waiver_post_impl` shared-helper pattern follows the existing `_get_league_key` helper convention already established in `web/routes/overview.py`.

---

### Issues

- **nit:** `cats = demo_module.get_stat_categories()` on line 161 is a dead assignment in the demo branch. `name_to_id` and `id_to_name` are only constructed in the `else` branch, and the demo path skips the per-stat loop entirely. The line is harmless (the Engineer noted it in the handoff) and the ticket spec prescribed fetching it, but the variable goes unused. Logged to `docs/improvements.md` for removal when `waiver.py` is next touched — not a blocker.

---

### Verification adequacy

All 5 acceptance criteria have direct test coverage in `tests/test_waiver.py`:

| AC | Test(s) |
|----|---------|
| AC1 (empty stats → empty state, no `<table>`) | TC1 |
| AC2 (stats=["Goals"] → table; cache-hit skips API) | TC2, TC7 |
| AC3 (no cookie → 302) | TC3 |
| AC4 (demo POST → 200, no Yahoo calls, no cache writes) | TC4, TC9 |
| AC5 (pagination: page=0 ≤25; page=1 next slice; page=99 clamped) | TC5, TC6 |

Four `_merge_pool` unit tests cover the core DataFrame-merge invariants. TC8 covers the missing-columns guard (position=G on a C-only pool → empty result, no 500).

QA's manual verification confirmed:
- Empty-state (no stats) via curl on the demo route
- Unauthenticated POST → 302 via curl
- Template attribute review (`hx-include`, `hx-post`, `hx-target`, `hx-vals`) confirmed correct

The AC3 ticket wording says "401" but implementation correctly returns 302 (consistent with `RequiresLogin → RedirectResponse("/auth/login")` used everywhere else). This is a ticket documentation error, not a code defect — noted and correctly handled by QA. No action required from Engineer.

The browser HTMX round-trip (no full-page reload, filter-state preservation) is owner-must-verify; the test-environment constraint is documented and pre-existing.

---

### Beginner-friendliness

No concerns. `_waiver_post_impl` is a straightforward helper function, not an abstraction — it reads top-to-bottom: set form action, handle empty stats, branch on demo, per-stat cache loop, filter, rank, paginate, return template. The `kwargs`-only `demo`, `session`, `league_key` parameters are explicit and well-named. No inverted control flow, no thread-local state, no new dependencies introduced.

---

### Verdict: APPROVED

The implementation meets all acceptance criteria, conforms to the HTMX fragment pattern and league context decisions, stays within scope, and has solid test coverage. One dead variable (`cats` in demo branch) logged to `docs/improvements.md` — not blocking.
