## Code Review — 032

**Files reviewed:**
- `web/routes/waiver.py` — `position: str` → `positions: list[str]` on both POST handlers and `_waiver_post_impl`; per-position fetch loop; union filter.
- `web/templates/waiver/index.html` — position radios → checkboxes with All/specific mutual-exclusivity handlers.
- `tests/test_waiver.py` — TC8 rename fix, 6 new AC/coverage tests, TC10 `>GR<` assertion.
- `docs/improvements.md` — TC10 quality item moved to `## Closed` (sanctioned close-out).
- `docs/backlog.md` — added deferred ranking-behaviour note (owner-accepted).

### Scope: CLEAN (with two out-of-Touches doc edits, assessed below)

The three code/test edits stay exactly inside `Touches` (`web/routes/waiver.py`, `web/templates/waiver/index.html`, `tests/test_waiver.py`) and match the required change shape in the ticket's Notes item-by-item. No bonus features, no unrelated cleanup in the code files.

Two files were modified outside the `Touches` list:
- `docs/improvements.md` — closes the "TC10 missing `>GR<`" quality item, which lives on `tests/test_waiver.py` (a touched file). This is the one sanctioned exception under both the Engineer persona (input #6) and my own persona (I curate this file). The `>GR<` assertion was actually added to the test, so the close is real, not clerical. Legitimate.
- `docs/backlog.md` — a deferred-item note for the pre-existing cross-position NaN-composite ranking issue in `analysis/waiver_ranking.py`. This is out of scope for 032 and correctly not fixed here. Strictly, backlog.md is PM-owned and this reads more like a `Type: bug`/quality item than a deferred feature, so improvements.md would have been the tidier home. The owner has reviewed and accepted it, so I am recording the observation rather than blocking on lane ownership. Not a behaviour change.

### Architecture: CLEAN

- **Layer purity:** all logic changes are in `web/`; no framework imports leak into `data/`, `analysis/`, or `auth/`. `analysis/waiver_ranking.py`, `data/cache.py`, `data/players.py`, `data/client.py` untouched, as the ticket's Out of scope demands.
- **Bulk vs per-entity:** the live branch loops `fetch_positions` (the selected positions, or `["All"]` when none) and calls `fetch_season_pool(..., position=api_position)` once per (position, stat) using the existing per-position cache keys `cache.*_player_pool(league_key, pos, stat)`. It does NOT collapse to a single "All" fetch when specifics are selected (`fetch_positions = selected if selected else ["All"]`), so sparse D/G pools are preserved per the ticket's top-25 rationale. This reuses the same bulk pool endpoint per position as before — no new per-entity call regression.
- **`filter_by_position` reuse:** the final union is `pd.concat([filter_by_position(base_df, p) for p in selected])` deduped on `player_key`, guarded by `if not selected or base_df.empty`. It calls the existing `filter_by_position`, which already splits composite `display_position` (e.g. `"C,LW"`) on comma — matching is not reimplemented. `_coerce`/`_as_list` are not in play here (no new Yahoo-response parsing; data flows through the unchanged fetch functions).
- **Demo parity:** `_waiver_post_impl` serves both live and demo; the union filter and normalization are shared, so demo parity is structural, not a separate code path. No new `data/` function was added, so no `data/demo.py` counterpart is required.
- **DECISIONS.md:** no conflict; ticket correctly flagged as non-architectural (no OAuth/cache/API-client/routing/shell changes). No new convention established.

### Security: CLEAN

- No secrets, tokens, session IDs, or PII touched or logged.
- Org rule (no client-side-only passwords): N/A — no passwords here. The JS All/specific mutual exclusivity is a UX convenience only; correctness does not depend on it, because the server independently normalizes with `selected = [p for p in positions if p and p != "All"]`, so an `All`+specific submission is handled correctly server-side.
- `positions: list[str] = Form([])` is validated at the HTTP boundary; unknown values fall through `filter_by_position` harmlessly (no eligible players match) and `"All"`/empty is normalized. No SQL, no cookie-attribute surface touched.

### Verification adequacy

All four ACs are covered by committed, non-trivial tests (both inclusion and exclusion assertions against a 6-player fixture spanning every group), plus the live per-position fetch-loop assertion (`mock_fetch.call_count == 2`, positions `{"C","LW"}`). QA independently exercised the real `/demo` routes across all pages against actual demo data. Full waiver suite re-run during this review: `25 passed`. The JS-click mutual-exclusivity toggle and pill styling remain owner-must-verify in a real browser (headless limit) — the rendered-markup and server-normalization behaviour is covered, so this is a visual confirmation, not a correctness gap.

### Issues
- **nit:** `docs/improvements.md` now has a doubled `---` separator (lines ~161–163) left where the TC10 block was lifted into `## Closed`. Cosmetic only; leaving it rather than editing outside this ticket's concern.
- **nit:** the ranking follow-up would sit more naturally in `docs/improvements.md` as `Type: bug` than in `docs/backlog.md`, but the owner has accepted the placement.

### Verdict: APPROVED

Clean scope, clean architecture, clean security. The per-position fetch loop and the `filter_by_position` union are implemented exactly as the ticket specified, with no bulk-endpoint regression and correct composite-position handling. Both out-of-Touches doc edits are sanctioned or owner-accepted. No improvements-tracker entries added by me (only the two nits above, both intentionally left).
