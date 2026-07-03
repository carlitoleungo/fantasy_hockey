# Team Workflow — Fantasy Hockey Waiver Wire

This is the operating manual for the team-of-personas workflow. Each persona runs in
its own Claude Code session — handoffs flow through files, not conversation. That's the
central principle. Do not paste the output of one session into another; the next
session reads the file the previous one wrote.

---

## Quick start

You're developing **Fantasy Hockey Waiver Wire** — a public-facing FastAPI/HTMX app,
mid-migration from a Streamlit prototype — with a team of six personas in `.team/`
(PM, Tech Lead, Engineer, Test Engineer, Reviewer, Orchestrator).

- **Current state lives in `tickets/` and `docs/ROADMAP.md`**, not in this file — check
  those to see what's active and what's next.
- **To start new work**, run a PM session and tell it what you want: `/pm <request>`
  in Claude Code (or `cat .team/pm.md | claude`).
- **To push an existing `Status: ready` ticket forward**, run an Engineer session
  (`/engineer <ticket>`) — or the Orchestrator (`/orchestrate <ticket>`), if the
  ticket qualifies (see "The Orchestrator" below).
- The stack is already chosen — don't run a day-zero Tech Lead session (see "Day-zero
  sequence" below).

---

## Why separate sessions?

Fresh context per role keeps each session focused and cheap. The PM doesn't need the
Engineer's debugging trace. The Reviewer doesn't need the QA's manual-verification
walkthrough. Each persona declares what it reads (specific files) and what it writes,
so the next role can pick up cold.

If you're tempted to keep a long PM session alive while implementing — don't. Start a
fresh Engineer session.

---

## The roles

| Role | Persona file | Inputs | Writes | When to invoke |
|---|---|---|---|---|
| Product Manager | `.team/pm.md` | Idea, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/LEARNINGS.md`, `docs/backlog.md` | `tickets/NNN-slug.md`, `docs/backlog.md`, `docs/ROADMAP.md` | Define / scope / sign-off |
| Tech Lead | `.team/tech-lead.md` | Scoping brief, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` | `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, scoping notes | PM scoping consultation on architectural surfaces; mid-build architectural questions; periodic ARCHITECTURE.md refresh |
| Engineer | `.team/engineer.md` | One ticket, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/LEARNINGS.md` | Code, `tickets/NNN-done.md`, optional `docs/LEARNINGS.md` append, `docs/improvements.md` close-outs for items in modified files | Build phase, one ticket per session |
| Test Engineer | `.team/test-engineer.md` | Ticket, `tickets/NNN-done.md`, `docs/LEARNINGS.md` | `tickets/NNN-qa.md` (or `NNN-qa-review.md` for light tickets), possibly new tests in `tests/` | After Engineer hands off |
| Reviewer | `.team/reviewer.md` | Ticket, done note, QA report, diff | `tickets/NNN-review.md`, `docs/improvements.md`, `.team/audits/NNN-audit.md` | After QA approves (full-process tickets only), plus audits per `scripts/audit_due.py` |
| Orchestrator | `.team/orchestrator.md` | One ticket | Spawned subagents for each role; `.team/orchestration-logs/NNN-slug.md` | Optional: runs the per-ticket loop autonomously |

---

## How to invoke a persona

**In Claude Code (recommended)** — project slash commands wrap each persona:

| Command | Persona |
|---|---|
| `/pm <request>` | Product Manager |
| `/tech-lead <question or brief path>` | Tech Lead |
| `/engineer <ticket>` | Engineer |
| `/qa <ticket>` | Test Engineer (combined QA+review for light tickets) |
| `/reviewer <ticket \| audit>` | Reviewer |
| `/orchestrate <ticket>` | Orchestrator |

The commands live in `.claude/commands/`; the Orchestrator spawns its subagents via
the matching agent definitions in `.claude/agents/` (`fh-engineer`,
`fh-test-engineer`, `fh-reviewer`). All of them load the persona files from `.team/`
at run time — **the persona files remain the single source of truth**; the command and
agent files are thin shims, so persona edits never need to be made twice.

**Plain CLI equivalent** (still works):
```bash
cat .team/pm.md | claude
# or
claude "Read .team/pm.md and follow those instructions. Here's what I need: [your request]"
```

Either way, start each persona in a fresh session; the personas read the project docs
they need from disk.

---

## The standard ticket loop

