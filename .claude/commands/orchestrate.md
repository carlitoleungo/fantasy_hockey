---
description: Orchestrate the full ticket loop autonomously (Engineer → QA → fix round → Reviewer)
argument-hint: ticket number (Status must be ready, no architectural surfaces)
---

Read `.team/orchestrator.md` from disk and follow it exactly to drive this ticket:
$ARGUMENTS

Run every pre-flight check first, including `python scripts/audit_due.py`. Spawn each
role with the Agent tool using these subagent types (they load the persona files from
disk, satisfying the re-read rule):

- Engineer → `fh-engineer`
- Test Engineer → `fh-test-engineer`
- Reviewer → `fh-reviewer` (skipped when the ticket is `Process: light`)

Each spawn's prompt must name the ticket file and the output file to write, per the
orchestrator persona. Spawns are sequential — never parallel, never combined roles,
never a Tech Lead. Halt and surface to the owner on any halt condition; always write
the orchestration log to `.team/orchestration-logs/NNN-slug.md`.
