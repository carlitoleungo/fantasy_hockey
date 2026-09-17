# 051 — OAuth credential helpers fail fast when an env var is missing

## Status
done

## Type
bug

## Process
full

(Not `light`: the change is ~12 lines and follows an obvious pattern, but `auth/oauth.py`
is on `WORKFLOW.md`'s architectural-surface escalation list, which rules out `light` per
`.team/pm.md`. The Reviewer pass is cheap here and this is the last code change before the
first production deploy.)

## Model
sonnet

## Milestone
m1

## Touches
- auth/oauth.py
- tests/test_oauth_helpers.py

## Why
On the first `fly deploy`, the single most likely misconfiguration is a Yahoo credential
secret that was never set (or set under the wrong name). Today `_client_id()`,
`_client_secret()` and `_redirect_uri()` (`auth/oauth.py:147-166`) fall back to
`import streamlit` + `st.secrets["yahoo"][...]` when their env var is absent. `streamlit`
is not in `requirements-web.txt`, so in the Fly image that fallback raises
`ModuleNotFoundError: No module named 'streamlit'` from inside the OAuth callback, which
the 500 handler renders to the user as "Something went wrong." The owner debugging a
broken login would be chasing a phantom Streamlit dependency instead of reading "YAHOO_CLIENT_SECRET
environment variable not set". This must land **before** `fly deploy`
(`docs/ROADMAP.md` § M1 launch steps 2-3 now run `fly apps create` → `fly volumes create`
→ `fly secrets set` → `fly deploy` with nothing in front of them).

## Acceptance criteria
- [ ] `grep -n streamlit auth/oauth.py` returns no hits inside `_client_id`,
      `_client_secret` or `_redirect_uri` (hits elsewhere in the file are expected and in
      scope to leave alone — see Out of scope).
- [ ] With `YAHOO_CLIENT_ID` unset, calling `auth.oauth._client_id()` raises
      `RuntimeError` whose message contains `YAHOO_CLIENT_ID`; likewise `_client_secret()`
      → `YAHOO_CLIENT_SECRET` and `_redirect_uri()` → `YAHOO_REDIRECT_URI`. Each helper
      names its own env var, not a shared generic message.
- [ ] With the env var set, each helper still returns the env var's value unchanged
      (no behaviour change on the configured path).
- [ ] `tests/test_oauth_helpers.py` gains coverage for both branches of all three helpers
      (set → value, unset → `RuntimeError` naming that variable), and the test asserts the
      error type is `RuntimeError`, not `ModuleNotFoundError`.
- [ ] `.venv/bin/python -m pytest tests/` passes with no new failures.

## Out of scope
- **The four Streamlit-only functions in the same file** (`validate_and_consume_state`,
  `try_restore_session`, `get_session`, `clear_session`, ~60 lines, `auth/oauth.py:58-117`).
  Audit 046 suggested folding them in; leaving them out deliberately. They are still
  imported by `app.py`, `pages/` and `utils/common.py`, so removing them breaks the
  Streamlit prototype's import graph and turns a two-file deploy-critical fix into a
  cross-workstream teardown touching five-plus files. Their presence costs nothing at
  runtime: the three that touch Streamlit lazy-import it inside the function body, and `web/`
  never calls any of the four.
  They stay on the `docs/improvements.md` entry for the Streamlit teardown to claim.
- Adding `streamlit` to `requirements-web.txt`. The fallback is dead code, not a missing
  dependency.
- Any startup-time / config-validation check that fails the app boot when a secret is
  missing. Fail-fast at first use is the whole ask here.
- Touching `.env.example`, `fly.toml`, or the Dockerfile. The env var names are unchanged.

## Notes for the Engineer
- **Pattern to follow:** keep the existing `if "YAHOO_CLIENT_ID" in os.environ: return
  os.environ["YAHOO_CLIENT_ID"]` shape and replace only the two fallback lines with a
  `raise RuntimeError(...)`. `os.environ[...]`'s own `KeyError` is not an acceptable
  substitute — the message is the point of the ticket.
