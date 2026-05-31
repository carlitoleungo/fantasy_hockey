## Code Review — 020

**Files reviewed:**
- `web/routes/overview.py` — added `public_router`, `demo_overview`, `demo_overview_table`; `table_url` added to both authenticated context dicts
- `web/templates/overview/index.html` — `hx-get` changed from hard-coded string to `{{ table_url }}`
- `web/main.py` — `overview_public_router` imported and registered
- `docs/improvements.md` — "Demo mode not reachable for `/overview`" item partially closed

---

### Scope: CLEAN

All changed files are in the ticket's `Touches` list. The `docs/improvements.md` edit is the permitted partial close-out explicitly described in the Engineer's handoff. No other files were touched.

---

### Architecture: CLEAN

**`public_router` shape matches `waiver.py` exactly.**
`web/routes/waiver.py` declares `public_router = APIRouter()` at module level alongside `router = APIRouter()`. `overview.py` follows the identical pattern. Both demo shell routes use the inline `from data import demo as demo_module` import (matching the waiver template exactly). Neither demo route carries `Depends(require_user)` or `Depends(db_dep)`. The registration order in `web/main.py` mirrors the waiver pairing: public router registered before the authenticated router.

**`table_url` context variable — backward-compatible.**
Both authenticated handlers (`overview()` and `overview_table()`) already pass `table_url="/overview/table"`. The template's single occurrence of `hx-get="{{ table_url }}"` is the only reference to the fragment URL. The empty-data path in `overview()` also passes `table_url`. No code path renders the template without `table_url` in context. The change is fully backward-compatible; `overview_table()` is a fragment handler (never renders `index.html`) so it correctly does not receive `table_url`.

**No framework imports in `data/`, `analysis/`, or `auth/`.** The demo routes call `data.demo.get_matchups()`, `analysis.team_scores.weekly_scores_ranked`, and `analysis.team_scores.stat_columns` — all pure Python, no FastAPI/Streamlit imports introduced into those layers.

**No per-entity Yahoo API loop.** The demo routes make no Yahoo API calls at all.

**`data/demo.py` counterpart pre-existed.** `demo_module.get_matchups()` was in place before this ticket (ticket scope explicitly noted this). No new `data/` function was added without a demo counterpart.

**No new convention without a DECISIONS.MD entry.** The `table_url` pattern is an extension of the already-documented `form_action` pattern from the waiver routes. It does not establish a new convention requiring a separate entry — it is an instance of the existing HTMX shell+fragment split decision (2026-05-30) applied to a second shell. The demo route pairing policy (2026-05-30) is satisfied: `/demo/overview` ships alongside `/overview` (deferred from ticket 015, now paid back per policy).

---

### Issues

- **should-fix (logged to `docs/improvements.md`):** No automated tests cover `GET /demo/overview` or `GET /demo/overview/table?week=N`. The waiver demo routes have `test_demo_waiver_shell_returns_200` as a direct parallel; the same three tests should be added for the overview demo routes. Out of scope for this ticket — logged.

- **should-fix (logged to `docs/improvements.md`):** The "Compare two teams →" link in `web/templates/overview/index.html` line 11 hard-codes `/overview/head-to-head`. When the template is rendered under `/demo/overview`, that link sends the unauthenticated visitor to an auth-protected route, which redirects to login. This is a direct UX breakage introduced by sharing the template without a `head_to_head_url` context variable equivalent to `table_url`. The fix (pass `head_to_head_url` from both shells; update the `href`) should land in ticket 021 when `/demo/overview/head-to-head` is built. Logged to improvements.md rather than blocking here because ticket 021 is the natural place to resolve it, and the broken link is a consequence of the explicitly out-of-scope deferral.

No nits.

---

### Verification adequacy

QA exercised all five acceptance criteria with concrete curl observations. AC1 confirmed page structure including week selector with correct week count and default. AC2 confirmed fragment shape (no `<html>` wrapper), team names, stat columns, and `bg-green-100` cells. AC3 confirmed via log inspection and code reading that `data/demo.py` imports only `json`, `pathlib`, and `pandas`. AC4 confirmed HTMX attributes (`hx-get`, `hx-target`, `hx-trigger`) by HTML inspection; browser swap is correctly deferred to owner. AC5 confirmed redirect behavior by curl and structural code inspection of the authenticated handlers. Verification is adequate for the scope of this ticket.

---

### Verdict: APPROVED

Logged improvements:
1. `docs/improvements.md` — "No automated tests for `/demo/overview` and `/demo/overview/table` routes" (should-fix)
2. `docs/improvements.md` — "'Compare two teams' link hard-codes `/overview/head-to-head` in shared template" (should-fix; resolve in ticket 021)
