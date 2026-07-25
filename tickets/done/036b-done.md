# Implementation complete — 036b

**What I did:**
- Adopted `shell_context()` from `web/routes/common.py` in every full-page handler branch
  of `overview.py`, `waiver.py`, and `projection.py` — 12 context dicts in total, matching
  the count the ticket predicted.
- Authenticated handlers pass the user already resolved by `require_user`:
  `**shell_context(current_user, league_name=selected_league_name)`. No second cookie/DB
  lookup was introduced (DECISIONS 2026-07-03).
- Demo handlers pass `**shell_context(None, demo=True, league_name="Demo League")`.
- Deleted all 12 explicit `selected_league_name` keys and threaded the value through the
  helper instead. In every dict literal the `**shell_context(...)` spread is the **last**
  entry, so nothing can overwrite it — the silent-blanking trap the ticket warned about.
- Left every fragment handler untouched (`overview/_table`, `overview/_head_to_head_table`,
  `waiver/_table`, `projection/_matchup`) — those templates do not extend `base.html`.
- Deleted `tests/test_nav_shell_qa.py::test_demo_pages_still_render_default_authenticated_nav`
  (036a's deliberate before-state tripwire) and replaced it with the 036b after-state
  assertions in the same file.

**Files changed:**
- `web/routes/overview.py` — `shell_context` import; 8 context dicts migrated across 4
  full-page handlers (`overview`, `head_to_head`, `demo_overview`, `demo_head_to_head`),
  covering both the empty-state and populated branch of each.
- `web/routes/waiver.py` — `shell_context` import; `waiver_shell` (auth) and
  `demo_waiver_shell` (demo) migrated.
- `web/routes/projection.py` — `shell_context` import; `projection_shell` (auth) and
  `demo_projection_shell` (demo) migrated.
- `tests/test_nav_shell_qa.py` — removed the 036a tripwire; added the 036b nav coverage
  (21 new parametrised cases) reusing that file's existing `<nav>`- and `<header>`-scoped
  helpers. Put here rather than in a new file deliberately: `docs/improvements.md` has an
  open item about the `_make_db`/`ctx` scaffolding already being copied five times, and a
  new file would have made it six.

**Note on `/demo/overview/head-to-head`:** the ticket's AC text names three demo pages, but
`overview/head_to_head.html` also extends `base.html` and the ticket's Notes say to cover
*each* full-page branch. I migrated it too and included it in the test coverage. Flagging
it explicitly because it is broader than the AC's literal wording.

**Acceptance criteria status (self-check):**
- [x] AC1: demo header nav points at demo counterparts; clicking any stays in demo mode
  (200, never 302→`/auth/login`). Evidence: walked on a live `uvicorn web.main:app`
  (port 8931). From each of `/demo/overview`, `/demo/waiver`, `/demo/projection`,
  `/demo/overview/head-to-head`, every nav link was followed: Overview→`/demo/overview` 200,
  Waiver→`/demo/waiver` 200, Projection→`/demo/projection` 200. Also asserted by
  `test_demo_pages_render_demo_nav` and `test_demo_nav_links_stay_in_demo_mode`.
- [x] AC2: no "Logout" on demo pages; an exit/login affordance is present instead.
  Evidence: live walk showed `/auth/logout` absent from the entire page body on all four
  demo pages, and `Log in with Yahoo → /auth/login` present in each nav. Asserted by
  `test_demo_pages_render_demo_nav` (exact nav-link equality plus a whole-body check that
  `/auth/logout`, `/overview`, `/waiver`, `/projection` appear nowhere).
- [x] AC3: authenticated `/overview`, `/waiver`, `/projection` nav unchanged — Overview,
  Waiver, Projection, Logout in roadmap order, all 200. Evidence:
  `test_authenticated_feature_pages_render_authenticated_nav` asserts exact nav-link
  equality against `AUTHENTICATED_NAV` (which encodes the roadmap order) plus the header
  league label; `test_authenticated_nav_links_return_200` walks all three links.
  **Verified by mocked route tests only, not by a live browser session** — see Known
  limitations.
- [x] AC4: `.venv/bin/python -m pytest tests/` green including the demo-vs-authenticated
  nav-difference assertion. Evidence: `437 passed` (command output below). The difference
  assertion is `test_demo_nav_differs_from_authenticated_nav`: `/demo/overview` contains
  `href="/demo/waiver"` and no bare `href="/waiver"`; authenticated `/overview` contains
  `href="/waiver"` and no `href="/demo/waiver"`.

**How to verify (for QA):**
1. `.venv/bin/python -m pytest tests/` → expect `437 passed`.
2. Demo walk (no auth needed): `.venv/bin/python -m uvicorn web.main:app --port 8000`, then
   from `/demo/overview` click each header link. Each lands on the `/demo/*` counterpart
   with 200; no Logout link anywhere; "Log in with Yahoo" is the exit affordance; the
   header reads "Fantasy Hockey · Demo League". Repeat from `/demo/waiver`,
   `/demo/projection`, `/demo/overview/head-to-head`.
3. Confirm the demo pages' HTMX interactions still work (week selector on
   `/demo/overview`, filter form on `/demo/waiver`, team selector on `/demo/projection`) —
   fragment handlers were not touched, so a swapped fragment must still contain no
   `<header>`/`<nav>`.
