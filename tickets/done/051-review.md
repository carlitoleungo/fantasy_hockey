## Code Review — 051

**Files reviewed:**
- `auth/oauth.py` — three credential helpers' dead Streamlit fallback replaced with a self-naming `RuntimeError`; nothing else in the file touched.
- `tests/test_oauth_helpers.py` — purely additive: import-list extension plus 6 tests, 2 per helper.
- `docs/improvements.md` — the one entry the ticket's Notes instruct, trimmed in place rather than archived.

### Scope: CLEAN

The diff is exactly the ticket's `Touches` list plus the explicitly instructed
`docs/improvements.md` trim. I confirmed line by line that `auth/oauth.py`'s diff is six
removed lines and three added ones, all inside `_client_id`/`_client_secret`/`_redirect_uri`;
`get_auth_url`, `exchange_code`, `make_session`, `_stamp_expiry`, `_is_valid`, the module
docstring and the import block are untouched. `tests/test_oauth_helpers.py` modifies no
existing test.

The other working-tree changes QA flagged as unattributable (`docs/ROADMAP.md`,
`docs/backlog.md`, the Audit-046-sourced `docs/improvements.md` entries) are confirmed by the
Orchestrator as concurrent PM and audit output from tickets 046-050, observed as they were
written. That is settled and outside this review's scope. QA was right to flag what it could
not prove from git state; no further action.

### Architecture: CLEAN

