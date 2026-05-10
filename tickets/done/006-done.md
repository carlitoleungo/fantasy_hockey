## Implementation complete — 006

**What I did:**
- Replaced intro paragraph to remove "A Streamlit web app" — now uses the overview from `docs/ARCHITECTURE.md §Overview`
- Replaced `## Architecture` directory tree + prose with single pointer line to `docs/ARCHITECTURE.md`
- Replaced `## Tech Stack` bullet list with single pointer line to `docs/ARCHITECTURE.md`
- Removed `## Streamlit-Specific Patterns` section in its entirety (Session State, In-session Caching, Auth Flow, Page Structure)
- Updated `## Running Locally` to include both `### Streamlit prototype` and `### FastAPI app` subheadings with correct commands

**Files changed:**
- `CLAUDE.md` — targeted trim and two pointer-line replacements per ticket spec

**How to verify:**
- Open `CLAUDE.md` and confirm no `## Streamlit-Specific Patterns` section exists
- Search for `st\.` — only hits should be `st.secrets` (line 54, Secrets & Auth section) and `@st.cache_data` (line 73, Known Gotchas section), both in explicitly preserved sections
- Confirm `## Architecture` reads: `See \`docs/ARCHITECTURE.md\` for directory structure and layer rules.`
- Confirm `## Tech Stack` reads: `See \`docs/ARCHITECTURE.md\` for stack decisions.`
- Confirm `## Running Locally` has two subheadings: `### Streamlit prototype` (`streamlit run app.py`) and `### FastAPI app` (`uvicorn web.main:app --reload`)

**Scope notes:**
- `Known Gotchas` contains two stale Streamlit-specific bullets (lines 73–74): one about Streamlit reruns/`@st.cache_data` and one referencing "default Streamlit port is 8501". The ticket explicitly leaves Known Gotchas unchanged, so these were not touched. A follow-up ticket should update Known Gotchas to remove or replace the Streamlit-specific items with FastAPI equivalents.

**Known limitations:**
- The `Secrets & Auth` section still references `.streamlit/secrets.toml` and `st.secrets` — the ticket notes this is acceptable as a record that the Streamlit prototype uses it; the FastAPI stack uses env vars per `docs/ARCHITECTURE.md`.
