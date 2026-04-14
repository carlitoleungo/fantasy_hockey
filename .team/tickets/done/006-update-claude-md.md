# 006 — Update CLAUDE.md for the FastAPI stack

## Summary

CLAUDE.md is loaded by Claude on every session start. It currently describes the Streamlit prototype — wrong stack, wrong entry points, and Streamlit-specific patterns that will mislead any engineer working on the new FastAPI architecture. Now that `docs/ARCHITECTURE.md` exists as the authoritative source of truth, CLAUDE.md needs a targeted trim and redirect: remove Streamlit-specific sections, replace duplicated structure with pointers, and update the running-locally instructions to cover both stacks.

## Acceptance criteria

- [ ] The "Streamlit-Specific Patterns" section (session state, `@st.cache_data`, auth flow, page structure guard) is removed in its entirety
- [ ] The "Tech Stack" section is replaced with a single line: `See docs/ARCHITECTURE.md for stack decisions.`
- [ ] The "Architecture" directory tree section is replaced with a single line: `See docs/ARCHITECTURE.md for directory structure.`
- [ ] The "Running Locally" section covers both stacks under their own subheadings: Streamlit prototype (`streamlit run app.py`) and FastAPI app (`uvicorn web.main:app --reload`)
- [ ] The intro paragraph at the top contains no mention of Streamlit as the stack
- [ ] Known Gotchas, Testing Strategy, Caching Strategy, Key Decisions Log pointer, Out of Scope, and Secrets & Auth sections are unchanged

## Files likely affected

- `CLAUDE.md`

## Dependencies

- Requires 001 to be merged (`docs/ARCHITECTURE.md` must exist before `CLAUDE.md` can point to it)

## Notes for the engineer

Read `docs/ARCHITECTURE.md` before editing — the replacement lines should reference specific paths and commands from it (e.g. the `uvicorn web.main:app --reload` start command, the `web/` directory). This is a trim, not a rewrite: do not touch sections that still apply to the new stack. The Secrets & Auth section can remain as-is; it's acceptable to leave the `.streamlit/secrets.toml` reference as a note that the Streamlit prototype still uses it, since the new stack uses env vars per `docs/ARCHITECTURE.md`. The goal is that a future Claude session reading `CLAUDE.md` gets accurate context about the current project state, not the prototype.

## Notes for QA

Read `CLAUDE.md` top to bottom after the edit and check for any remaining `st.`, `@st.cache_data`, or `st.session_state` references outside the Secrets & Auth section. Confirm the two pointer lines cite `docs/ARCHITECTURE.md` exactly. Confirm the Running Locally section has both subheadings with correct commands.

## Tech Lead Review

**Dependency status: functionally satisfied, not yet committed.** `docs/ARCHITECTURE.md` exists on disk (written as part of ticket 001) but is currently untracked in git. The engineer can author the edit now, but must confirm 001 is committed before opening a PR — otherwise the pointer lines in `CLAUDE.md` reference a file not present in the tree at review time.

**Intro paragraph needs updating.** The current `CLAUDE.md` opens with "A Streamlit web app that helps fantasy hockey managers make better add/drop decisions..." — the first sentence names Streamlit as the stack. The intro AC requires removing this. Suggested replacement, drawn from `docs/ARCHITECTURE.md §Overview`: "A public-facing web app that helps fantasy hockey managers evaluate waiver wire add/drop decisions using Yahoo Fantasy API data." Keep the rest of the intro paragraph if it remains accurate after removing the Streamlit reference.

**No hidden complexity.** The sections to remove (Streamlit-Specific Patterns, Tech Stack verbatim, Architecture tree) are clearly bounded. Known Gotchas, Testing Strategy, Caching Strategy, Secrets & Auth, and Out of Scope are unchanged — the ticket is correct to leave them alone. The "Development Workflow" section (do not use git worktrees) is still valid and also untouched.

**Files likely affected — complete.** `CLAUDE.md` only. Correct.

**Complexity: S** — a targeted trim and two pointer-line replacements. No code changes; low risk.

**Ordering**: Can proceed as soon as ticket 001 is committed. No dependency on 003, 004a, or 004b. Parallelisable with 004a.
