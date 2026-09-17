## Audit Checkpoint 046 — covering tickets 038, 039, 040, 042, 043, 045

**Date:** 2026-09-15

Weighted count 5.5 / 5 (043 light ½, the other five full 1 each). Ticket 043 landed after the
counter hit 5/5; the owner ruled it non-architectural and authorised it ahead of this audit, and
it is swept here. One dominant theme: **this batch built the deployment, and the documentation
that describes the deployment did not move with it.**

> **The shipped code and config are sound. Every finding below is about documentation, process
> plumbing, or work that was correctly identified and then quietly dropped.** No blocker, no
> architectural violation, no DECISIONS entry contradicted across six tickets.

**TL;DR**

- **Verdict: NEEDS ATTENTION**, on one item only: the `auth/oauth.py` `st.secrets` fallback that
  Audit 041 instructed be taken "before or with ticket 039" was not taken, and `fly deploy` is now
  the next thing that happens. It is a three-line fix. Nothing else here blocks anything.
- **`docs/ARCHITECTURE.md` is further out of date than anyone has recorded.** The known finding was
  "two stale lines"; the reality is that the entire § Directory structure is the April plan and has
  never been reconciled with the repo.
- **The tracker is in good shape, and the process fixes from the last two audits held.** Every
  ticket in this batch closed or explicitly declined its improvements items, and 045's partial trim
  of a half-resolved entry was exactly right.

Full suite re-run during this audit: `.venv/bin/python -m pytest tests/` → **471 passed**, 0 failed.

---

### Tickets reviewed

- 038 — Matchups parquet bloat fix (`data/matchups.py`, `tests/test_matchups.py`). Correct. The
  strongest verification in the batch: the bug was invisible from the return value, and both QA and
  the Reviewer mutation-tested from independent directions to prove the on-disk assertions bite.
- 039 — Deployment config: `fly.toml` + `.dockerignore`. Correct, one fix round (root-anchored
  bytecode globs). Implements DECISIONS 2026-07-23 item for item; secret hygiene verified against a
  real build context rather than by reading the file.
- 040 — Nav shell regression guards (`tests/test_nav_shell.py`). Correct, test-only. Its ablation
  work produced the best evidence yet for the pending `base.html` default flip.
- 042 — Error pages render nav-free (`web/routes/common.py`, `web/main.py`, `base.html`,
  `error.html`, tests). Correct. Implements DECISIONS 2026-07-25 verbatim; blast radius is
  structurally bounded, not merely observed.
- 043 — "Try the demo" CTA on the logged-out home page (`web/templates/home.html`, tests). Correct,
  `Process: light`. Three template lines; the light classification was right.
- 045 — `.dockerignore` secret globs widened to `**/`; `auto_start_machines = true`. Correct. The
  two riskiest properties (root-level `.env` still excluded; the single-machine pin not breached)
  were the two the evidence was spent on.

I re-derived the load-bearing claims rather than accepting them: the current `fly.toml` and
`.dockerignore` on disk, `base.html`'s four-branch nav, `unknown_auth_shell_context()`, the
exception handlers deriving no auth, and the suite.

---

### Prior audit (041) close-out

Six of the nine suggested actions landed. Three did not, and two of those matter.

| 041 action | Status |
|---|---|
| 1. Scope 039; **fold in the `auth/oauth.py` `st.secrets` removal** | Half done. 039 shipped; the `st.secrets` half was **not folded in and was never ticketed**. See finding 1. |
| 2. Scope the error-page nav fix | DONE — became 042, shipped. |
| 3. Tech Lead rules on test-file naming and `tests/conftest.py` | DONE — two DECISIONS entries dated 2026-07-26, and the naming one landed before 040, as instructed. |
| 4. Scope the test consolidation ticket | NOT DONE. No ticket exists; the ~1,489-line duplication and its sub-items are still open in the tracker. Non-urgent, but it was action 4 of 9 and has now skipped a cycle. |
| 5. File the `optional_user` coverage ticket | NOT DONE. Still only a tracker entry. This is the one security-relevant coverage gap and the app is about to be public. |
| 6. Amend the `~200-line` halt heuristic to count non-test source lines | NOT DONE. `.team/orchestrator.md:168` still reads "Cumulative diff exceeds ~200 lines". |
| 7. Carry the accrued visual checks to the next authenticated login | Still accruing (see finding 4). |
| 8. Commit ticket 037's code | Not verified — this audit was instructed not to run git. |
| 9. Fix the `audit_due.py` bullet-list parser | Still open as a `Type: bug` entry; this report uses bullets, so the counter will reset. |

The pattern worth naming: **actions 1, 4 and 5 all shared the disposition "fold this into the next
ticket that touches the area", and all three evaporated.** Actions 2 and 3, which named a ticket or
a decision owner, both landed. The same disposition is what has kept the `.pyc` LEARNINGS item open
across two cycles. Work that is assigned to a hypothetical future ticket does not get done here.

---

### Findings

**1. should-fix (the one item behind the NEEDS ATTENTION verdict) — the Streamlit credential
fallback is still in `auth/oauth.py`, and deployment is now unblocked in front of it.**

