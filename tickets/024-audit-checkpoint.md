# 024 — Audit checkpoint: tickets 020, bug-week23, 021, 022, 023

## Status
done

## Type
audit

## Touches
- .team/audits/024-audit.md

## Why
Five non-audit tickets have completed since audit 001 (020, bug-week23-all-zeroes, 021,
022, 023). Per the team's mandatory audit cadence, the Reviewer reads the last five
tickets' outputs end-to-end and produces an audit report before new feature work proceeds.

## Acceptance criteria
- [ ] `.team/audits/024-audit.md` exists and covers all five tickets: 020, bug-week23-all-zeroes, 021, 022, 023
- [ ] Each ticket's acceptance criteria are checked against the actual shipped code (not just the done note)
- [ ] Any patterns introduced that future tickets should know about are flagged for `docs/LEARNINGS.md` or `docs/DECISIONS.md`
- [ ] Open items are logged in `docs/improvements.md` (Reviewer's file) or surfaced to the PM as follow-up tickets

## Out of scope
- Fixing any issues found — flag them; the PM scopes follow-up tickets separately
- Tickets prior to 020 (covered by audit 001)

## Notes for the Engineer
- Audit 001 (`.team/audits/001-audit.md`) covers tickets 015, 016, 018, 019a, 019b — do not re-audit those
- The five tickets to cover:
  - **020** — Demo mode: `/demo/overview` leaderboard (`web/routes/overview.py`, `web/templates/overview/index.html`)
  - **bug-week23-all-zeroes** — Bug fix: week 23 all-zero rows
  - **021** — Demo mode: `/demo/overview/head-to-head` (`web/routes/overview.py`, `web/templates/overview/head_to_head.html`)
  - **022** — Logout confirmation (`web/routes/auth.py`, `web/templates/home.html`)
  - **023** — Optional-auth home page (`web/middleware/session.py`, `web/routes/home.py`, `web/templates/home.html`)
- Check for: demo parity completeness, cross-route URL hardcoding, test coverage gaps, DECISIONS.md entries from these tickets that should be ratified

## Verification
- Audit report at `.team/audits/024-audit.md` exists with findings for each of the five tickets
- PM reads the report and acts on any flagged items before ticket 025 begins

## Dependencies
- None — this ticket is the prerequisite for 025 and 026
