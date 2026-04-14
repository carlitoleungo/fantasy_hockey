## Code Review — 002

**Files reviewed:**
- `tests/test_oauth_helpers.py` — new file; 8 tests for `_stamp_expiry`, `_is_valid`, and nonce lifecycle
- `tests/test_matchups.py` — added 2 tests for prev-week re-fetch logic; added `date` to datetime import
- `tests/test_projection.py` — added `test_is_rate_stat`
- `auth/oauth.py` — added `from __future__ import annotations` for Python 3.9 compatibility

---

### Scope: SCOPE_CREEP_DETECTED

`auth/oauth.py` was not in the ticket's listed files. That said, the change is a single `from __future__ import annotations` line required to make `test_oauth_helpers.py` importable on Python 3.9 (the file uses `X | None` union syntax in signatures). It is zero-behavior-change and the done.md calls it out explicitly. The scope creep is both necessary and benign — flag for awareness, not a blocker.

---

### Architecture: CLEAN

- No framework imports in `data/` or `analysis/`.
- No per-entity API loops introduced.
- No raw stat values read without coercion (tests use in-memory inputs, not API responses).
- No array responses accessed without `_as_list()` normalization.
- No new live data functions added, so no demo counterpart required.

---

### Issues

**Must fix:** None.

**Should fix:**

- **Unused `date` import in `test_matchups.py` (line 11).** The done.md says "`date` was added to the existing `datetime` import," but neither of the two new tests uses `date` — they use `datetime.now(timezone.utc)` instead of the `datetime.combine(date.today(), time.min)` pattern the ticket spec suggested (timezone-aware is actually the better choice). The `date` name is now a dead import. Remove it to keep the import line clean and avoid future confusion.

**Nit:**

- **`from analysis.projection import _is_rate_stat` is inside the test function** (`test_projection.py:219`) rather than at module level with the rest of the imports. Works fine, and pulling a private symbol into the module namespace is mildly unusual, so the local import is defensible — but it's inconsistent with how every other import in the file is handled. Either style is acceptable; pick one.

- **`test_stamp_expiry_returns_same_dict`** is a bonus test not required by the acceptance criteria. It asserts that `_stamp_expiry` mutates and returns the same dict object. Useful regression guard; harmless. Just noting it wasn't in-spec.

- **`test_is_valid_returns_false_within_buffer` timing sensitivity** (flagged in done.md). The test uses a fixed 30-second offset into the 60-second buffer window. In practice it completes in microseconds, so no real risk — but if you ever want a hardened version, `time.time() + TOKEN_EXPIRY_BUFFER_SECONDS - 1` ties the test to the actual constant rather than a hardcoded 30.

---

### Verdict: APPROVED

The three acceptance-criteria gaps are all closed, all 240 tests pass, and there are no architecture violations. The `auth/oauth.py` addition is a legitimate prerequisite, not opportunistic cleanup. The unused `date` import is worth cleaning up before 004 when the same file gets touched again, but it doesn't block merging this ticket.