`_client_id()`, `_client_secret()` and `_redirect_uri()` (`auth/oauth.py:147-166`) read the env var
and otherwise `import streamlit` and read `st.secrets["yahoo"][...]`. `streamlit` is not in
`requirements-web.txt` (verified), so in the Fly image a missing Yahoo secret surfaces as
`ModuleNotFoundError: No module named 'streamlit'` raised from inside the OAuth callback, which the
500 handler then renders as "Something went wrong." Audit 041's action 1 said to take this before or
with 039. 039 was scoped without it and shipped. `docs/ROADMAP.md` § M1 launch steps now runs
`fly apps create` → `fly volumes create` → `fly secrets set` → `fly deploy` with nothing in front of
it, so the next event on this file is the deploy. A missing secret is the single most likely
misconfiguration on a first deploy, and this converts it into the least legible failure available.
The fix is three `raise RuntimeError("YAHOO_CLIENT_ID environment variable not set")` lines. Tracker
entry updated with this; **it needs its own ticket, not another "fold it in".**

**2. should-fix — `docs/ARCHITECTURE.md` § Directory structure is the April plan, not the repo.**

The open tracker item describes this as two stale lines (the `fly.toml # planned, not yet in repo`
comment and a missing `.dockerignore`). Checking the whole fenced tree at lines 66-103 against the
working tree, it is considerably worse: it lists `routes/leagues.py` and `routes/demo.py`, neither
of which exists; it omits `web/routes/common.py`, `web/routes/overview.py`, `web/routes/home.py`,
`web/templates.py` and `utils/`; and it shows templates as flat files (`waiver.html`,
`leagues.html`, `projection.html`) when the repo uses per-feature subdirectories with `_`-prefixed
fragment partials, and omits `home.html` and `error.html` entirely.

This matters twice over. It is the file the Reviewer persona names as the thing to verify changes
against, so a tree that describes a codebase nobody has ever had weakens every review that cites it.
And the per-feature-directory plus `_partial.html` layout is a real convention with no DECISIONS
entry — the persona lists "a new template-naming pattern" as implicit-decision drift by name — that
ARCHITECTURE.md now actively contradicts, leaving copy-the-neighbour as the only way to learn it.
I have widened the tracker entry to the real scope and added the DECISIONS question to it. Tech Lead
owns the file; this is now an upkeep pass, not a two-line edit.

**3. should-fix — the deployment decision text still attributes the pin to an inert key.** Already
tracked (`min_machines_running = 1` is inert as configured), filed by Review 045, and I confirm both
halves independently: `fly.toml:38` sets it while `auto_stop_machines = false` makes it a no-op, and
DECISIONS 2026-07-23 Option A presents it as the chosen pin mechanism. The actual pin is the absence
of `max_machines_running` / `concurrency` / `[processes]` / `[[services]]` / `regions` plus the
single `[[vm]]`, which I re-verified against the file on disk. Nothing is broken; the risk is a
future reader trusting a guarantee that is not there. Group it with finding 2 as one Tech Lead docs
pass, and resolve it alongside the `auto_stop_machines` deprecation question when `flyctl` is in
hand at `fly config validate` time.

**4. should-fix — the owner-must-verify queue has been growing for nine tickets and nobody owns
draining it.** 038 (warm-cache `/overview` walk), 039 and 045 (`fly config validate`, and the pin
being observable only via `fly status`), 042 (authenticated `/` and `/overview` in a browser), 043
(does the demo CTA actually read as secondary) all end with a correctly-declared item no agent in
this workflow can execute — no Yahoo session, no `flyctl`, no browser, and it is the NHL off-season.
Every one of those declarations is honest and correctly scoped; that is not the problem. The problem
is that they are recorded only in individual ticket artifacts now sitting in `tickets/done/`, and
Audit 041 already carried three of them forward with no effect. The first `fly deploy` plus one
authenticated login clears nearly the whole queue at once. Recommend the PM or owner collect them
into a single checklist on `docs/ROADMAP.md` beside the M1 launch steps, so the deploy session
closes them as a batch instead of each one being rediscovered by a future audit.

**5. nit — front-end CDN dependencies are unpinned, and Tailwind's is a development build.**
`base.html:7-9` pulls Tailwind's in-browser JIT compiler, htmx pinned exactly at 2.0.4, and Alpine
at a floating `3.x.x`. This faithfully implements DECISIONS 2026-04-10, whose `Revisit if` clause is
about UI richness and says nothing about going public. Not a defect, no exposure today; filed to the
tracker and routed to the M1 UI re-design, which will touch every template anyway.

**6. nit — the orchestrator's QA prompt contradicts the Test Engineer persona.**
`.team/orchestrator.md:114` says to read `tickets/NNN-done.md` first; `.team/test-engineer.md:28-32`
says to skim it without anchoring, and derive the plan from the acceptance criteria. QA disclosed
the deviation on 038, 042 and 043 — half this batch — and each time spent a paragraph defending its
independence. No verification was actually weakened (QA compensated with its own harness and
parameters every time, and I agree with the three reviewers who ruled the same way), so this is a
one-line fix that buys back report space and reviewer attention. Filed as `Type: bug`; owner action,
since `.team/*.md` is outside what any agent here edits.

