# Team Workflow — Fantasy Hockey Waiver Wire

This is the operating manual for the team-of-personas workflow. Read it after
`START_HERE.md`. Each persona runs in its own Claude Code session — handoffs flow
through files, not conversation. That's the central principle. Do not paste the output
of one session into another; the next session reads the file the previous one wrote.

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
| Test Engineer | `.team/test-engineer.md` | Ticket, `tickets/NNN-done.md`, `docs/LEARNINGS.md` | `tickets/NNN-qa.md`, possibly new tests in `tests/` | After Engineer hands off |
| Reviewer | `.team/reviewer.md` | Ticket, done note, QA report, diff | `tickets/NNN-review.md`, `docs/improvements.md`, `.team/audits/NNN-audit.md` | After QA approves, plus every 5 tickets for an audit |
| Orchestrator | `.team/orchestrator.md` | One ticket | Spawned subagents for each role; `.team/orchestration-logs/NNN-slug.md` | Optional: runs the per-ticket loop autonomously |

---

## How to invoke a persona

**Recommended (interactive):**
```bash
cat .team/pm.md | claude
```

**Reference in prompt:**
```bash
claude "Read .team/pm.md and follow those instructions. Here's what I need: [your request]"
```

The persona files are paste-and-go: they contain the project context inline so the
session needs no prior reading.

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
   → if APPROVED: updates ticket Status to done
```

---

## Audit cadence — non-negotiable

Every **5 completed non-audit tickets**, the next ticket is an `audit` ticket.
Additionally, before any architectural-surface ticket, if no audit has run in the last
5, schedule the audit first. The PM is the enforcer; the Reviewer runs the audit and
writes `.team/audits/NNN-audit.md`.

When the audit verdict is `NEEDS ATTENTION`, the PM should not scope further
architectural tickets until the action items are resolved.

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
├── START_HERE.md                # one-screen onboarding
├── WORKFLOW.md                  # this file
├── CLAUDE.md                    # project instructions (pre-existing, hands off)
├── docs/
│   ├── ARCHITECTURE.md          # current state of the world (Tech Lead owns)
│   ├── DECISIONS.md             # newest-first decisions log (Tech Lead owns)
│   ├── ROADMAP.md               # near-term work, editable (PM owns)
│   ├── LEARNINGS.md             # recurring gotchas (team adds)
│   ├── backlog.md               # deferred features (PM owns)
│   ├── improvements.md          # code-quality nits (Reviewer owns)
│   ├── bugs.md                  # known bugs in current stack
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
| Review | Reviewer | QA verdict APPROVED |
| Audit | Reviewer | Every 5 tickets, or before an arch-surface ticket |
| Sign-off | PM | All tickets for a feature done |
| Autonomous loop | Orchestrator | Ticket Status `ready`, no arch surface |
