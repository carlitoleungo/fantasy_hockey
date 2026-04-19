# Team Workflow — Fantasy Hockey Waiver Wire

This guide explains how to use the persona files in `.team/` with Claude Code to develop
the Fantasy Hockey Waiver Wire app with the structure and quality control of a full dev team.

---

## Before you start — know what's being preserved vs. replaced

This is a rebuild of a working Streamlit prototype. Before writing any new code:

**Preserved (pure Python, no framework deps — portable to any backend):**
- `data/client.py` — Yahoo API client, XML parsing, `_as_list()`, `_coerce()`
- `data/cache.py` — Parquet + JSON disk cache; delta-fetch, TTL, append patterns
- `data/matchups.py`, `data/players.py`, `data/leagues.py` — Data fetching logic
- `analysis/waiver_ranking.py`, `analysis/team_scores.py`, `analysis/matchup_sim.py`
- `auth/oauth.py` — Custom Yahoo OAuth 2.0 (will need changes for multi-user)
- `data/demo.py` + `demo/data/` — Demo mode static data

**Being replaced:**
- All `pages/` and `app.py` (Streamlit UI — going away entirely)
- `st.session_state`, `@st.cache_data` patterns
- Single-user token storage in session state

---

## Setup

Each persona runs in its own Claude Code session. Keeping sessions separate keeps context
focused and costs low. Handoffs happen through files (tickets, handoff notes, QA reports),
not through conversation.

### How to invoke a persona

**Option A — interactive session (recommended):**
```bash
cat .team/pm.md | claude
```

**Option B — reference in your prompt:**
```bash
claude "Read .team/pm.md and follow those instructions. Here's what I need: [your request]"
```

**Option C — one-shot with --print:**
```bash
claude --print "$(cat .team/pm.md)" -p "Here's my feature idea: [idea]"
```

---

## Phase 0: Stack Selection (Tech Lead) — run this first, before any PM tickets

The frontend stack is undecided. Nothing else can start until the Tech Lead makes a
recommendation and writes `ARCHITECTURE.md`.

```bash
cat .team/tech-lead.md | claude
```

**Prompt after Tech Lead loads:**
> "We're rebuilding the Fantasy Hockey Waiver Wire app from its Streamlit prototype into a
>  public-facing, mobile-friendly web app. Read `.team/tech-lead.md` for what's preserved
>  vs. replaced, then work through the stack evaluation questions and write `ARCHITECTURE.md`
>  with your recommendation and rationale."

**Output:** `ARCHITECTURE.md` at the project root with stack choice, directory structure,
and key patterns.

---

## Phase 1: Define (PM)

```bash
cat .team/pm.md | claude
```

Tell the PM your idea. It will ask clarifying questions, then produce ticket files
in `.team/tickets/` and update `docs/backlog.md` for anything deferred.

**Example prompts:**
> "I want to add a player comparison view — show two players side by side with their
>  stats for the last 30 days. Help me scope this into tickets."

> "The waiver wire page needs to show how many games each player has remaining this week.
>  Scope it out."

**Hard rule:** The PM will not create a ticket that spans Yahoo API fetching AND UI in the
same ticket. If your idea requires both, expect two tickets — data first, UI second.

---

## Phase 1b: Scoping consultation (Tech Lead) — optional, for architectural work

If the PM flags a ticket as architecturally significant (touches data model, auth, routing,
state management, API boundaries, storage, or cross-cutting dependencies in `data/`/`analysis/`),
it will produce a short scoping brief with 2–3 option sketches before finalizing the ticket.
Run those options past the Tech Lead:

```bash
cat .team/tech-lead.md | claude
```

**Prompt after Tech Lead loads:**
> "The PM is scoping a ticket and flagged it as architectural. Here's the brief: [paste brief].
>  Sanity-check against `docs/decisions.md` and `docs/roadmap.md`, and add long-term implications
>  to each option."

Take the Tech Lead's notes back to the PM to finalize the ticket. The Tech Lead should log
any significant decision that falls out of this in `docs/decisions.md`.

Skip this phase for non-architectural tickets (UI tweaks, isolated bug fixes, copy changes).

---

## Phase 2: Plan (Tech Lead)

After the PM creates tickets, have the Tech Lead review them for feasibility and ordering.

```bash
cat .team/tech-lead.md | claude
```

**Prompt after Tech Lead loads:**
> "Review the new tickets in `tickets/` and give me an implementation order. Add complexity
>  estimates (S/M/L) and flag anything that's too large or has hidden dependencies."

**Output:** Complexity estimates and implementation order appended to each ticket file,
plus a summary ordering message.

---

## Phase 3: Build (Engineer)

One ticket per session. This is the single most important rule.

```bash
cat .team/engineer.md | claude
```

**Prompt after Engineer loads:**
> "Implement ticket 001. Read `tickets/001-[name].md` and `ARCHITECTURE.md` first.
>  Do not start writing code until you've read both."

The Engineer produces a handoff note (`.team/tickets/[NUMBER]-done.md`) when finished.

---

