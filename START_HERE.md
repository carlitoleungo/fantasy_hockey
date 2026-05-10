# Start Here

You're using a team-of-personas workflow to develop **Fantasy Hockey Waiver Wire** — a
public-facing FastAPI/HTMX app, mid-migration from a Streamlit prototype.

## What's been generated

- **`WORKFLOW.md`** — the operating manual: when to invoke each persona, the standard
  ticket loop, escalation rules. Read this next.
- **`.team/`** — six personas: PM, Tech Lead, Engineer, Test Engineer, Reviewer,
  Orchestrator. Each runs in its own Claude Code session. Handoffs flow through files.
- **`docs/`** — `ARCHITECTURE.md`, `DECISIONS.md`, `LEARNINGS.md`, `ROADMAP.md`,
  `backlog.md`, `improvements.md`, `bugs.md`. Pre-populated from the existing project
  history. Personas read these before scoping or implementing.
- **`tickets/`** — active tickets at this level (current: 018, 019a, 019b). Closed
  tickets and migration history are in `tickets/done/` and `tickets/archive/`.

## Stack is already chosen

The team-generator skill normally expects a "day-zero Tech Lead session" to pick the
stack. **Skip that** — this project's stack was chosen on 2026-04-10 (FastAPI + Jinja2
+ HTMX + Alpine + Tailwind, SQLite, Fly.io) and is documented in
`docs/ARCHITECTURE.md` and `docs/DECISIONS.md`.

## Your immediate next step

Have the PM scope the next ticket. From the project root:

```bash
cat .team/pm.md | claude
```

Then tell the PM what you want to work on. Likely candidates from `docs/ROADMAP.md`:

- The waiver wire post handler (tickets 019a/019b) is already scoped — invoke the
  Engineer instead if you want to push existing tickets forward
- Demo mode port
- Per-user cache storage migration
- Bug fixes from `docs/bugs.md` or `docs/improvements.md`

For everything else — handoff format, audit cadence, when to consult the Tech Lead,
how to use the optional Orchestrator — see `WORKFLOW.md`.