```
1. PM session
   → reads ROADMAP, DECISIONS, LEARNINGS, backlog
   → asks clarifying questions if the idea is ambiguous (max 2-3)
   → if architectural surface: writes a scoping brief, you run it past the Tech Lead
   → produces tickets/NNN-slug.md (Status: ready)

2. Tech Lead session (only when PM flagged the ticket as architectural)
   → reviews PM's scoping brief
   → adds long-term implications to each option
   → writes a DECISIONS.md entry if the chosen option warrants one
   → returns notes that the PM folds into "Notes for the Engineer"

3. Engineer session
   → reads the ticket, ARCHITECTURE.md, DECISIONS.md, LEARNINGS.md, the Touches files
   → implements only what's specified
   → walks the new behaviour in a browser if UI-touching
   → writes tickets/NNN-done.md
   → updates ticket Status to qa

4. Test Engineer session
   → writes their own test plan before reading the Engineer's verification
   → runs `python -m pytest tests/`
   → starts uvicorn, walks each acceptance criterion in a browser
   → verifies demo mode if the ticket touched data/
   → writes tickets/NNN-qa.md (verdict: APPROVED or NEEDS FIXES)
   → if NEEDS FIXES: back to Engineer with the QA report;
     Engineer writes tickets/NNN-fix.md; QA re-runs

5. Reviewer session
   → only after QA verdict is APPROVED
   → reviews the diff, ticket, done, qa
   → writes tickets/NNN-review.md
   → logs nits to docs/improvements.md
   → if APPROVED: updates ticket Status to done, then moves the ticket and all its
     artifacts (tickets/NNN-*.md) into tickets/done/
```

### Light process — for trivial tickets

The PM may mark a ticket `Process: light` (an optional `## Process` section in the
ticket file) when **all three** hold:

- ≤ ~20 lines of change expected
- it follows an existing pattern verbatim (a same-shape route, template variable, or
  test already exists to copy)
- it touches no architectural surface

Light loop: Engineer session → **one combined QA-and-review session**. The Test
Engineer runs their normal verification plus the Reviewer's always-blocker checklist
(layer purity, `_coerce`/`_as_list`, bulk endpoints, demo parity, DECISIONS conflicts,
`Touches` adherence) and writes a single `tickets/NNN-qa-review.md`. No separate
Reviewer session; one fix round allowed as usual. On an APPROVED verdict the Test
Engineer sets Status to done and moves the ticket and its artifacts into `tickets/done/`
(same as the Reviewer does on the full process). Light tickets count ½ toward the audit
cadence and are still covered by audits.

When in doubt, use the full process — light is an optimisation, not the default.

---

## Audit cadence — non-negotiable

Every **5 weighted completed non-audit tickets**, the next ticket is an `audit`
ticket. Full-process tickets count 1; `Process: light` tickets count ½ (less risk, but
the audit still covers them). Don't count by memory — run:

```bash
python scripts/audit_due.py
```

The PM runs it at the start of every scoping session and before finalising any
architectural-surface ticket; the Orchestrator runs it in pre-flight. The Reviewer runs
the audit and writes `.team/audits/NNN-audit.md` (NNN = the audit ticket's number).

**What an overdue audit blocks — and what it doesn't.** An overdue audit, or a
`NEEDS ATTENTION` verdict with unresolved action items, blocks scoping
**architectural-surface tickets only**. Non-architectural bug fixes and light tickets
may proceed while the audit is scheduled and run — do not sequence unrelated small
fixes behind an audit.

**Revisit the interval.** The 5-ticket cadence is calibrated for the migration period,
where most tickets establish new conventions. When the Streamlit teardown completes and
the pattern set stabilises, revisit the threshold (8–10 is reasonable for a stable
codebase) — change `AUDIT_THRESHOLD` in `scripts/audit_due.py` and this section together.

---

## Architectural-surface escalation list

Any ticket touching the following requires a Tech Lead consult **before** the PM
finalises it:

- Yahoo OAuth flow (`auth/oauth.py`) and session/nonce storage (`db/schema.sql`,
  `user_sessions`, `oauth_states`)
- Parquet cache layer (`data/cache.py`, `CACHE_DIR`, on-disk layout under `/data/cache/`)
- Yahoo API client conventions (`data/client.py` — bulk vs. per-entity, `_as_list`,
  `_coerce`, `xmltodict` quirks)
- Routing / middleware (`web/main.py`, `web/middleware/session.py`, `Depends(require_user)`,
  public vs. authenticated route registration)
- Template structure (HTMX shell + fragment split — `docs/DECISIONS.md` 2026-04-19 entry)
- Demo-mode parity — every new live data function needs a demo counterpart
- New dependency (`requirements-web.txt`), new env var (`Dockerfile`, `fly.toml`),
  new config knob

---

## Day-zero sequence — N/A for this project

The original `team-generator` skill prescribes a Tech Lead session as step zero to pick
the stack. **This project's stack was chosen on 2026-04-10** (FastAPI + Jinja2 + HTMX +
Alpine + Tailwind, SQLite, Fly.io). See `docs/ARCHITECTURE.md` and `docs/DECISIONS.md`
for the rationale. Don't re-litigate it; if a hard new constraint emerges, the Tech
Lead supersedes the prior decision with a new dated entry — never edit in place.

