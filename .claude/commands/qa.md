---
description: Run the Test Engineer persona — QA a ticket (combined QA+review for Process:light tickets)
argument-hint: ticket number (e.g. 025)
---

Read `.team/test-engineer.md` from disk and adopt that persona, following its
instructions exactly — including writing your own test plan before reading the
Engineer's "How to verify". QA this ticket: $ARGUMENTS

If the argument is a bare number, the ticket file is `tickets/<number>-*.md` and the
Engineer's handoff is `tickets/<number>-done.md`. If the ticket has `Process: light`,
run the combined QA + review mode and write `tickets/<number>-qa-review.md`. If no
ticket was given, list tickets with `Status: qa` and ask which to verify.
