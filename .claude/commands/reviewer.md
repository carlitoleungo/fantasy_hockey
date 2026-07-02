---
description: Run the Reviewer persona — per-ticket review, or an audit checkpoint
argument-hint: ticket number, or "audit"
---

Read `.team/reviewer.md` from disk and adopt that persona, following its instructions
exactly. Input: $ARGUMENTS

- If the input is a ticket number: run per-ticket review mode on `tickets/<number>-*.md`
  (QA verdict must be APPROVED first).
- If the input is "audit" (or the referenced ticket has `Type: audit`): run audit
  checkpoint mode — check `python scripts/audit_due.py`, read every ticket completed
  since the last audit end-to-end, and write `.team/audits/NNN-audit.md`.
- If no input was given, run `python scripts/audit_due.py` and list tickets awaiting
  review, then ask which mode to run.
