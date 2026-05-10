# 001 — Tech Lead: stack selection + ARCHITECTURE.md

## Summary

The Tech Lead delivers a decision document at `docs/ARCHITECTURE.md` that records the framework choice with explicit reasoning over alternatives, the multi-tenant Yahoo OAuth strategy (how state nonces and tokens are stored server-side across processes), the storage plan for all three data tiers (session/auth tokens, user-scoped league cache, static demo data), and the deployment target. The document also enumerates which existing files are preserved verbatim and which are replaced, so every subsequent ticket has a shared reference point. No code is written in this ticket — the output is the document alone.

## Acceptance criteria

- [ ] `docs/ARCHITECTURE.md` exists and is committed to the repo.
- [ ] The document names exactly one web framework and argues why it is preferred over at least two named alternatives for this specific use case (multi-tenant, Yahoo OAuth callback, Python data stack, single-engineer maintained).
- [ ] The document specifies the storage backend for each of three tiers: (1) CSRF state nonces with TTL, (2) encrypted OAuth tokens per user, (3) per-user matchups/players cache (the parquet files currently at `.cache/{league_key}/`). Each tier names the specific technology or service, not a category like "a database".
- [ ] The document states the deployment target (platform, region, containerised vs. managed) and argues why it was chosen over at least one alternative.
- [ ] The document contains a "Preserved files" table listing every file under `data/`, `analysis/`, `auth/oauth.py`, and `demo/data/` that requires zero changes, and a "Replaced files" table listing every file under `app.py` and `pages/` that will be deleted.
- [ ] The document describes the session strategy: how an authenticated user's identity travels from the OAuth callback through to a route handler in subsequent requests (cookie, JWT, or server-side session — whichever is chosen — must be named and the lifetime policy stated).

## Files likely affected

- `docs/ARCHITECTURE.md` (created)

## Dependencies

None

## Notes for the engineer

Three concrete problems the new architecture must solve that the current code does not:

1. **CSRF nonce store**: `_save_state` / `_load_states` in `auth/oauth.py` write to `.streamlit/oauth_states.json` — a shared flat file that breaks under concurrent users and is inaccessible across multiple web processes or containers. The new architecture needs an atomic, TTL-aware store (a DB row with an expiry column, or a Redis key with TTL).

2. **Token persistence**: Tokens live exclusively in `st.session_state` (in-process, per-tab). A web framework needs either a signed-cookie session (tokens in the cookie) or a server-side session table (session ID in cookie, tokens in DB). The multi-tenant public deployment makes client-side token storage riskier — the architecture doc should justify whichever choice is made.

3. **Cache portability**: The parquet cache at `.cache/{league_key}/` is local disk. In a containerised or managed deployment without a persistent volume, this is ephemeral. The doc must name where this cache goes (object storage, a DB with blob columns, etc.) and acknowledge the trade-off between simplicity and scalability.

The `TOKEN_EXPIRY_BUFFER_SECONDS = 60` constant and `_is_valid` / `_try_refresh` logic in `auth/oauth.py` are already correct and will be reused in ticket 005 — do not redesign them. The `data/`, `analysis/`, and `demo/` layers are pure Python with no framework imports and need zero changes.

Also read `docs/decisions.md` for historical context on choices already made.

## Notes for QA

This ticket produces a document, not running code. Review should confirm: (a) every decision has at least one sentence of justification, (b) all file paths in the "Preserved files" and "Replaced files" tables actually exist in the repo (`ls data/ analysis/ pages/` to verify), and (c) there are no internal contradictions — e.g. choosing stateless JWT but then describing server-side token lookup that requires a user ID.
