## Orchestration log — 051-oauth-credential-env-fail-fast

**Run started:** 2026-09-17
**Run ended:** 2026-09-17
**Outcome:** completed

### Pre-flight
- Status check: pass (`ready`)
- Type check: pass (`bug`, not `audit`)
- Required-sections check: pass (all eight present)
- `Touches` non-empty: pass (`auth/oauth.py`, `tests/test_oauth_helpers.py`)
- Audit check: pass — `scripts/audit_due.py` reads 0 / 5, AUDIT NOT DUE (checkpoint 046
  ran earlier this session and reset the counter; highest audited ticket 45)
- Architectural-surface coverage: pass — `auth/oauth.py` is on WORKFLOW.md's escalation
  list (Yahoo OAuth flow). The ticket cites `docs/DECISIONS.md` 2026-03-03 "Auth:
  yahoo_oauth not used for the OAuth flow" by date and title in its Notes for the
  Engineer. Verified active, not in `docs/archive/decisions-superseded.md`.

### Model selection
- Engineer: `sonnet` — explicit PM `## Model` field (overrides the heuristic, which would
  have chosen opus for `Process: full` with 2 Touches).
- Test Engineer: `sonnet` — same PM field.
- Reviewer: `opus` — always, never downgraded.

### Subagents spawned (in order)
1. Engineer (round 1)
   - Inputs: `.team/engineer.md`, the ticket, DECISIONS 2026-03-03, the LEARNINGS
     "patch the importing module's namespace" entry, ARCHITECTURE Key patterns #6
   - Output: `tickets/051-done.md`
   - Summary: Replaced the `import streamlit` + `st.secrets[...]` fallback in
     `_client_id`, `_client_secret` and `_redirect_uri` with `raise RuntimeError(...)`,
     each naming its own env var. Added 6 tests (set/unset per helper) using
     `monkeypatch.setenv`/`delenv`. Trimmed the `docs/improvements.md` entry to its
     Streamlit-only-functions remainder rather than archiving it. Left
     `auth/oauth.py:58-117` untouched. Suite: 477 passed (471 baseline + 6).
     Ran the ticket's negative control and observed the old `ModuleNotFoundError`.

2. Test Engineer (round 1, normal QA — `Process: full`)
   - Output: `tickets/051-qa.md`
   - Verdict: **APPROVED**
   - Summary: Re-ran everything independently rather than trusting the handoff.
     Notably re-derived the 471 baseline by `git stash push --keep-index` on the two
     touched files, re-running the suite, then restoring — real evidence rather than a
     quoted number. Extended the negative control to all three helpers where the Engineer
     had reproduced only `_client_id`. Verified `auth/oauth.py:58-117` byte-identical
     against `git show HEAD:auth/oauth.py`. Confirmed the improvements entry was trimmed
     in place, not archived.

3. Reviewer (round 1)
   - Output: `tickets/done/051-review.md`
   - Verdict: **APPROVED** — no blockers, no should-fixes
   - Summary: Scope clean (6 removed / 3 added lines, all inside the three helpers; tests
     purely additive). Architecture clean (no new import at all; `RuntimeError` is a
     builtin, `os` already imported at line 19; the change strictly reduces framework
     coupling). Re-ran the suite: 477 passed. Set Status `done` and moved all four
     artifacts to `tickets/done/`.

### Rulings requested of the Reviewer
1. **Waived Tech Lead consult upheld.** The deleted branch is unreachable wherever `web/`
   runs (`streamlit` absent from `requirements-web.txt`, verified), so every production
   execution that previously reached the fallback already terminated in an exception. Only
   which exception and which message changed; the configured path is byte-identical. The
   invariants DECISIONS 2026-03-03 states are all untouched. The Review 045 precedent maps
   cleanly. Not filed as a finding.
2. **Out-of-scope boundary upheld as the safer call.** Removing the four Streamlit-only
   functions would turn a two-file fix into a five-plus-file teardown across a workstream
   that is not being deployed, adding risk in front of the first `fly deploy` for no
   production benefit. Trim-not-archive on the improvements entry is correct since the
   entry is not fully resolved.

### QA uncertainty resolved by the orchestrator
QA flagged that `docs/ROADMAP.md`, `docs/backlog.md` and several extra `docs/improvements.md`
entries were also modified in the working tree, and could not prove from git state whether
they belonged to this diff — everything sits uncommitted in one tree with no commit
boundary. They do not belong to 051: they are output from this session's concurrent PM
agents (tickets 046-050) and the 046 audit checkpoint, which the orchestrator observed
being written. Passed to the Reviewer as settled fact so it would not re-open the question.

### Files changed
- `auth/oauth.py` (+9 -5, net 4 lines shorter)
- `tests/test_oauth_helpers.py` (+53 -1)
- `docs/improvements.md` — one entry trimmed in place (plus a Reviewer append, below)
- Moved to `tickets/done/`: the ticket, `051-done.md`, `051-qa.md`, `051-review.md`

Cumulative code diff: 62 insertions, 6 deletions. Well under the ~200-line halt heuristic.
Orchestrator verified scope independently via `git diff --stat` before the Reviewer spawn.

### Halt conditions tripped
- None. No fix round was needed.

### Notes for the owner
- **This clears Finding 1 of `.team/audits/046-audit.md`**, the sole item gating that
  checkpoint's NEEDS ATTENTION verdict. `fly deploy` is no longer blocked on it.
- **What the fix actually buys:** a missing secret still fails the login, still shows the
  user "Something went wrong", still returns 500. What changed is that the Fly log now
  reads `RuntimeError: YAHOO_CLIENT_SECRET environment variable not set` instead of
  `ModuleNotFoundError: No module named 'streamlit'` — the difference between a one-minute
  `fly secrets set` and an hour chasing a phantom dependency.
- **New item logged, not blocked on.** The Reviewer found that `_pending_states`
  (`auth/oauth.py:28-32`) is the Streamlit nonce store, but `get_auth_url()` writes to it
  on every call including the FastAPI path, and only `validate_and_consume_state()` prunes
  it — which `web/` never calls. In the Fly process it gains one entry per login attempt
  and is never cleaned. Not a correctness or security problem (nonces are single-use, the
  `oauth_states` table is the authority, growth is immaterial at M1 traffic on a restarting
  machine). Appended to the existing improvements entry so the Streamlit teardown takes
  `_pending_states`, `_NONCE_TTL_SECONDS` and the `get_auth_url()` assignment along with
  the four functions.
- The four Streamlit-only functions at `auth/oauth.py:58-117` remain, deliberately. They
  are still imported by `app.py`, `pages/` and `utils/common.py`.
- Nothing was committed by any subagent. Version control is the owner's.

### Round-1 QA report
Not archived here — no round-2 ran. Full report at `tickets/done/051-qa.md`.