**Scope creep across tickets: none found.** Six tickets, six clean scopes. 038 hit a boundary it was
forbidden to cross, stopped, and flagged it rather than widening — and QA then reproduced the
consequence empirically instead of arguing about it. 040 reverted five mutation probes and proved
`web/` was byte-identical. 045 left the `auto_stop_machines` half of a tracker entry open rather than
archiving the whole thing. That is the process working as designed.

**Verification gaps: none of substance.** This is the best-evidenced batch I have audited. Every AC
marked PASS in this batch carries an observation, and the three that could not be observed here were
declared rather than asserted. Two specific things worth keeping: 038's and 045's negative controls
(reproducing the defect under the old code before claiming the new code fixes it), and 045's
discriminator proving its control was genuinely in force rather than silently falling back.

---

### Implicit decisions surfaced

1. **Per-feature template directories with `_`-prefixed fragment partials.** In force across
   `overview/`, `waiver/` and `projection/`, contradicted by ARCHITECTURE.md's flat listing, and
   recorded in no DECISIONS entry. The 2026-05-30 "Feature pages: HTMX fragment pattern with shell +
   fragment template split" entry ratifies the *split* but not the naming or the directory layout.
   Worth one short entry, or a sentence folded into the ARCHITECTURE upkeep pass in finding 2.
2. **`fly.toml` is now a reviewed architectural surface with two precedents but no written rule.**
   039 and 045 both established, in review prose, that a machine-lifecycle key may be changed without
   a Tech Lead consult when it cannot produce a second machine, while anything touching machine count
   re-opens DECISIONS 2026-07-23. That test is sound and both applications of it were correct. It
   currently lives only in two `tickets/done/` review files. One sentence in the 2026-07-23 entry
   would make the next `fly.toml` ticket decidable without re-deriving it.

Both are for the Tech Lead. Neither is drift that needed blocking: in each case the convention was
reasoned about explicitly and out loud, which is why they are surfaced here rather than flagged as
violations.

---

### DECISIONS.md hygiene

No new gaps. Both entries added since Audit 041 (2026-07-26, tests naming and `tests/conftest.py`)
carry `Revisit if` clauses. The eight pre-2026-04-19 entries lacking them, flagged in audits 024, 032
and 041, remain open and remain low priority; not re-litigated.

Two entries need factual upkeep rather than a hygiene fix: 2026-07-23 (finding 3, the inert pin key)
and 2026-05-31 (the `data/matchups.py` line-number citation that 038 drifted, already tracked). Both
argue for the durable habit of citing symbols rather than line ranges in a decisions log.

---

### Suggested actions (priority order)

1. **(PM)** Scope the `auth/oauth.py` `st.secrets` removal as its own small ticket, and land it
   **before `fly deploy`**. Three `raise RuntimeError` lines plus tests. This is the only action
   gating the verdict. Fold in the ~45 lines of Streamlit-only functions in the same file if the
   Streamlit teardown has not claimed them first.
2. **(Tech Lead)** One docs upkeep pass covering findings 2 and 3: regenerate ARCHITECTURE.md's
   directory tree from the repo, correct DECISIONS 2026-07-23's Option A to attribute the pin to the
   absent autoscaling keys and the single `[[vm]]`, and rule on the two implicit decisions above.
3. **(PM or owner)** Collect the accumulated owner-must-verify items into one checklist beside
   `docs/ROADMAP.md`'s M1 launch steps, so the first deploy and the first authenticated login close
   the whole queue (finding 4).
4. **(PM)** File the two tickets Audit 041 asked for and that did not get filed: `optional_user`
   coverage (action 5 — the one security-relevant coverage gap, and the app is about to be public)
   and the `tests/conftest.py` consolidation (action 4, now with two ratified DECISIONS entries
   waiting on it). Also the one-line `docs/LEARNINGS.md` append for the `.pyc` mutation-probe trap,
   which has now been hit independently three times and has no other route to getting written down.
5. **(Owner, process)** Two one-line edits to `.team/orchestrator.md`: reorder the QA prompt at
   line 114 so it stops contradicting the Test Engineer persona (finding 6), and amend the ~200-line
   halt heuristic at line 168 to count non-test source lines only (Audit 041 action 6, still open).
6. **(Owner, tooling)** The `audit_due.py` bullet-list parser bug is still open. Lowest priority; it
   fails safe, and this report is written in bullets so the counter resets.

---

### Verdict: NEEDS ATTENTION

Six tickets, zero blockers, zero architectural violations, zero scope creep, and the strongest
verification evidence of any batch so far. The verdict is not about the code.

It is about one item: a known, three-line, deploy-critical fix that the previous audit explicitly
routed into ticket 039, which 039 shipped without, and which nothing has picked up since — while the
deployment it protects went from "no `fly.toml` exists" to "owner runs `fly deploy`" in the same
batch. Per the persona, this holds **architectural-surface** scoping only; the M1 UI re-design,
ticket 044, and any non-architectural fix are not blocked. Action 1 clears it.
