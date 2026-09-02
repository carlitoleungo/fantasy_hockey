## Code Review — 042

**Reviewed:** 2026-09-01. QA verdict was APPROVED, so this is the final gate.

**Files reviewed:**
- `web/routes/common.py` — new `unknown_auth_shell_context()`; no-argument sibling to `shell_context()`, returns one key, no logic, docstring cites 2026-07-25. `shell_context()` byte-unchanged.
- `web/main.py` — both handlers spread the helper into their `error.html` context; neither reads a cookie, queries the DB, or touches `request.state`; the `detail` strings and status codes are unchanged.
- `web/templates/base.html` — one leading `{% if auth_state_unknown %}` (empty body) branch inside `<nav>`, plus a three-line comment explaining why it is first. The `demo_mode` branch is re-chained to `{% elif %}`; its body and the authenticated and login branch bodies are unchanged.
- `web/templates/error.html` — one added anchor, `<a href="/" …>Back to home</a>`, after the `detail` paragraph.
- `tests/test_nav_shell.py` — `error_client` fixture + 10 tests appended, 2-line docstring provenance note, one import line widened. Three hunks, all outside `test_base_html_nav_branches`.
- `docs/improvements.md` / `docs/archive/improvements-closed.md` — the mandated item move, with a `**Resolved:** Ticket 042` note.
- `tickets/042-error-page-nav-free.md` — `## Status` line only.

### Scope: CLEAN

The working tree touches exactly the five files in `Touches`, the two mandated documentation
files, and the ticket's own Status line. Nothing else is modified and nothing else is
untracked (`git status --porcelain` shows only `tickets/042-done.md` and `tickets/042-qa.md`
as new). No "while I'm here" cleanup.

Every explicit `Out of scope` item held:

| Out-of-scope item | Verified |
|---|---|
| `{% elif is_authenticated is undefined or is_authenticated %}` (ticket 044) | Present verbatim, `web/templates/base.html:33`; the diff does not touch the condition. |
| Stale `base.html` comment, lines 21-22 | Unchanged, appears as diff context. The new comment is a separate block at lines 24-26. |
| Any auth derivation in the handlers | None. Both handlers are two-key dict literals; `grep` finds no cookie read, DB call, or `request.state` in `web/main.py:49-73`. |
| Restyling / error codes / `detail` strings | Untouched. |
| `tests/conftest.py` consolidation | Untouched; `tests/test_error_handling.py` is absent from the diff. |

The Engineer also correctly declined the dangling cross-reference in the still-open
"Post-036b stale comments" improvements item (its "one remaining beneficiary" claim is now
false) and flagged it for 044 rather than editing an out-of-scope entry. That is the right
call, and 044 should fix both the pointer and the claim.

### Architecture: CLEAN

Checked against `docs/DECISIONS.md` **2026-07-25** "Nav shell: render sites that cannot
resolve a user declare the state unknown and render nav-free; exception handlers never derive
auth", which the ticket instructs be implemented verbatim. All four prescribed steps land as
written, and nothing exceeds them:

| Decision's prescribed shape | Implementation |
|---|---|
| 1. `web/routes/common.py` gains a small sibling to `shell_context()` returning `{"auth_state_unknown": True}`, no user, no logic | `unknown_auth_shell_context()` at `web/routes/common.py:32-43` — exactly that, one return statement. |
| 2. Both handlers spread it into their `error.html` context | `web/main.py:49-73`, both. |
| 3. `base.html` branches on the key **first**, before `demo_mode`, header renders the brand link only | `web/templates/base.html:27`, first branch, empty body; brand link and league-label span sit outside `<nav>` and are untouched. |
| 4. `error.html`'s body gains an explicit "Back to home" link to `/` | `web/templates/error.html:9`. |

Also checked:

- **Key naming** — named for its cause, not its effect, per the decision. No `hide_nav`.
- **Single auth-derivation path (2026-07-03, reaffirmed by 2026-07-25)** — intact. `shell_context()` is untouched and the new helper is a sibling, not a parameter on it.
- **No implicit-decision drift.** The change introduces no new directory, no template-naming pattern, no session handling, and no new dependency. The one new convention (a nav-shell key meaning "unresolvable") is the subject of the covering entry itself, and the entry's own `Revisit if` clause already anticipates the follow-on question (a dataclass once the shell keys pass three or four).
- **Blast radius is structurally bounded**, not just observationally. `grep -rn auth_state_unknown` over the tree returns writers in exactly one place (`web/routes/common.py:43`), reachable only from the two exception handlers. No route and no template can set the key, so no other page can enter the new branch.
- Pure-layer rules are not engaged: no file under `data/`, `analysis/`, or `auth/` is touched, no Yahoo call is added, no `stat['value']`, no `_as_list()` site, and no new live data function, so no `data/demo.py` counterpart is owed.

### Verification adequacy: adequate, and re-derived independently

I did not take QA's or the Engineer's results on trust for the load-bearing claims:

