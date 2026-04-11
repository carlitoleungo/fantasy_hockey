---
name: team-generator
description: >
  Generates a set of AI persona files (.md) that emulate a software development team for use
  with Claude Code. Use this skill whenever a user wants to set up development personas, create
  a virtual dev team, generate role-based prompt files for Claude Code, or says things like
  "set up my team", "create personas for my project", "I want a PM/engineer/QA for Claude Code",
  "generate team files", or "help me use Claude Code like a dev team". Also trigger when the user
  mentions wanting better structure, process, or quality control in their Claude Code workflow,
  or when they describe a solo development setup where they want the rigor of a full team.
---

# Team Generator Skill

Generate a project-specific set of persona `.md` files that give Claude Code the focus and
discipline of a structured development team. Each persona enforces a specific role in the
development process, with clear inputs, outputs, and quality gates.

---

## What this skill produces

A `.team/` folder containing:

1. **pm.md** — Product Manager: takes rough ideas, produces scoped tickets with acceptance criteria
2. **tech-lead.md** — Tech Lead: defines architecture, picks stack, orders the backlog
3. **engineer.md** — Engineer: implements one ticket at a time, hands off to QA
4. **test-engineer.md** — Test Engineer: independently verifies against acceptance criteria
5. **reviewer.md** — Code Reviewer: checks quality, patterns, and scope creep
6. **WORKFLOW.md** — Step-by-step guide for using the personas with Claude Code
7. **backlog.md** — Empty backlog file the PM populates with deferred features
8. **tickets/** — Empty directory for PM-generated ticket files

---

## Process

### Step 1: Project interview (3-4 questions max)

Before generating anything, understand the project. Ask these in one message:

1. **What are you building?** (one sentence is fine)
2. **Tech stack** — if known. If greenfield and undecided, say so and the Tech Lead persona
   will handle stack selection.
3. **Repo structure** — does a repo exist already? If so, what's the general layout?
   If greenfield, note that.
4. **Your biggest pain point** — what goes wrong most often when building? (e.g., scope creep,
   bugs, losing context, not knowing where to start)

If the conversation already contains answers to these, extract them — don't re-ask.

### Step 2: Generate the team files

Read `references/persona-templates.md` for the full template for each persona.

For each persona file, take the template and weave in project-specific details:

- Replace all `[PLACEHOLDER]` values with project-specific information
- Add stack-specific guidance to the Engineer persona (e.g., framework conventions, test runners)
- Add project-specific architecture patterns to the Tech Lead persona
- Adjust the Test Engineer's verification commands to match the stack (e.g., `npm test`,
  `pytest`, `streamlit run` + manual check)
- If the project is frontend-heavy, emphasize visual verification in the Test Engineer
- If the project is data-heavy, emphasize data validation and edge cases

Generate all files into a `.team/` directory structure.

### Step 3: Generate the WORKFLOW.md

This is the most important file — it tells the user exactly how to use the team.
Read the workflow template in `references/persona-templates.md` and customize it
with the project's specific commands and context.

### Step 4: Present to the user

Share all generated files using `present_files`. Provide a brief summary:
- What was generated
- The recommended first step (usually: start a Claude Code session with the PM persona)
- One concrete example of how to invoke the first persona for their specific project

Keep the summary short — the WORKFLOW.md has the details.

---

## Design principles baked into every persona

These are non-negotiable and should be preserved when customizing:

1. **Separate sessions per persona.** Each role runs in its own Claude Code session.
   Handoffs happen through files in the repo (tickets, code, bug reports), not conversation.
   This keeps context focused and token costs low.

2. **Explicit inputs and outputs.** Every persona states what it needs before starting and
   what it produces when done. No ambiguity about handoff points.

3. **Quality gates with teeth.** The Test Engineer never trusts the Engineer's self-report.
   The PM enforces ticket size limits. The Reviewer checks for scope creep. These aren't
   suggestions — they're hard rules in each persona file.

4. **Anti-patterns are as important as instructions.** Each persona includes a "Never do this"
   section. Telling Claude what NOT to do is often more effective than positive instructions,
   because it prevents the specific failure modes that cause real problems.

5. **The PM is the highest-leverage persona.** Most development problems trace back to poor
   scoping. The PM persona is deliberately opinionated about ticket size — it refuses to
   create tickets that touch more than 2-3 files or require more than one focused session.
   This is the single most important constraint in the entire system.

6. **Backlog over scope creep.** When the PM scopes down an idea, cut features go into
   `backlog.md` with enough context to pick up later without re-explaining. Nothing is lost,
   but nothing sneaks into the current sprint either.
