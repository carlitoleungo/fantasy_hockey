## Code Review — 016

**Files reviewed:**
- `web/routes/overview.py` — head-to-head shell and fragment handlers added; `stat_columns` duplication fixed in existing handlers
- `web/templates/overview/head_to_head.html` — new shell template
- `web/templates/overview/_head_to_head_table.html` — new fragment template
- `web/templates/overview/index.html` — "Compare two teams →" in-page link added
- `tests/test_head_to_head_routes.py` — new test file (11 tests)
- `docs/improvements.md` — `stat_columns` duplication item closed
- `reference/waiver_wire_helper_refactor.ipynb` — credential scrub (see note below)

**Note on notebook change:** The `reference/waiver_wire_helper_refactor.ipynb` diff in this
commit is an owner-applied hotfix made outside the ticket workflow — real Yahoo OAuth
credentials that had been committed in the notebook's initial commit were replaced with
placeholder values. This change is not part of the ticket scope and was not authored by the
Engineer. It is recorded here for completeness. The credential rotation was completed
separately (2026-05-30).

---

### Scope: CLEAN

All Engineer changes are within the ticket's `Touches` list. The `docs/improvements.md`
update closes the `stat_columns` duplication item from ticket 015 — explicitly permitted
per the "improvements.md close-out" allowance. The notebook change is owner-authored and
out of scope for this review.

---

### Architecture: CLEAN

- No framework imports in `data/`, `analysis/`, or `auth/`.
- No per-entity Yahoo API loops — `get_matchups` is a single bulk fetch.
- No raw `stat['value']` access — all stat data flows through the existing `data/` layer.
- No new `data/` functions introduced — no demo counterpart required. Demo mode for
  head-to-head is explicitly deferred to a follow-up ticket.
- DECISIONS.md conformance:
  - *HTMX fragment pattern (2026-04-19):* shell (`head_to_head.html`) + fragment
    (`_head_to_head_table.html`) split; `hx-get="/overview/head-to-head/table"`,
    `hx-target="#head-to-head-table"`, `hx-trigger="change"` on the form. Conforms.
  - *League context (2026-04-19):* `league_key` resolved from session via `require_user`;
    route is bare (`/overview/head-to-head`, not `/leagues/{key}/...`). Conforms.
- No new implicit conventions introduced.

---

### Issues

- **should-fix (logged to `docs/improvements.md`):** No demo route for
  `/overview/head-to-head`. Unauthenticated visitors in demo mode hit a login redirect.
  The waiver wire pages (tickets 018/019a/019b) do have demo counterparts; the overview
  section does not. A follow-up ticket should add `/demo/overview` and
  `/demo/overview/head-to-head` routes backed by `data.demo.get_matchups()`.

- **nit:** Team names with spaces are not covered by any test fixture. QA noted the logic
  is correct by inspection (HTML `value` attribute → browser URL encoding → FastAPI query
  param decoding), but there is no automated exercise of this path. Low risk for v1.

---

### Verdict: APPROVED

All acceptance criteria pass per the QA report (300/300 tests). Architecture rules
followed. The `stat_columns` duplication fix from `docs/improvements.md` is a clean
close-out. The demo mode gap for head-to-head is a known deferral, not a regression.
