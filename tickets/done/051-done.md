## Implementation complete — 051

**What I did:**
- Replaced the dead `import streamlit as st; return st.secrets["yahoo"][...]` fallback in
  each of `_client_id()`, `_client_secret()`, and `_redirect_uri()` with a
  `raise RuntimeError("<VAR_NAME> environment variable not set")`, naming the specific
  env var in each helper's own message.
- Added test coverage for both branches (env set → returns value unchanged; env unset →
  `RuntimeError` naming that variable) of all three helpers, asserting the exception type
  is exactly `RuntimeError`.
- Trimmed the `docs/improvements.md` "Stale Streamlit fallback in `auth/oauth.py`
  credential helpers" entry to its Streamlit-only-functions remainder (renamed to
  "Streamlit-only functions remaining in `auth/oauth.py`"), noting ticket 051 closed the
  credential-helper half.

**Files changed:**
- `auth/oauth.py` — `_client_id`, `_client_secret`, `_redirect_uri` (lines 147-160) now
  fail fast with `RuntimeError` instead of falling through to a Streamlit import that
  doesn't exist in the FastAPI deployment. No other function in the file touched; the four
  Streamlit-only functions at lines 58-117 are untouched (their line numbers are
  unaffected since the edit is entirely below them).
- `tests/test_oauth_helpers.py` — added 6 tests (2 per helper) covering the set/unset
  branches for `_client_id`, `_client_secret`, `_redirect_uri`, using
  `monkeypatch.setenv`/`monkeypatch.delenv` per `docs/LEARNINGS.md`'s guidance on
  restoring env state per test.
- `docs/improvements.md` — trimmed the scoping entry to its still-open
  Streamlit-teardown remainder (see below).

**Acceptance criteria status (self-check):**
- [x] `grep -n streamlit auth/oauth.py` inside `_client_id`/`_client_secret`/`_redirect_uri`
      returns no hits — verified: the only three remaining `streamlit` hits in the file are
      at lines 83, 100, 114, inside the out-of-scope Streamlit-only functions
      (`try_restore_session`, `get_session`, `clear_session`).
- [x] Unset `YAHOO_CLIENT_ID`/`YAHOO_CLIENT_SECRET`/`YAHOO_REDIRECT_URI` each raise
      `RuntimeError` naming their own var — verified by
      `test_client_id_raises_when_env_unset`, `test_client_secret_raises_when_env_unset`,
      `test_redirect_uri_raises_when_env_unset` (all pass), and by an ad hoc call to
      `_client_id()` with the env var popped, which printed
      `RuntimeError: YAHOO_CLIENT_ID environment variable not set`.
- [x] With the env var set, each helper still returns the value unchanged — verified by
      `test_client_id_returns_env_value`, `test_client_secret_returns_env_value`,
      `test_redirect_uri_returns_env_value` (all pass).
- [x] `tests/test_oauth_helpers.py` gains coverage for both branches of all three helpers,
      asserting `RuntimeError` (not `ModuleNotFoundError`) — done; each unset-branch test
      uses `type(exc_info.value) is RuntimeError` plus a substring check on the message.
- [x] `.venv/bin/python -m pytest tests/` passes with no new failures — ran it: 477 passed
      (471 baseline per Audit 046 + 6 new tests), 0 failures.

**How to verify (for QA):**
- `.venv/bin/python -m pytest tests/test_oauth_helpers.py -v` — expect 12 passed (6
  pre-existing + 6 new).
- `.venv/bin/python -m pytest tests/` — expect 477 passed.
- `grep -n streamlit auth/oauth.py` — expect hits only at (current) lines 83, 100, 114
  (inside `try_restore_session`/`get_session`/`clear_session`), none inside
  `_client_id`/`_client_secret`/`_redirect_uri`.
- `grep -c streamlit requirements-web.txt` — expect `0`.
- Negative control (ran myself, reproducible): confirmed `streamlit` is not installed in
  `.venv` (`.venv/bin/python -c "import streamlit"` → `ModuleNotFoundError`, matching the
  production image). Pasted the pre-fix bodies of the three helpers into a throwaway
  scratch module, popped `YAHOO_CLIENT_ID` from `os.environ`, and called the throwaway
  `_client_id()`: it raised `ModuleNotFoundError: No module named 'streamlit'`, confirming
  the old failure mode was real. Then called the shipped `auth.oauth._client_id()` under
  the same unset-env condition: it raised `RuntimeError: YAHOO_CLIENT_ID environment
  variable not set`, confirming the fix. No demo-mode or browser step applies — no `data/`
  function or rendered page is touched, and the configured (env-set) path is behaviourally
  unchanged.

**Scope notes:**
- None beyond what's already tracked: the four Streamlit-only functions
  (`validate_and_consume_state`, `try_restore_session`, `get_session`, `clear_session`,
  `auth/oauth.py:58-117`) remain, per the ticket's explicit Out of scope — they're still
  imported by `app.py`, `pages/`, and `utils/common.py`. They're tracked in the trimmed
  `docs/improvements.md` entry for a future Streamlit-teardown ticket to pick up.

**Improvements items closed:**
- "Stale Streamlit fallback in `auth/oauth.py` credential helpers" — the credential-helper
  half is resolved by ticket 051. Per the ticket's explicit instruction, I did not archive
  the whole entry; I trimmed it in place (renamed to "Streamlit-only functions remaining in
  `auth/oauth.py`") to its still-open Streamlit-only-functions remainder, with a note that
  ticket 051 closed the credential-helper half. This follows the partial-trim precedent
  from ticket 045 that Audit 046 praised. Nothing was moved to
  `docs/archive/improvements-closed.md` because the entry is not fully resolved — its
  remainder is still open work.

**Known limitations / things I couldn't fully test:**
- None. All three acceptance-criteria behaviours (env-set pass-through, env-unset
  `RuntimeError` with the right message, and the absence of the Streamlit fallback) are
  covered by automated tests I ran green, plus the negative-control reproduction the
  ticket's Verification section asked for. No UI or demo-mode surface is touched, so no
  manual browser walk applies.
