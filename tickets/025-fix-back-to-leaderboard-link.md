# 025 — Fix hardcoded "Back to Leaderboard" link in head_to_head.html

## Status
ready

## Type
bug

## Touches
- web/templates/overview/head_to_head.html
- web/routes/overview.py

## Why
The "Back to Leaderboard" link in `web/templates/overview/head_to_head.html` is hardcoded
to `/overview`. Since ticket 021 shipped `/demo/overview/head-to-head` using the same
template, unauthenticated visitors who reach the demo head-to-head page via
`/demo/overview/head-to-head` are sent to `/overview` when they click "Back to
Leaderboard" — the authenticated route, which immediately redirects them to Yahoo login.
The demo context needs a link back to `/demo/overview` instead.

## Acceptance criteria
- [ ] Visiting `/demo/overview/head-to-head` (no auth cookie), clicking "Back to Leaderboard" navigates to `/demo/overview` (not `/overview`)
- [ ] Visiting `/overview/head-to-head` (authenticated), clicking "Back to Leaderboard" navigates to `/overview`
- [ ] `web/templates/overview/head_to_head.html` uses `{{ overview_url }}` rather than the literal `/overview` string
- [ ] Both the authenticated `head_to_head` handler and the `demo_head_to_head` handler pass `overview_url` in their context dicts

## Out of scope
- Any other hardcoded links in the overview templates (tracked separately in `docs/improvements.md`)
- Changes to the waiver wire or any non-overview templates

## Notes for the Engineer
- The fix follows the identical pattern as `table_url` introduced in ticket 021
  (`web/routes/overview.py` lines 150–152, 307–310): the handler passes a context variable;
  the template uses `{{ variable }}` instead of a hardcoded path.
- Authenticated handler: `head_to_head()` at `web/routes/overview.py` — add
  `"overview_url": "/overview"` to its context dict in both the `not_enough_data` branch
  and the normal return (lines ~142–178).
- Demo handler: `demo_head_to_head()` at `web/routes/overview.py` — add
  `"overview_url": "/demo/overview"` to its context dict in both branches (~lines 302–339).
- Template change: `web/templates/overview/head_to_head.html` line 8 — replace
  `href="/overview"` with `href="{{ overview_url }}"`.
- This item was logged in `docs/improvements.md` under "Back to Leaderboard link
  hard-codes /overview" (source: Code review 020; unblocked by ticket 021).

## Verification
1. Start the server: `uvicorn web.main:app --reload`
2. While logged out, visit `http://localhost:8000/demo/overview/head-to-head`. Confirm the
   page loads.
3. Click "← Back to Leaderboard". Confirm the browser navigates to
   `http://localhost:8000/demo/overview` — not `/overview`.
4. Log in, visit `http://localhost:8000/overview/head-to-head`. Click "← Back to
   Leaderboard". Confirm the browser navigates to `http://localhost:8000/overview`.
5. Confirm no other page behaviour has changed.

## Dependencies
- Ticket 024 (audit checkpoint) must complete first
