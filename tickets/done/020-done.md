## Implementation complete — 020

**What I did:**
- Added `public_router = APIRouter()` to `web/routes/overview.py` alongside the existing `router`
- Added `GET /demo/overview` shell route on `public_router`: loads demo matchups via `demo_module.get_matchups()`, passes data through `weekly_scores_ranked` and `stat_columns`, renders `overview/index.html` with `table_url="/demo/overview/table"`
- Added `GET /demo/overview/table?week=N` fragment route on `public_router`: same demo data path, renders `overview/_table.html`
- Updated `overview/index.html` to use `{{ table_url }}` instead of the hard-coded `/overview/table` string in the `hx-get` attribute; authenticated routes now pass `table_url="/overview/table"` in their context dicts
- Registered `overview_public_router` in `web/main.py` (imported as `overview_public_router`, added before `overview_router` in `include_router` calls)
- Closed the "Demo mode not reachable for `/overview`" improvements.md item (the `/overview/head-to-head` portion remains open as ticket 021)

**Files changed:**
- `web/routes/overview.py` — added `public_router`, `demo_overview`, `demo_overview_table` routes; added `table_url` context var to both authenticated route responses
- `web/templates/overview/index.html` — changed `hx-get="/overview/table"` to `hx-get="{{ table_url }}"` so demo and authenticated shells point at the correct fragment endpoint
- `web/main.py` — imported `overview_public_router` and registered it with `app.include_router`
- `docs/improvements.md` — closed the "Demo mode not reachable for `/overview` and `/overview/head-to-head`" open item (partial: `/overview` closed by this ticket; `/overview/head-to-head` remains for ticket 021)

**Acceptance criteria status (self-check):**
- [x] AC1: `GET /demo/overview` returns 200 and renders the leaderboard shell with week selector and stat table populated from `data.demo.get_matchups()` data — no Yahoo session required. — Confirmed: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/demo/overview` returned `200`; response HTML contains "Demo League", "Weekly Leaderboard", week options 1–14, and `hx-get="/demo/overview/table"`.
- [x] AC2: `GET /demo/overview/table?week=N` returns 200 and renders `overview/_table.html` fragment populated from demo data for the requested week. — Confirmed: `curl "http://localhost:8501/demo/overview/table?week=5"` returned `200` with `<tr>` rows containing team names and `bg-green-100` rank cells.
- [x] AC3: No outbound Yahoo API calls are made when hitting either demo route. — Confirmed: server log for both requests shows only `200 OK` lines; no `data/client.py` or `auth/oauth.py` imports are on the demo code path; `demo_module.get_matchups()` reads a local parquet file.
- [x] AC4: Navigating to `/demo/overview` and changing the week selector updates the table via HTMX (fragment swap fires against `/demo/overview/table`). — Confirmed via HTML inspection: `hx-get="/demo/overview/table"` is present on the `<select>` in the demo shell response. Full browser test requires a browser (not testable via curl); HTMX wiring is correct.
- [x] AC5: An authenticated user visiting `/overview` still sees the live-data route unchanged. — Not testable without a real Yahoo login. The `router.get("/overview")` handler is untouched except for the addition of `"table_url": "/overview/table"` to its context dict. The template change is backwards-compatible: the authenticated shell now passes `table_url` where it previously hard-coded the URL.

**Note on AC5 partial verification:** `GET /overview` without auth returns `302 → /auth/login` (confirmed: `curl -w "%{http_code} %{redirect_url}" http://localhost:8501/overview` returned `302 http://localhost:8501/auth/login`). The live-data path requires a real session and cannot be walked without Yahoo credentials.

**How to verify (for QA):**
1. `uvicorn web.main:app --reload --port 8501`
2. Without logging in, visit `http://localhost:8501/demo/overview` — page loads; "Demo League" in header; leaderboard table with team names and colored stat cells; week selector shows weeks 1–14
3. Change the week selector — table updates without full page reload; server log shows `GET /demo/overview/table?week=N`; no Yahoo API activity in logs
4. Visit `http://localhost:8501/overview` without logging in — confirm 302 redirect to `/auth/login`
5. (Requires Yahoo credentials) Log in and visit `http://localhost:8501/overview` — confirm live leaderboard still loads correctly

**Scope notes:**
- `/demo/overview/head-to-head` is out of scope for this ticket (per ticket's Out of Scope section); tracked in ticket 021

**Known limitations / things I couldn't fully test:**
- AC4 (HTMX week-change swap) verified by HTML inspection only; full in-browser interaction not tested
- AC5 (live `/overview` with real Yahoo session) not testable without Yahoo credentials
- `pyarrow` was not installed in the Python 3.11 environment that uvicorn uses. Installed it (`pip install pyarrow`) to unblock local verification. The same gap affects the existing `/demo/waiver` route. This is a pre-existing environment issue, not introduced by this ticket.