- **Architectural surface + covering decision.** `auth/oauth.py` (Yahoo OAuth flow) is on
  `WORKFLOW.md` § "Architectural-surface escalation list", so the Orchestrator's pre-flight
  check 6 applies. The covering active decision is **`docs/DECISIONS.md` 2026-03-03 "Auth:
  yahoo_oauth not used for the OAuth flow"**, which establishes the hand-rolled
  `requests`-based implementation in `auth/oauth.py` as the sanctioned flow. This ticket
  conforms to it: the redirect-based flow, the token endpoints, the `check validity →
  refresh → return session` pattern and the env-var credential contract are all unchanged.
  Only a dead, unreachable-in-production fallback branch is deleted. No new Tech Lead
  consult was taken, on the same basis Review 045 accepted an existing decision as covering
  a `fly.toml` change that could not alter the decided behaviour. **`docs/DECISIONS.md`
  2026-07-23 "Deployment: M1 shape — single pinned machine, 1 GB volume, fly.toml in repo"**
  is the context for the urgency (credentials arrive via `fly secrets set`), not a second
  covering decision. Neither entry is superseded — both were checked against
  `docs/archive/decisions-superseded.md`.
- **`docs/improvements.md` items on files in `Touches`:**
  - `auth/oauth.py` — **"Stale Streamlit fallback in `auth/oauth.py` credential helpers"**
    (`Type: quality`, open since Audit 001, updated by Audits 041 and 046). **This ticket is
    scoped from that entry.** Its credential-helper half is fully resolved here; its
    "archive the four Streamlit-only functions" half is not (see Out of scope). On handoff,
    do **not** archive the whole entry — trim it to the Streamlit-only-functions remainder
    and note that ticket 051 closed the credential-helper half, following the partial-trim
    precedent Audit 046 praised in ticket 045.
  - `tests/test_oauth_helpers.py` — none. (The `tests/conftest.py` consolidation entry lists
    thirteen test files; `test_oauth_helpers.py` is not one of them, as it needs no session-DB
    harness.)
  - No open `Type: bug` items on either path.
- **`docs/LEARNINGS.md` gotcha that applies:** "Tests must patch the importing module's
  namespace." Use `monkeypatch.delenv("YAHOO_CLIENT_ID", raising=False)` /
  `monkeypatch.setenv(...)` so the env is restored per test; do not mutate `os.environ`
  directly, and do not rely on the developer's `.env` being loaded or absent.
- No Yahoo API call is made by any of these three helpers, so no Yahoo API gotchas apply
  and no live call is needed to verify.
- `auth/` is framework-free pure Python (`docs/ARCHITECTURE.md` Key patterns #6). The new
  code must import nothing beyond the stdlib already imported at the top of the file.

## Verification
- `.venv/bin/python -m pytest tests/test_oauth_helpers.py -v` — the three unset-env cases
  raise `RuntimeError` with the right variable name in the message.
- Negative control: confirm the old failure mode was real. With `streamlit` not installed
  in `.venv` (check with `.venv/bin/python -c "import streamlit"`), reproduce the old failure
  in a scratch copy of the three helpers (no git commands needed — paste the pre-fix bodies
  into a throwaway module) and confirm an unset `YAHOO_CLIENT_ID` yields
  `ModuleNotFoundError`, then confirm the shipped helper yields `RuntimeError`. If `streamlit` *is* installed in the local venv, say so and
  verify by reading the import instead — the production image is what matters, and
  `requirements-web.txt` is the authority there.
- `grep -c streamlit requirements-web.txt` → 0, confirming the premise still holds.
- Full suite: `.venv/bin/python -m pytest tests/` (471 passing as of Audit 046, plus the new
  tests).
- No demo-mode step: this touches no `data/` function and no rendered page. No browser step
  is needed; nothing user-visible changes on the configured path.

## Dependencies
None. Blocks nothing in the ticket queue, but must land **before** the owner runs
`fly deploy` (`docs/ROADMAP.md` § "M1 launch steps that are owner actions", step 3).