- **Pure-layer purity (`docs/ARCHITECTURE.md` Key patterns #6).** The new code adds no import
  at all. `raise RuntimeError(...)` is a builtin; the surviving `os.environ` lookups use the
  stdlib `os` already imported at line 19. The change strictly *reduces* the file's framework
  coupling by deleting three lazy `import streamlit` statements. The three remaining
  `streamlit` hits (lines 83, 100, 114) are all inside the out-of-scope Streamlit-only
  functions and are lazy in-body imports that the FastAPI process never reaches.
- **No Yahoo API surface.** These helpers make no HTTP call, so the per-entity-loop, `_coerce`,
  `_as_list` and demo-counterpart checks do not apply.
- **No DECISIONS conflict, and no new convention established.** `docs/DECISIONS.md` 2026-03-03
  "Auth: yahoo_oauth not used for the OAuth flow" is active (not in
  `docs/archive/decisions-superseded.md`) and its stated invariants — the redirect-based flow,
  the hand-rolled `requests` implementation, and the "check validity → refresh → return
  session" pattern — are all untouched.

**On the waived Tech Lead consult (ruling requested).** The PM's reasoning holds. The consult
requirement exists to stop a change altering decided behaviour on a load-bearing surface
without the Tech Lead ruling. This change cannot alter decided behaviour: the deleted branch is
unreachable in the only environment that runs `web/`, because `streamlit` is absent from
`requirements-web.txt` (verified: `grep -c streamlit requirements-web.txt` → 0), so every
production execution of these helpers that previously reached the fallback terminated in an
exception, and the only change is which exception and which message. The configured path is
byte-for-byte identical. The Review 045 precedent maps cleanly: there too an active decision
covered a change that could not move the decided behaviour, only its legibility. Nothing here
creates a new convention needing a DECISIONS entry. Not a finding.

**On the out-of-scope boundary (ruling requested).** Leaving the four Streamlit-only functions
(`auth/oauth.py:58-117`) was the right call, and for a deploy-critical ticket it is the
*safer* call, not the lazier one. They are imported by `app.py`, `pages/` and
`utils/common.py`; removing them turns a two-file fix into a five-plus-file teardown across a
workstream that is not being deployed, and every line of that teardown is risk added in front
of the first `fly deploy` with no production benefit — the functions cost nothing at runtime
because `web/` never calls them and their Streamlit imports are in-body. QA's byte-identical
check against `git show HEAD:auth/oauth.py` for lines 58-117 is the right evidence and it came
back clean.

The trimmed `docs/improvements.md` entry preserves the remaining work adequately: it keeps the
Audit 001 provenance, names all four functions and their three importers, states the file
range, and records why 051 declined them. The partial-trim-not-archive handling is correct —
the entry is not fully resolved, so it stays out of `docs/archive/improvements-closed.md`. One
gap, which I have now closed myself in that entry rather than sending back (see Issues).

### Verification adequacy

Strong, and better than the handoff it was checking. QA independently reproduced the 471
baseline via `git stash`/`pop` instead of trusting the Engineer's number, and extended the
negative control from the one helper the Engineer exercised to all three, so the old
`ModuleNotFoundError` failure mode is confirmed real per helper rather than by analogy. The
unset-branch tests assert `type(exc_info.value) is RuntimeError` rather than `isinstance`,
which is the right assertion here: it is what rules out the exact regression the ticket
exists to prevent, since `ModuleNotFoundError` would pass an `isinstance(..., Exception)`
check and a broader `RuntimeError` catch would not distinguish them. The tests use
`monkeypatch.setenv`/`delenv`, per the `docs/LEARNINGS.md` env-restoration guidance, so they
do not depend on whether the developer's `.env` is loaded. I re-ran the full suite myself:
477 passed, 0 failures.

The absent items are correctly absent: no demo counterpart (no `data/` function), no browser
walk (no rendered page), no fixture (no Yahoo response parsed).

### Security and data

No secret value is logged or included in any message — each `RuntimeError` names the *variable*
(`YAHOO_CLIENT_SECRET`), never its value, which is the correct side of that line and is what
makes this message safe to surface in a Fly log. No token, session ID or PII enters the diff.
No cookie attributes, SQL, or HTTP input boundary is touched. No new dependency.

Worth stating plainly, since this is the last change before deploy: the fix does not make a
missing secret *recoverable*, it makes it *legible*. A missing `YAHOO_CLIENT_SECRET` still
fails the login, still renders "Something went wrong" to the user, and still returns 500. What
changes is that the Fly log now reads `RuntimeError: YAHOO_CLIENT_SECRET environment variable
not set` instead of `ModuleNotFoundError: No module named 'streamlit'`, which is precisely the
difference between a one-minute `fly secrets set` and an hour chasing a phantom dependency.
That is the whole ask and the ticket delivers it.

### Issues

- **nit:** The three helpers are now near-identical three-line bodies, and a
  `_require_env("YAHOO_CLIENT_ID")` helper would collapse them. I am explicitly *not* asking
  for it. The ticket prescribed keeping the existing shape, three literal branches are easier
  to step through than one indirection, and the per-variable message is the point of the
  ticket — a shared helper is where a generic message tends to creep back in. Take it or
  leave it; leaving it is fine.

- **logged, not blocking:** While verifying that `auth/` imports nothing new, I found a small
  live-path leftover the trimmed entry did not cover. `_pending_states`
  (`auth/oauth.py:28-32`) is the Streamlit single-process nonce store, but `get_auth_url()`
  writes to it on *every* call including the FastAPI path, and the only code that removes
  entries is `validate_and_consume_state()`, which `web/` never calls. In the Fly process the
  dict therefore gains one entry per login attempt and is never pruned. It is not a
  correctness or security problem — the nonces are single-use, the `oauth_states` DB table is
  the authority, and the growth is immaterial at M1 traffic on a machine that restarts
  regularly — and it is outside this ticket's scope, so I have not asked for a change. I
  appended it to the existing `docs/improvements.md` Streamlit-remainder entry so the teardown
  that removes the four functions also takes `_pending_states`, `_NONCE_TTL_SECONDS` and the
  one assignment in `get_auth_url()`. That is the gap in the trim I mentioned above; it is now
  closed.

No blockers. No should-fixes.

### Verdict: APPROVED

Ship it, then deploy. This clears Finding 1 of `.team/audits/046-audit.md`, which was the sole
item gating that checkpoint's NEEDS ATTENTION verdict.

**`docs/improvements.md` changes made by this review:**
- Appended an `**Update (Review 051)**` paragraph to "Streamlit-only functions remaining in
  `auth/oauth.py`", folding `_pending_states` into that teardown's scope. Appended in place
  alongside the concurrent Audit 046 / PM edits already in the working tree; no existing entry
  was rewritten or removed.
