# Code Review — 045

**Reviewer date:** 2026-07-27
**QA verdict on entry:** APPROVED (`tickets/045-qa.md`) — precondition satisfied before I started.

**Files reviewed:**
- `.dockerignore` — `.env` + `.env.*` → `**/.env*`, `*.pem` → `**/*.pem`, four-line comment added in the Secrets block. Nothing else moved.
- `fly.toml` — `auto_start_machines = false` → `true`. One line, nothing else.
- `docs/improvements.md` — `.dockerignore` entry removed; `fly.toml` entry trimmed in place to its `auto_stop_machines` half.
- `docs/archive/improvements-closed.md` — `.dockerignore` entry appended with a `**Resolved:** Ticket 045` note.

### Scope: CLEAN

The diff is `Touches` (`.dockerignore`, `fly.toml`) plus the two tracker files the ticket's close-out bullet prescribes. No bonus features, no drive-by cleanup.

**On the missing git baseline.** Both config files are untracked, so there is no committed baseline and `git diff` shows nothing for them — the Engineer and QA both stated this plainly rather than implying a diff was checked, which is the right call. I reconstructed the change from the pre-edit scratch copies (`dockerignore.ORIG` 873 B, `fly.toml.ORIG` 1587 B, both matching the sizes QA 039 independently recorded for the 039-landed files) and diffed them against the current files myself:

| File | Diff against pre-045 copy |
|---|---|
| `fly.toml` | Exactly one changed line: `auto_start_machines = false` → `true`. 1587 → 1586 bytes. The header comment block (lines 7-12) intact. |
| `.dockerignore` | Exactly two hunks: `.env` + `.env.*` → four comment lines + `**/.env*`; `*.pem` → `**/*.pem`. The pre-existing bytecode comment is unchanged in content, displaced from lines 21-22 to 24-25 purely by the four inserted lines. |

Every out-of-scope boundary the ticket drew holds, verified rather than taken on report:

| Boundary | Verified |
|---|---|
| `auto_stop_machines` stays `false` | `fly.toml:36` — `false`, boolean. Deprecation half correctly left open. |
| No `--workers` | Absent from `fly.toml`; `Dockerfile:12` `CMD` still single-worker. |
| No machine/region/autoscaling knob | Recursive walk of the parsed document for `max_machines_running` / `concurrency` / `processes` / `services` / `regions` → no hits. |
| `Dockerfile` untouched | Tracked and absent from `git status --porcelain`. |
| `docs/ARCHITECTURE.md` untouched, its entry left open | Tracked and clean; entry still open in `docs/improvements.md`. |
| `.streamlit/` patterns left root-anchored | `.dockerignore:11-13` unchanged. |
| `[build] dockerfile` redundancy left alone | `fly.toml:21-22` unchanged. |
| No exclusions added for Streamlit prototype files | No `app.py` / `pages` / `requirements.txt` / `validate_api` pattern in `.dockerignore`. |
| No `docs/LEARNINGS.md` append | Tracked and absent from `git status --porcelain`. |

### Architecture: CLEAN

**The load-bearing question — can `auto_start_machines = true` breach the single-machine pin? No.** I re-derived this rather than accepting the ticket's citation of my own 039 enumeration.

The covering decision is `docs/DECISIONS.md` "Deployment: M1 shape — single pinned machine, 1 GB volume, fly.toml in repo" (2026-07-23). Its correctness requirement is *never more than one machine*, because a Fly volume binds to one machine (a second splits sessions, forks the parquet cache, and voids the per-league `threading.Lock`). Auto-start is not a route to a second machine: Fly Proxy's autostart wakes an **existing stopped** machine when a request arrives and has no capability to provision one — machine creation requires `fly scale count`, `fly machine clone`, or a deploy, none of which this key touches. Restarting the same machine reattaches the same volume, so none of the three failure modes the decision names can arise. `tickets/done/039-review.md` § "On the single-machine pin" reached the same conclusion by exhaustive enumeration ("Not a route at all … Safe at either value"), and I still agree with it on re-reading.