- `.venv/bin/python -m pytest tests/` from a purged `__pycache__` → **469 passed** in 2.08s.
- Rendered `base.html` directly through the Jinja environment across the four context shapes. This is the assertion the whole ticket rests on, and it discriminates: `{}` → `/overview, /waiver, /projection, /auth/logout` (the 044 default, deliberately unchanged); `{"auth_state_unknown": True}` → `[]`; `{"demo_mode": True}` → the four demo links; `{"is_authenticated": False}` → `/auth/login` only. The new branch changes exactly one context and no other.
- Read both handlers and the template diff in full for derivation; there is none.

QA's coverage of the ACs is real rather than nominal. The two proofs that matter are the
byte-identity check with and without a cookie (AC2) and the demonstration that it is not
vacuous — QA's stronger form, `GET /` returning 502 with the seeded cookie against 200 with a
garbage cookie, proves the app genuinely resolves that session, so a handler that *did* derive
had a real user available and would have rendered differently. The nav assertions are scoped
to the `<nav>` and header regions via `_nav_links` / `_header_left` rather than to the whole
body, which is what the ACs require, and the "Back to home" assertion splits on `</header>` so
the link is proved to be in the body.

**On QA's disclosed persona deviation** (reading `042-done.md` in one pass, so the Engineer's
"How to verify" was seen before their plan was written): **it does not compromise the
verification here.** The risk that rule guards against is anchoring, QA reproducing the
Engineer's proof rather than probing independently. That did not happen: QA's plan is written
against the ACs with its own failure conditions, several of them stricter than the Engineer's
(a "Back to home" link located in the header counts as a fail); the harness is independent
(own driver module outside the repo, own DB copy, own port, own route paths); and it adds two
evidence sources the Engineer had no access to — a headless-Chrome render at 1280 px and
375 px, and a rendered pre-042 baseline from `git show HEAD:` proving the new tests fail on the
old markup. The deviation would matter more on a ticket whose ACs were subjective. These are
objectively checkable, and I re-derived the central ones myself above, which is the third
independent confirmation. Disclosing it rather than hiding it is the behaviour the process
wants; no re-run needed.

### Issues

- **blocker:** none.
- **should-fix:** none.
- **nit:** the `{% if auth_state_unknown %}` branch has an empty body, which is unusual Jinja and reads at a glance like an editing accident. The comment immediately above it does the work of explaining why, and the decision prescribes exactly this ordering, so it stays as-is. Recorded only so a future reader does not "tidy" it into `{% if not auth_state_unknown %}` wrapping the rest — that inversion would collide with ticket 044's edit.

**Ruling on the QA nit referred to me — the "Back to home" link not reading as clickable:
follow-up, not a should-fix here.** Three reasons. It satisfies AC3 as written (visible, an
anchor to `/`). The ticket puts restyling the error page explicitly out of scope, so fixing it
here would be the scope creep this review exists to catch. And the classes are copied verbatim
from the `base.html` nav links, so changing them in this one spot would *create* an
inconsistency rather than remove one — the affordance question belongs to whatever settles a
single link style for the whole app. Blocking a ticket on a nit is also explicitly outside the
Reviewer's remit. Logged to `docs/improvements.md` and pointed at the M1 UI re-design
(`docs/ROADMAP.md` § M1 item 3), which is the right owner. QA's second observation, the 375 px
horizontal clipping on the error body, is folded into that entry: QA attributed it to pre-042
markup by rendering the old templates at the same width, and 042 in fact reduces the overflow.

### Security and data: CLEAN

No tokens, session IDs, or PII reach the response or any log — both handlers still return
fixed `detail` strings and do not surface the exception. No user input is consumed by the new
code path (the helper takes no arguments). No SQL is added. No new dependency. No cookie
attributes are touched. Notably, the change *reduces* what the error page asserts about the
visitor rather than adding a second place that decides whether a request is authenticated,
which is the security property the 2026-07-25 entry was written to protect.

### Verdict: APPROVED

Status set to `done`; `tickets/042-*.md` moved to `tickets/done/`.

**New `docs/improvements.md` entry written by this review:**
- "Error page \"Back to home\" link does not read as clickable" (`Type: quality`, `web/templates/error.html` line 9) — assigned to the M1 UI re-design; includes QA's pre-existing 375 px clipping observation.

**Carried forward for the PM / owner, not blocking:**
- **Owner-must-verify, from QA:** live authenticated `/` and `/overview` were not walked in a browser (no Yahoo OAuth round trip is possible from this environment, and every session in the dev `app.db` is expired). The mocked tests cover those pages and the new branch is structurally unreachable from them, so AC4 is not open — but a ten-second look next time the owner is logged in closes the one link no automated test can.
- **Ticket 044** should, when it retires the `base.html` comment, also correct the "Post-036b stale comments" improvements entry: its pointer now aims at an archived item, and its "one remaining beneficiary, `error.html`" claim became false with this ticket (the count is now zero).
- The open improvements item about the mutation-probe `.pyc` staleness trap has now been independently hit by the Engineer, QA, and this review. Third vote for writing it into `docs/LEARNINGS.md`.
