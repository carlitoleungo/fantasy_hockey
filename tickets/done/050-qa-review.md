## QA + Review Report — 050 (Round 2 — re-verification after fix round)

**Ticket:** Error page body clips at phone width
**Engineer handoff:** tickets/050-fix.md (fix round); tickets/050-done.md (original)
**QA date:** 2026-09-17
**Process:** light (combined QA + review, no separate Reviewer session)

### Context

Round 1 (see prior report, now superseded by this file) raised exactly one blocker: AC1
(`px-4` container padding) had no automated test coverage. Everything else — the template
diff, scope boundaries, the asymmetric `docs/improvements.md` bookkeeping, and the
`scope="module"` fixture change — passed round 1. AC2 (375px visual check) was recorded as
owner-must-verify because the sandbox browser has no network egress (confirmed in round 1
via a real CDP connection to a cached Chromium where every `page.goto()` timed out,
including to `example.com`). This round re-verifies the blocker fix and re-confirms nothing
else regressed; AC2 is not re-investigated per instruction.

### Test plan for this round (written before reading `050-fix.md`'s "Verification" claims in detail)

- Confirm the new test the Engineer added actually guards the regression: temporarily strip
  `px-4` from `error.html`'s container myself, run the new test alone, expect an
  `AssertionError`; then restore the file and confirm `git diff` shows only the original
  one-line round-1 change.
- Diff every file the fix round could plausibly have touched
  (`web/templates/error.html`, `web/templates/base.html`, `docs/improvements.md`,
  `docs/archive/improvements-closed.md`, `tickets/050-error-page-mobile-padding.md`)
  against what round 1 already established, to confirm the fix round's diff is scoped to
  `tests/test_error_handling.py` only.
- Run `.venv/bin/python -m pytest tests/` and `tests/test_error_handling.py -v` myself and
  compare counts against the Engineer's claim (478 total, 8 in the file, +1 over baseline).
- Re-read the fixture and the "Back to home" link to confirm no drift from round 1's
  approved state (cheap re-confirmation, not redone from scratch).

### Test results

| # | Acceptance criterion | Result | Observation |
|---|----------------------|--------|-------------|
| 1 | `error.html`'s content container carries horizontal padding matching the other page shells (`px-4`) | **PASS — now automated** | `tests/test_error_handling.py::test_500_handler_content_container_has_horizontal_padding` asserts `'<div class="max-w-xl mx-auto mt-16 px-4 text-center">' in resp.text` against `/test/unhandled`. Ran alone: `1 passed`. Independently reproduced the regression-guard: stripped `px-4` from `error.html`'s container, reran the test, got `AssertionError` with the un-padded div shown in the failure diff (`assert '<div class="max-w-xl mx-auto mt-16 px-4 text-center">' in '...<div class="max-w-xl mx-auto mt-16 text-center">...'`). Restored the file; `git diff web/templates/error.html` afterward shows only the single round-1 line (`text-center` → `px-4 text-center`), byte-identical to round 1. |
| 2 | Rendering at 375px shows heading, detail text, and "Back to home" link fully inside the viewport, no horizontal page scroll | **owner-must-verify (unchanged from round 1)** | Not re-investigated this round per instruction. Round 1 exhausted the sandbox's browser options (real CDP connection established, but the browser process has no network egress — confirmed via `page.goto()` timeouts on both loopback and `https://example.com/`, zero network activity, no `requestfailed` events). This is an environment limitation, not a code defect, and is not something a fix round in this sandbox can close. Flag for whoever has real browser/device-emulation access before release. |
| 3 | Existing error-handling tests still pass unchanged | PASS | `.venv/bin/python -m pytest tests/test_error_handling.py -v` → `8 passed` (the original 7, unchanged, plus the 1 new test). |

### On the Engineer's reasoning for the stronger assertion

The fix-round handoff argues that a bare `"px-4" in resp.text` substring check (my round-1
suggested minimal form) would not actually guard the regression, because `base.html`'s
header already renders `border-b px-4 py-3` on every page including the error page — so
`px-4` is present in the response body regardless of whether the content container has it.

**This is correct, and I proved it directly rather than just accepting the argument.** When
I stripped `px-4` from the container during my reproduction above, the failure output showed
the full response body still containing `<header class="border-b px-4 py-3 ...">` — a bare
substring assertion on `"px-4"` would have passed against that same un-padded response. The
Engineer's choice to assert the exact container tag
(`<div class="max-w-xl mx-auto mt-16 px-4 text-center">`) instead of the substring is the
correct fix and closes the gap round 1 identified. My original suggestion, taken literally,
would have been a false-negative-prone test; the Engineer caught and fixed that, which is
better than what I asked for.

### Automated tests

- Command: `.venv/bin/python -m pytest tests/`
- Result: `478 passed, 109 warnings in 1.55s` — matches the Engineer's report exactly:
  baseline 477 + 1 new test, zero regressions elsewhere.
- Command: `.venv/bin/python -m pytest tests/test_error_handling.py -v`
- Result: `8 passed` — all 7 original tests plus
  `test_500_handler_content_container_has_horizontal_padding`, all green, correct names.
- New tests added this round: `tests/test_error_handling.py::test_500_handler_content_container_has_horizontal_padding`.
- AC1 coverage gap from round 1: **closed.**

