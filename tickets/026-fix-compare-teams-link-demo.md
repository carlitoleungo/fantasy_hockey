# 026 — Fix hardcoded "Compare two teams" link in demo leaderboard

## Status
ready

## Type
bug

## Touches
- web/templates/overview/index.html
- web/routes/overview.py

## Why
The "Compare two teams →" link in `web/templates/overview/index.html` is hardcoded to
`/overview/head-to-head`. The same template is rendered for both the authenticated
leaderboard (`/overview`) and the demo leaderboard (`/demo/overview`). An unauthenticated
visitor on `/demo/overview` who clicks "Compare two teams" is sent to
`/overview/head-to-head` — the authenticated route — and immediately redirected to Yahoo
login. There is effectively no way to reach `/demo/overview/head-to-head` from the demo
leaderboard, making the page unreachable through normal navigation.

## Acceptance criteria
- [ ] Visiting `/demo/overview` (no auth cookie), clicking "Compare two teams →" navigates to `/demo/overview/head-to-head` (not `/overview/head-to-head`)
- [ ] Visiting `/overview` (authenticated), clicking "Compare two teams →" navigates to `/overview/head-to-head`
- [ ] `web/templates/overview/index.html` uses `{{ head_to_head_url }}` rather than the literal `/overview/head-to-head` string
- [ ] Both the authenticated `overview` handler and the `demo_overview` handler pass `head_to_head_url` in their context dicts

## Out of scope
- Changes to `head_to_head.html` (covered by ticket 025)
- Fragment endpoints `overview_table` and `demo_overview_table` — the "Compare two teams" link is in the shell only, not the fragment
- Any other hardcoded links in the codebase

## Notes for the Engineer
- Same pattern as `table_url` (ticket 020) and `overview_url` (ticket 025): pass a
  context variable from the route handler; use `{{ variable }}` in the template.
- Authenticated handler: `overview()` at `web/routes/overview.py` — add
  `"head_to_head_url": "/overview/head-to-head"` to both the empty-state and normal return
  context dicts (lines ~53–84).
- Demo handler: `demo_overview()` at `web/routes/overview.py` — add
  `"head_to_head_url": "/demo/overview/head-to-head"` to both context dicts (~lines 229–265).
- Template change: `web/templates/overview/index.html` line 11 — replace
  `href="/overview/head-to-head"` with `href="{{ head_to_head_url }}"`.
- The fragment handlers (`overview_table`, `demo_overview_table`) do not render
  `index.html`, so they need no changes.
- This item was logged in `docs/improvements.md` under '"Compare two teams" link
  hard-codes `/overview/head-to-head` in shared template' (source: Code review 020,
  updated code review 021; unblocked by ticket 021 shipping the demo head-to-head route).

## Verification
1. Start the server: `uvicorn web.main:app --reload`
2. While logged out, visit `http://localhost:8000/demo/overview`. Confirm the page loads.
3. Click "Compare two teams →". Confirm the browser navigates to
   `http://localhost:8000/demo/overview/head-to-head` — not `/overview/head-to-head`.
4. Log in, visit `http://localhost:8000/overview`. Click "Compare two teams →". Confirm
   the browser navigates to `http://localhost:8000/overview/head-to-head`.
5. Confirm the leaderboard table fragment still loads and week switching still works.

## Dependencies
- Ticket 025 may be worked in parallel (touches different files); neither depends on the other
- Ticket 024 (audit checkpoint) must complete first