The flip also touches none of the entry's other commitments (1 GB volume at `/data`, `fly.toml` in repo, no CI), and `false` was never a decided value — no DECISIONS entry, no 039 acceptance criterion and no ROADMAP step names it. `true` is Fly's own default, and auto-start with `auto_stop_machines` off is the coherent combination Fly documents as the restart safety net. So this corrects an undecided implementation detail toward the platform default, in the direction that serves the entry's stated purpose ("M1 requires the app deployed at a stable HTTPS URL"). **No superseding DECISIONS entry is needed and no Tech Lead consult is owed.**

No other architectural surface is in play: no `data/`, `analysis/`, or `auth/` code, no route, no dependency, no new convention. The pure-layer, `_coerce`/`_as_list`, bulk-endpoint, and demo-parity rules have no surface here.

### Security and data: CLEAN — and strictly improved

The change is a strict widening of secret exclusions, so the only way it could hurt is by over-excluding a needed runtime file. It does not.

I built my own throwaway `FROM busybox` + `COPY . /ctx` context over the real repo root, Dockerfile written outside the repo:

- Depth sweep for `.env`, `.env.*`, `*.pem`, `.env*` → **empty**. Non-vacuous: the host carries `./.env` (914 bytes of real Yahoo credentials) and `./.env.example` (755 bytes).
- **Root coverage preserved** — the regression the ticket named worst-case: `ABSENT /ctx/.env`, `ABSENT /ctx/.env.example`. The host `.env` is untouched at 914 bytes.
- Nothing over-excluded: `web/main.py`, `requirements-web.txt`, `db/schema.sql`, `fly.toml` all `PRESENT`. Whole context **74 files** and the same **19 top-level entries** QA 039 and QA 045 recorded, so the file set did not move.
- No `*.pyc`, `app.db*`, `.git`, or `.cache` in the context.

I also ran my own nested-probe test with a control, in a scratch tree that never touched the repo, to confirm the glob semantics independently of the repo's file layout:

| Patterns | Context contents |
|---|---|
| Pre-045 (`.env`, `.env.*`, `*.pem`) | `web/.env`, `web/deep/nest/.env.local`, `web/certs/key.pem`, `.envrc` all **present** — the defect, reproduced |
| Post-045 (`**/.env*`, `**/*.pem`) | all of the above **absent**, root `.env` / `.env.example` / `root.pem` absent, `web/main.py` still present |

`fly.toml` remains free of credentials: `[env]` is exactly `{DB_PATH, CACHE_DIR, HTTPS_ONLY}`, `force_https = true`, and the header comment still states that Yahoo credentials go through `fly secrets set`. No cookie-attribute or auth surface is touched.

### Verification adequacy: strong

QA's negative control is the part that matters and it is better than the Engineer's. Two things raise it above a checklist pass:

1. **It never mutated the repo's `.dockerignore`.** QA used BuildKit's per-Dockerfile sidecar to run the pre-change patterns, so both config files are provably unmodified across the QA session and the "did the restore work?" question does not arise.
2. **It added a discriminator so the control could not be misread.** A silently ignored sidecar would fall back to the repo file and also produce "probes absent", making absence ambiguous. QA asserted that pre-change semantics were genuinely in force (probes present *while* root `.env`, `.git`, `tests/`, `docs/`, `.venv/` were still excluded and `pyc=0`) — a combination only the pre-change pattern list can produce.

AC4's `fly.toml` assertions were re-derived by me: **11/11 pass** (`auto_start_machines is True` and `isinstance(..., bool)`, `auto_stop_machines is False`, `min_machines_running == 1` with `type(...) is int`, exactly one `[[vm]]`, exact top-level / `[env]` / `[http_service]` key sets, no forbidden autoscaling key anywhere in the document). AC5: `.venv/bin/python -m pytest tests/` → **459 passed**. No new tests were added, correctly — `.dockerignore` and `fly.toml` are consumed by Docker and Fly, not by Python, so there is no importable path to assert build-context membership from pytest. This is not a missing-AC-coverage return under DECISIONS 2026-05-31.

The four owner-must-verify items QA listed are the right residue, honestly scoped: `fly config validate` never ran, the restart behaviour is post-deploy-only, Fly's remote builder was not proven to apply `**/` identically to local Docker 29.6.2, and the real production image was never built. AC4 correctly scopes this ticket to TOML validity and value correctness.