### Scope check — fix round touched only `tests/test_error_handling.py`

Diffed every file that could plausibly have moved this round against round 1's already-approved
state:

- `web/templates/error.html` — diff is exactly the single round-1 line
  (`max-w-xl mx-auto mt-16 text-center` → `max-w-xl mx-auto mt-16 px-4 text-center`). No
  further change. Confirmed byte-identical to round 1's diff both before and after my
  strip/restore reproduction.
- `web/templates/base.html` — `git diff web/templates/base.html` returns no output. Untouched,
  as in round 1.
- **"Back to home" link** — `<a href="/" class="mt-6 inline-block text-sm text-gray-600
  hover:text-gray-800">Back to home</a>` is present in `error.html` unchanged, byte-for-byte,
  same as round 1. No restyling.
- `docs/improvements.md` — diff matches round 1 exactly: the fixture-scope item removed, the
  "Back to home" link item's entry gets the same `**Update (Ticket 050):**` note recorded in
  round 1, nothing added or altered this round.
- `docs/archive/improvements-closed.md` — diff matches round 1 exactly: the fixture-scope item
  added with the same resolution note as round 1.
- `tickets/050-error-page-mobile-padding.md` — only the `## Status` line changed
  (`ready` → `qa`), same as round 1; no AC or scope text touched.
- `git status --short` confirms the only file with new changes since round 1's approved
  state is `tests/test_error_handling.py` (plus the ticket artifacts `050-fix.md` /
  `050-qa-review.md`, which are process artifacts, not source).

**No scope expansion. The fix round did exactly what it said: one 3-line test addition to
one file.**

### Fixture (`scope="module"`) and asymmetric bookkeeping — re-confirmed, not redone

Re-read `tests/test_error_handling.py` in full this round (reproduced above) and re-diffed
the two improvements files. Both match round 1's approved state exactly:
- `scope="module"` is present on the `client` fixture (line 8), unchanged from round 1.
- The fixture-scope improvements item is closed (moved to
  `docs/archive/improvements-closed.md`) — correct, per the ticket's explicit instruction.
- The "Back to home" link-affordance item remains open in `docs/improvements.md` with the
  round-1 update note appended — correct, per the ticket's explicit instruction that this
  item must **not** close.

Not re-deriving the isolation analysis (no cross-test state leakage, no route-collision risk
across the 15 other modules importing `web.main.app`) from scratch — round 1 already did that
work and nothing in this round touched the fixture beyond adding a new test function that
uses the same fixture the same way as the other 7.

### Manual verification

Per the light-ticket QA workflow, AC1 and AC3 are now both covered by green tests I ran and
independently stress-tested myself (see reproduction above), so no hand-driven walk was
needed for either. AC2 has no automated coverage possible (rendering/viewport question) and
remains owner-must-verify per the round-1 sandbox investigation; not re-attempted this round
per explicit instruction.

### Demo mode

N/A — this ticket touches only a template and a test file, no `data/` function or route
logic. No demo-mode parity concern. (Unchanged from round 1.)

### Review checks (blocker checklist)

| Check | Result |
|---|---|
| Framework import in `data/`, `analysis/`, or `auth/` | Pass — not touched |
| Raw `stat['value']` without `_coerce()`; Yahoo collection without `_as_list()` | Pass — not applicable |
| Per-entity Yahoo API loop where a bulk endpoint exists | Pass — not applicable |
| New live data function with no demo counterpart | Pass — not applicable |
| Contradicts an active `docs/DECISIONS.md` entry | Pass — `base.html`'s `auth_state_unknown` branch (042, DECISIONS 2026-07-25) untouched this round; no contradiction |
| Diff escapes the ticket's `Touches` list | Pass — fix round touched only `tests/test_error_handling.py`, which is in `Touches`; the ticket status-line flip is standard bookkeeping |

Zero architectural/security blockers. Nothing about this diff smells mis-classified as
light — the fix round is a genuinely minimal, correctly-scoped test addition.

### Issues found

None. The round-1 blocker (missing AC1 coverage) is closed with a test I independently
verified guards the actual regression, including confirming the Engineer's stated reason for
preferring the stronger assertion over my round-1 suggested substring check.

### Notes

- AC2 stays **owner-must-verify**: this environment cannot render a page in an actual browser
  (confirmed twice now, round 1 and not re-attempted round 2 per instruction — no new
  information). Whoever has real device-emulation access should confirm no horizontal
  scroll / edge-clipping at 375px before or shortly after this ships. This does not block
  the verdict below per the ticket owner's explicit instruction that AC2 is not QA's to
  close in this sandbox.
- No new out-of-scope defects found this round.

### Verdict: APPROVED

Both rounds' evidence combined: AC1 now has automated coverage that I independently proved
guards the regression (fails without `px-4`, passes with it); AC3 is solidly green (478/478,
matching the Engineer's reported count exactly); the fix round did not expand scope beyond
`tests/test_error_handling.py`; all round-1 findings (template diff, base.html untouched,
"Back to home" link untouched, asymmetric improvements bookkeeping, fixture safety) hold
unchanged. Zero review blockers. AC2 remains owner-must-verify due to a sandbox environment
limitation (no browser network egress), not a code defect, and is explicitly out of scope
for this QA sign-off per the ticket owner's instruction.