4. Authenticated walk (needs a real Yahoo session + ngrok per `RUNNING.md`): log in, select
   a league, then check `/overview`, `/waiver`, `/projection`. Nav must be Overview /
   Waiver / Projection / Logout, all 200, and the header must still show the selected
   league name.
5. Mutation probes I ran, worth re-running if you want the guards proven:
   - In `demo_waiver_shell`, move `"selected_league_name": "Demo League"` back as an
     explicit key before `**shell_context(None, demo=True)` → exactly
     `test_demo_pages_header_keeps_demo_league_label[/demo/waiver]` fails (1 failed, 436
     passed). This is the silent-blanking trap; the guard catches it.
   - In `projection_shell`, change `shell_context(current_user, ...)` to
     `shell_context(None, ...)` → `test_authenticated_feature_pages_render_authenticated_nav[/projection]`
     and the pre-existing `test_projection_nav_link_present_and_after_waiver` fail
     (2 failed, 435 passed).
   Both mutations were reverted; the suite is green at 437 passed on the code as handed off.

**Scope notes:**
- `web/templates/base.html` and `web/templates.py` needed **no** changes — 036a's
  conditional nav and its authenticated default were sufficient. Nothing to escalate.
- `tests/test_overview_routes.py::test_overview_renders_authenticated_nav_by_default` (TC9)
  still passes, but its comment ("/overview has not adopted shell_context yet, so base.html
  must fall back to the authenticated nav") is now stale — `/overview` *has* adopted the
  helper, and the test now proves the explicit `is_authenticated=True` path rather than the
  default path. The assertions remain correct and valuable for AC3, so I left them; the
  comment is outside my `Touches` and the ticket mandated only one test deletion. Worth a
  one-line comment fix in whichever ticket next touches that file.
- Not built, correctly out of scope: the "Try the demo" home-page entry point. With this
  ticket landed, a visitor can navigate *within* demo mode but still has no linked way *in*
  from `/`. That follow-up is now the last gap in the demo journey.

**Improvements items closed:**
- None. This ticket was not scoped from a `docs/improvements.md` item (its Why cites the
  demo nav gap directly). 036a closed the related "Nav header shows auth links to
  unauthenticated visitors" item.

**Open improvements items on files I touched — read before QA:**
- `web/routes/projection.py` — **"Goalie breakdown table omits the shared offense
  categories (Assists)"** is `Type: quality`, and the Engineer rule says to fix quality
  items on files I modify. **I deliberately did not fix it, and I want that decision
  reviewed rather than assumed.** The item's own text says it "is a product call, not a
  defect", that ticket 034 "explicitly prescribed the `stat_group` partition and sanctioned
  the two-table option", and that "PM may promote this to a ticket if the owner wants
  goalie assists back". Fixing it would change projection *output* — nothing to do with
  nav — on a ticket whose entire diff is context-dict plumbing. Guessing at a product call
  is the thing I'm told not to do, so I'm surfacing it: if the owner wants goalie assists
  back, it needs its own ticket.
- `web/routes/overview.py` — two `Type: bug` items (leaderboard all-zero rows when a week
  has no activity; tied "worst" cells missing `bg-red-100`). Not fixed; out of scope per
  the Engineer rule on bug items.
- `web/routes/waiver.py` — `Type: bug` "League settings and stat categories re-fetched from
  Yahoo on every request" lists this file among its call sites. Not fixed; out of scope.

**Known limitations / things I couldn't fully test:**
- **The authenticated browser walk was not performed.** It needs a live Yahoo OAuth session
  over ngrok, which I have no credentials for in this environment. AC3 is covered by mocked
  route tests that assert the exact nav link set, order, and header league label for all
  three authenticated pages — but a human should still do step 4 above before this ships.
- The demo walk was driven by HTTP requests against a real uvicorn server, not by a
  clicking browser. That verifies status codes, link targets, and rendered header markup;
  it does not verify visual layout or CSS. The ticket forbids restyling, and the header
  markup is byte-identical to before apart from the link set, so I judged a visual pass
  unnecessary — but I did not do one.
- Demo data comes from the committed `demo/data/` snapshot. If that snapshot were missing
  or malformed the demo pages would fail before nav is reached; it is present and all four
  demo pages returned 200.