### Improvements tracker re-curation: CONFIRMED

I own this file, so I checked the end state by inspection rather than by diff. QA is right that `git diff docs/improvements.md` shows only additions and no deletion — I confirmed why: `git show HEAD:docs/improvements.md` contains none of the three entries Review 039 wrote (no `.dockerignore`, no `fly.toml`, no `docs/ARCHITECTURE.md` entry), because 039's review was never committed. So 045's removal is invisible against `HEAD` by construction, and the two entries appearing as additions are Review 039's work correctly left in place. Not a missing edit, and not scope creep.

| Required end state | Confirmed |
|---|---|
| `.dockerignore` entry out of the active tracker | Gone. No `## Closed` items section was created; the pointer paragraph at the file's foot is untouched. |
| Archived with a `**Resolved:**` note naming 045 | `docs/archive/improvements-closed.md:149-154`, appended after the 040 entry, same structure as its siblings. The note describes the pattern change, the comment, the negative control, and the 74-file / 19-entry property. Accurate on every claim I checked. |
| `fly.toml` entry trimmed in place, item 2 deleted, item 1 kept | Retitled to "`fly.toml`'s `auto_stop_machines` boolean form should be re-checked with `flyctl` in hand", `File:` narrowed `fly.toml:36-38` → `fly.toml:36`, lead-in now describes one key, plus an `**Update — ticket 045 resolved the auto_start_machines half**` note. No residue of the two-key framing. |

The surviving `auto_stop_machines` text is faithful to Review 039's original reasoning — boolean accepted by both older and newer flyctl, so switching to `"off"` blind trades a deprecation warning for an unvalidated schema risk in a file nothing here can lint; resolve it at `fly config validate` time. Nothing was lost in the trim, and the tracker no longer asserts `auto_start_machines = false`, which was the point.

### Issues

- **blocker:** none.
- **should-fix:** none.
- **nit:** the new comment lives in the Secrets block and names `.pem` in its text, but `**/*.pem` sits 25 lines away under `# Local TLS certs` with no note of its own. Someone editing line 35 in isolation will not see the explanation. The ticket sanctioned exactly this placement, so it is in spec; a future editor of the file could add a one-line back-reference. Not worth a tracker entry.
- **nit / no action:** `**/.env*` is genuinely wider than the three literals it replaced — it also excludes `.envrc` (direnv) and anything else beginning `.env`, which I confirmed empirically. Zero effect today (nothing in the repo matches beyond `./.env` and `./.env.example`, and no runtime file starts with `.env`), and excluding a direnv file from a production image is desirable anyway. Both the Engineer and QA surfaced this unprompted, which is the right instinct. It is the shape the ticket prescribed; implementing it as written was correct.

**Observation for the owner, not a defect.** With `auto_start_machines = true`, `fly machine stop` is no longer a way to hold the app down — the next request wakes it. Suspending or scaling to zero is now the way to take the app offline deliberately. This is the intended consequence: the ticket names manual stop as one of the failure modes it wants auto-recovered.

### New `docs/improvements.md` entry written by this review (1)

- **`min_machines_running = 1` is inert as configured, and DECISIONS 2026-07-23 names it as the pin mechanism** (`Type: quality`, `fly.toml:38` + `docs/DECISIONS.md:170`). Filed because the trim removed the last place this was recorded. QA 039 spotted the inertness and Review 039 noted the corollary, but both lived inside the `auto_start_machines` half of the entry that 045 has now resolved and deleted. The pin's actual mechanism is the absence of autoscaling keys plus the single `[[vm]]`, not this key. Tech Lead owns `DECISIONS.md`; routable with the existing ARCHITECTURE and DECISIONS upkeep entries.

### Verdict: APPROVED

A small ticket done carefully. The two riskiest things about it — that widening a secret glob could silently stop excluding root-level `.env`, and that a lifecycle-key flip on an architectural surface could breach the single-machine pin — were both the things the Engineer and QA spent their evidence on, and both hold under my independent re-derivation. No blockers, no should-fixes, and the tracker re-curation is correct.

Status set to `done`; ticket and artifacts moved to `tickets/done/`.