## Phase 4: Test (Test Engineer)

```bash
cat .team/test-engineer.md | claude
```

**Prompt after Test Engineer loads:**
> "QA ticket 001. Read the ticket at `.team/tickets/001-[name].md` and the engineer's
>  handoff at `.team/tickets/001-done.md`. Write your own test plan first, then run tests,
>  then verify manually in the browser."

**The Test Engineer will:**
1. Run `python -m pytest tests/` (or the current test command) and report which tests ran
2. Start the app and walk through acceptance criteria in a browser
3. Verify demo mode if the ticket touches any data function
4. Write a QA report at `tickets/[NUMBER]-qa.md`

If issues found → back to Engineer with the QA report. Engineer creates `-fix.md` handoff,
then QA runs again.

---

## Phase 5: Review (Code Reviewer) — required for L tickets, optional for S

```bash
cat .team/reviewer.md | claude
```

**Prompt after Reviewer loads:**
> "Review the changes for ticket 001. Read the ticket, the QA report at
>  `.team/tickets/001-qa.md`, and the changed files."

The Reviewer will specifically check for:
- Framework imports (`streamlit`, `fastapi`, etc.) in `data/` or `analysis/`
- Per-entity API loops where a bulk endpoint exists
- Missing demo counterparts for new data functions

---

## Phase 6: Product sign-off (PM)

After all tickets for a feature are approved:

```bash
cat .team/pm.md | claude
```

> "All tickets for [feature] are complete and tested. Do a final product review —
>  does the delivered work match what was originally asked for?"

---

## Tips for best results

1. **One ticket per Engineer session.** Don't batch. Batching is where bugs get introduced
   and context gets lost. This is the highest-leverage rule in the whole system.

2. **Let the PM push back on scope.** If it says your idea is too big, listen. Smaller
   tickets mean fewer bugs and clearer QA. If you feel the split is wrong, discuss it
   before ticketing — don't expand scope during implementation.

3. **Don't skip QA.** The Test Engineer catches things the Engineer genuinely misses,
   especially around demo mode parity and edge cases in Yahoo API responses. The cost of
   a QA session is far less than debugging a shipped bug.

4. **Use the backlog.** When new ideas come up mid-build, add them to `backlog.md` instead
   of expanding the current ticket. Nothing is lost; it just waits its turn.

5. **Run the Tech Lead before the first sprint of any new feature area.** If you're about
   to work in a part of the codebase you haven't touched before, have the Tech Lead review
   the relevant tickets first.

6. **Start fresh sessions.** Don't reuse a long Engineer session for a second ticket.
   Fresh context = better results and fewer "while I'm here" scope creeps.

7. **Loop in the Tech Lead early for architectural tickets.** The scoping consultation
   (Phase 1b) is cheap compared to undoing a structural choice later. Skip it for UI tweaks
   and isolated bug fixes — use it when data model, auth, routing, or state management moves.

8. **Keep `docs/roadmap.md` and `docs/decisions.md` current.** They're the project's long-term
   memory. The PM consults them every scoping pass; the Tech Lead updates `docs/decisions.md`
   when choices are made.

9. **Scope bugs one at a time by default.** If several bugs surface at once, ask the PM to
   triage first — the root cause of one often dissolves the others.

---

## Quick reference

| Phase | Persona | Input | Output |
|-------|---------|-------|--------|
| Stack selection | Tech Lead | Current codebase | `docs/ARCHITECTURE.md` |
| Define | PM | Your idea + `docs/roadmap.md` + `docs/decisions.md` | Ticket files + `docs/backlog.md` / `docs/roadmap.md` updates |
| Scoping consult (optional) | Tech Lead | PM's scoping brief | Option notes + `docs/decisions.md` entry if applicable |
| Plan | Tech Lead | Tickets | Ordered backlog + complexity estimates |
| Build | Engineer | One ticket | Code + `tickets/[N]-done.md` |
| Test | Test Engineer | Ticket + handoff | `tickets/[N]-qa.md` |
| Review | Reviewer | Ticket + code + QA | `tickets/[N]-review.md` |
| Sign-off | PM | All approved tickets | Product review summary |

---

## File map

```
.team/
  pm.md               # Product Manager persona
  tech-lead.md        # Tech Lead persona
  engineer.md         # Engineer persona
  test-engineer.md    # Test Engineer persona
  reviewer.md         # Code Reviewer persona
  WORKFLOW.md         # This file
  tickets/            # Ticket specs + done/qa/review artefacts (all flat, no subdirectory)
docs/
  ARCHITECTURE.md     # Stack decisions and directory structure (Tech Lead maintains this)
  decisions.md        # Architectural decisions log, newest at top (Tech Lead maintains this)
  roadmap.md          # Likely near-term work — pressure-test tool for scoping (PM maintains this)
  learnings.md        # Recurring gotchas that apply across tickets (Test Engineer / team add entries)
  backlog.md          # Deferred features (PM maintains this)
  improvements.md     # Code quality nits on existing code (Reviewer maintains this)
  bugs.md             # Known bugs
```
