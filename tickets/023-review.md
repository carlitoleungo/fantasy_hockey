## Code Review — 023

**Files reviewed:**
- `web/middleware/session.py` — `optional_user` added after `require_user`; all failure paths return `None`; `db.commit()` present before stale-session `return None`
- `web/routes/home.py` — `GET /` switched to `Depends(optional_user)` with unauthenticated branch; `POST /leagues/select` retains `Depends(require_user)` unchanged
- `web/templates/home.html` — `{% if leagues is none %}` identity check (not falsy); banner block precedes the auth-state branch; login CTA scoped to the unauthenticated block only
- `tests/test_home_routes.py` — TC5 renamed; TC14/TC15/TC16 added; TC9 tightened to isolate the `<header>` substring
- `docs/improvements.md` — TC9 improvement item closed (in scope per persona rules)

### Scope: CLEAN

All changes are within the ticket's `Touches` list. `web/main.py` and `require_user` are untouched. The `docs/improvements.md` close-out is an explicitly permitted update.

### Architecture: CLEAN

- `optional_user` lives in `web/middleware/session.py` alongside `require_user` — matches the DECISIONS.md entry "Auth: optional_user dependency for semi-public routes (2026-05-30)" exactly.
- `RequiresLogin` is never raised inside `optional_user` — confirmed by reading the full function (lines 102–158). All three failure paths (`no session_id cookie`, `row not found`, `refresh failure`) `return None`.
- `db.commit()` is called at line 137 before the stale-session `return None`, matching the pattern in `require_user` at line 78. The UPDATE-on-refresh-success path also commits (line 151). Both commits are correctly placed.
- The `optional_user` body is a structural mirror of `require_user` with the terminal `raise RequiresLogin()` replaced by `return None`. No security-critical logic was extracted or abstracted away — the two functions stay in sync naturally.
- `{% if leagues is none %}` is a Jinja identity check, not falsy. An authenticated user who returns `leagues=[]` enters the `{% else %}` branch and sees "No active NHL leagues found for your account." — not the login CTA. Correct.
- `POST /leagues/select` (`home.py` line 59) still uses `Depends(require_user)`. Unauthenticated POST returns 302 to `/auth/login`. Confirmed by TC6.
- No framework imports introduced in `data/`, `analysis/`, or `auth/`.
- No new Yahoo API calls.
- DECISIONS.md entry for this pattern is present and includes a `Revisit if` clause. ARCHITECTURE.md Key patterns #2 is not updated here — the ticket explicitly assigns that to the Tech Lead, and the engineer correctly left it untouched.

### Issues

- **nit:** TC14 (`test_home_unauthenticated_shows_login_cta`) line 367 contains `assert "<h1" in body and "Your Leagues" not in body.split("</head>", 1)[1]`. The `"<h1" in body` guard is always true for this page and adds no signal; the `body.split("</head>", 1)[1]` idiom is harder to read than a plain `not in body`. Logged to `docs/improvements.md` as "Simplify redundant assertion in TC14 of `test_home_routes.py`". Not a blocker — the test is correct and passes.

### Verdict: APPROVED

All four acceptance criteria are satisfied. The four Tech Lead gotchas from the ticket notes are all confirmed correct in the implementation. The `{% if leagues is none %}` template check correctly distinguishes unauthenticated (`None`) from authenticated-with-no-leagues (`[]`). Full test suite (332 tests) passes. One nit logged to `docs/improvements.md`; no blockers or should-fixes.
