## Code Review — 021

**Files reviewed:**
- `web/routes/overview.py` — demo shell and fragment handlers added on `public_router`; `table_url` added to authenticated handler contexts
- `web/templates/overview/head_to_head.html` — `hx-get` target parameterised via `{{ table_url }}`

### Scope: CLEAN

Both changed files are listed in `Touches`. The template change is exactly what the ticket anticipated ("read-only — no change expected, but verify"). The authenticated handlers receive `table_url` in their context dicts — a minimal, necessary fix to make the template work after the parameterisation; this is inside the ticket's scope (the ticket's Notes for the Engineer explicitly called out checking the `hx-get` target and adding `table_url`). No "while I'm here" changes outside `Touches`.

### Architecture: CLEAN

- Demo handlers are registered on `public_router`, consistent with the pattern established by ticket 020 and the `web/routes/waiver.py` demo routes. Conforms to ARCHITECTURE.md key pattern #3.
- `data.demo` is imported inline inside each demo handler (not at module level), matching the established demo route pattern.
- No framework imports (`fastapi`, `streamlit`) in `data/`, `analysis/`, or `auth/`.
- No per-entity Yahoo API loop — demo handlers call `demo_module.get_matchups()` which loads a static parquet file.
- `simulate()` and `tally()` from `analysis/matchup_sim.py` are called directly from the route handler; no service layer introduced. Conforms to ARCHITECTURE.md pattern #4.
- HTMX shell + fragment split maintained (shell at `/demo/overview/head-to-head`, fragment at `/demo/overview/head-to-head/table`). Conforms to DECISIONS.md 2026-05-30 fragment pattern entry.
- No new implicit decisions or conventions that would require a DECISIONS.md entry.

### Issues

- **nit:** The `not_enough_data` empty-state branch in `demo_head_to_head` passes `"weeks": []` but the template only uses `weeks` in the `{% else %}` branch (i.e. when `not_enough_data` is False). Passing an empty list is harmless but slightly inconsistent with the authenticated handler's empty-state branch, which passes the same. No action required.

### Diff note — apparent duplicate parameter

The diff provided to the Reviewer showed a duplicate `team_a: str` parameter in `demo_head_to_head_table`. The actual file on disk (`web/routes/overview.py` lines 344–350) has the correct signature (`team_a: str, team_b: str, from_week: int, to_week: int, request: Request`) — a transcription artifact in the diff, not a real defect. QA's full suite of 345 tests passing (including TC-D11 which exercises the fragment endpoint) confirms the code is correct.

### Improvements.md update

The open item "Compare two teams link hard-codes `/overview/head-to-head` in shared template" (source: Code review 020) noted that the fix should land in ticket 021 when `/demo/overview/head-to-head` exists. That route now exists but the fix was not included — correctly so, since `web/templates/overview/index.html` is not in this ticket's `Touches`. The item remains open and is now actionable; updated below.

### Verdict: APPROVED

One open improvements.md item updated to reflect that the prerequisite route now exists and the fix is unblocked.
