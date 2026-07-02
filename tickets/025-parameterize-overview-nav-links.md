# 025 — Parameterize hardcoded navigation links in overview templates

## Status
done

## Type
bug

## Process
light

## Touches
- web/templates/overview/index.html
- web/templates/overview/head_to_head.html
- web/routes/overview.py

## Why
Two navigation links in the overview templates are hardcoded to authenticated routes,
and both templates are shared with demo mode — same root cause, same fix pattern, so
one ticket (merges former tickets 025 and 026):

1. "Compare two teams →" in `index.html` points at `/overview/head-to-head`. An
   unauthenticated visitor on `/demo/overview` who clicks it is sent to the
   authenticated route and bounced to Yahoo login — `/demo/overview/head-to-head`
   (shipped in ticket 021) is unreachable through normal navigation.
2. "← Back to Leaderboard" in `head_to_head.html` points at `/overview`. Demo visitors
   who reach `/demo/overview/head-to-head` are bounced to login on the way back.

## Acceptance criteria
- [ ] On `/demo/overview` (no auth cookie), clicking "Compare two teams →" navigates to `/demo/overview/head-to-head` (not `/overview/head-to-head`)
- [ ] On `/demo/overview/head-to-head` (no auth cookie), clicking "← Back to Leaderboard" navigates to `/demo/overview` (not `/overview`)
- [ ] Authenticated: on `/overview`, "Compare two teams →" still navigates to `/overview/head-to-head`
- [ ] Authenticated: on `/overview/head-to-head`, "← Back to Leaderboard" still navigates to `/overview`

## Out of scope
- Fragment endpoints (`overview_table`, `demo_overview_table`) — both links live in the
  shell templates only, so the fragment handlers need no changes
- Any other hardcoded links in the codebase
- Waiver or non-overview templates

## Notes for the Engineer
- Implementation shape: identical to the `table_url` pattern from tickets 020/021
  (`web/routes/overview.py` lines 150–152, 307–310) — the handler passes a URL context
  variable; the template uses `{{ variable }}` instead of a literal path.
- `index.html` line 11: replace `href="/overview/head-to-head"` with
  `href="{{ head_to_head_url }}"`. Handlers: `overview()` (~lines 53–84) passes
  `"/overview/head-to-head"`; `demo_overview()` (~lines 229–265) passes
  `"/demo/overview/head-to-head"`. Add to **both** context dicts in each handler
  (empty-state and normal branches).
- `head_to_head.html` line 8: replace `href="/overview"` with
  `href="{{ overview_url }}"`. Handlers: `head_to_head()` (~lines 142–178) passes
  `"/overview"`; `demo_head_to_head()` (~lines 302–339) passes `"/demo/overview"`.
  Both branches (`not_enough_data` and normal).
- Tests: add minimal assertions to the existing overview route tests — the demo shell
  bodies contain the demo URLs and not the authenticated ones, and vice versa. Follow
  the shape of `tests/test_demo_head_to_head_routes.py`. (Fuller demo overview coverage
  is ticket 027 — don't duplicate it.)
- When done, close the `docs/improvements.md` item '"Compare two teams" link hard-codes
  `/overview/head-to-head` in shared template'.

## Verification
1. Start the server: `uvicorn web.main:app --reload`
2. Logged out: visit `http://localhost:8000/demo/overview` → click "Compare two teams →"
   → lands on `/demo/overview/head-to-head` → click "← Back to Leaderboard" → lands on
   `/demo/overview`.
3. Logged in: `/overview` → "Compare two teams →" → `/overview/head-to-head` →
   "← Back to Leaderboard" → `/overview`.
4. The leaderboard table fragment still loads and week switching still works on both
   `/overview` and `/demo/overview`.

## Dependencies
- None