---

## File layout (concrete paths only)

```
fantasy_hockey/
├── WORKFLOW.md                  # this file (includes quick start)
├── CLAUDE.md                    # project instructions, loaded into every session (owner maintains; personas hands off)
├── docs/
│   ├── ARCHITECTURE.md          # current state of the world (Tech Lead owns)
│   ├── DECISIONS.md             # newest-first decisions log (Tech Lead owns)
│   ├── ROADMAP.md               # near-term work, editable (PM owns)
│   ├── LEARNINGS.md             # recurring gotchas incl. Yahoo API (team adds)
│   ├── backlog.md               # deferred features (PM owns)
│   ├── improvements.md          # quality nits + bugs, Type-tagged (Reviewer curates)
│   └── archive/                 # Streamlit-era material; reference only
├── tickets/                     # active tickets at this level
│   ├── NNN-slug.md              # ticket spec (PM writes)
│   ├── NNN-done.md              # Engineer handoff
│   ├── NNN-qa.md                # Test Engineer report
│   ├── NNN-review.md            # Reviewer per-ticket output
│   ├── NNN-fix.md               # Engineer fix-round handoff (if QA returned NEEDS FIXES)
│   ├── done/                    # historical closed tickets
│   └── archive/                 # archived tickets
└── .team/
    ├── pm.md
    ├── tech-lead.md
    ├── engineer.md
    ├── test-engineer.md
    ├── reviewer.md
    ├── orchestrator.md
    ├── audits/                  # .team/audits/NNN-audit.md
    └── orchestration-logs/      # .team/orchestration-logs/NNN-slug.md
```

---

## The Orchestrator (optional)

`.team/orchestrator.md` runs the Engineer → Test Engineer → (one fix round) → Reviewer
loop autonomously by spawning subagents per ticket. It speeds up routine tickets but
reduces visibility into each handoff.

**Use the Orchestrator when:**

- The ticket is `Status: ready`, has no architectural surfaces in `Touches`, and the
  acceptance criteria are unambiguous
- You've run the manual loop a few times and trust the persona quality

**Don't use the Orchestrator when:**

- The ticket has any architectural surface in `Touches` (the orchestrator will refuse
  anyway, but flagging here so you don't try)
- You expect the Engineer to need clarification — the orchestrator will halt and
  surface, and you'll re-run manually
- You haven't seen the Test Engineer and Reviewer behave on this kind of ticket before

The Orchestrator never spawns a Tech Lead, never edits source code itself, and never
runs git. It always writes a log to `.team/orchestration-logs/NNN-slug.md`, completed
or halted.

---

## Tips that earn their weight

1. **One ticket per Engineer session.** Don't batch. Highest-leverage rule.
2. **Let the PM push back on scope.** If they say it's too big, listen.
3. **Don't skip QA.** It catches what self-review misses, especially demo-mode parity
   and Yahoo API edge cases.
4. **Use the backlog.** New ideas mid-build go in `docs/backlog.md`, not the current ticket.
5. **Loop in the Tech Lead early on architectural tickets.** The scoping consultation
   is cheap; undoing structure is not.
6. **Keep `docs/ROADMAP.md` and `docs/DECISIONS.md` current.** They're the project's
   long-term memory across sessions. The PM consults `ROADMAP.md` every scope pass; the
   Tech Lead writes to `DECISIONS.md` on every new architectural choice.
7. **Scope bugs one at a time by default.** A cluster gets a triage pass first, but the
   PM still scopes one ticket now and re-evaluates after the fix lands.
8. **Don't reuse a stale session.** Start fresh after each persona handoff. Long sessions
   accumulate scope creep.

---

## Quick reference

| Phase | Persona | Trigger |
|---|---|---|
| Scoping | PM | Idea, bug, or roadmap item ready to ticket |
| Architectural consult | Tech Lead | PM flagged a surface |
| Build | Engineer | Ticket Status is `ready` |
| QA | Test Engineer | Ticket Status is `qa` |
| QA + review combined | Test Engineer | Ticket Status is `qa` and `Process: light` |
| Review | Reviewer | QA verdict APPROVED (full-process tickets) |
| Audit | Reviewer | `scripts/audit_due.py` reports DUE, or before an arch-surface ticket |
| Sign-off | PM | All tickets for a feature done |
| Autonomous loop | Orchestrator | Ticket Status `ready`, no arch surface |
