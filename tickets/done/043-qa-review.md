## QA + Review Report — 043 (Process: light)

**Ticket:** "Try the demo" CTA on the logged-out home page
**Engineer handoff:** tickets/043-done.md
**QA date:** 2026-09-15

**Process note:** the task that launched this QA session instructed me to read
`tickets/043-done.md` in full before the ticket, which meant I saw the Engineer's "How
to verify" section before writing my own plan (a deviation from the persona's normal
step ordering, driven by the launching prompt, not by my own choice). The plan below is
derived directly from the ticket's Acceptance criteria, which are the same regardless of
when I read the Engineer's verify steps, so I don't believe this weakened the
independence of the verification — but flagging it per the persona's transparency
requirement.

### Test plan (derived from Acceptance criteria)
- AC1: `GET /` with no cookie → expect 200, body contains `href="/demo/overview"` and
  visible text "Try the demo". Fail if link absent or href wrong.
- AC2: same response → the demo link must render next to (not replacing) the login
  button, and be visually secondary (bordered/text vs. filled). This is the one visual
  criterion — assert via rendered Tailwind classes since I have no real browser/screenshot
  available; flag any residual uncertainty as owner-must-verify.
- AC3: `GET /` with a valid session → body must contain no `href="/demo/"` anywhere. Fail
  if any such href present.
- AC4: logged-out `<nav>` must contain only `("/auth/login", "Log in with Yahoo")`. Fail
  if any other href appears in the nav or elsewhere that the existing nav-guard test
  checks.
- AC5: `.venv/bin/python -m pytest tests/` must be green. Fail on any non-zero failures.

### Test results

| # | Acceptance criterion | Result | Observation |
|---|----------------------|--------|-------------|
| 1 | `GET /` unauthenticated returns 200, body has `href="/demo/overview"` link text "Try the demo" | PASS | Verified by test (`test_home_unauthenticated_shows_demo_cta`, green) **and** independently by live curl against `uvicorn web.main:app` on port 8791: response was `STATUS:200` and the fetched body contained `<a href="/demo/overview" class="inline-block ml-3 px-5 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 font-medium">Try the demo</a>`. |
| 2 | Demo link renders alongside login CTA, visually secondary | PASS | Manual walk (visual criterion, not fully test-assertable). From the same live curl fetch: login is `<a href="/auth/login" class="inline-block px-5 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 font-medium">Log in with Yahoo</a>` (filled purple), demo is `border border-gray-300 text-gray-700 ... hover:bg-gray-50` (bordered/text), placed immediately after it with `ml-3` spacing, both inside the same unauthenticated branch. This matches the ticket's own example of "a bordered/text link next to the filled purple button." Caveat: I did not render this in an actual browser/screenshot, so the literal pixel-level visual judgment (contrast, spacing, whether it genuinely reads as "secondary" to a human eye) is **owner-must-verify** — my evidence is the Tailwind class semantics, which strongly and conventionally imply secondary styling, not a rendered image. |
| 3 | `GET /` authenticated has no `href="/demo/"` link | PASS | Covered by test `test_home_authenticated_no_demo_cta` (green), which logs in via a seeded session and asserts `'href="/demo/'` absent from body. Cited as evidence per the light-ticket rule rather than re-driving the same check by hand — this is a direct, correctly-scoped assertion of the AC. |
| 4 | Logged-out `<nav>` unchanged (login-only) | PASS | Covered by test (`tests/test_nav_shell.py::test_logged_out_home_nav_is_login_only`, green, unmodified by this diff) **and** confirmed independently via the same live curl: the `<nav>` block in the fetched HTML is exactly `<nav class="flex items-center gap-4"><a href="/auth/login" ...>Log in with Yahoo</a></nav>` — no other links. |
| 5 | `.venv/bin/python -m pytest tests/` green | PASS | Ran myself: `471 passed, 109 warnings in 1.69s`. Matches the Engineer's reported count exactly. |

### Automated tests
- Command: `.venv/bin/python -m pytest tests/` (run by me, not copied from the handoff)
- Tests run: 471 — passed: 471, failed: 0
- New tests added by Engineer: `tests/test_home_routes.py::test_home_unauthenticated_shows_demo_cta`, `tests/test_home_routes.py::test_home_authenticated_no_demo_cta`. Both inspected directly (see diff below) and both exercised in the full suite run above.
- Supplementary tests added by QA: none needed — AC coverage is complete (AC1 and AC3 each have a dedicated, correctly-scoped test; AC4 reuses an existing unmodified guard test; AC5 is the suite run itself; AC2 is the one genuinely visual criterion, handled by manual walk per the persona).

### Manual verification
- Started `.venv/bin/python -m uvicorn web.main:app --port 8791` in the background.
- `curl -s -o /tmp/home_logged_out.html -w "STATUS:%{http_code}\n" http://127.0.0.1:8791/` → `STATUS:200`.
- Extracted both CTA anchors and the `<nav>` block from the fetched HTML (see Test results table above for literal contents).
- Did not manually drive the authenticated branch through a browser session (cookie/DB setup) — AC3 is already asserted directly and correctly by a green test I ran myself (`test_home_authenticated_no_demo_cta`), which is sufficient independent evidence under the light-ticket rule; re-deriving the identical check by hand would not add assurance.
- Stopped the background uvicorn process afterward (`pkill -f "uvicorn web.main:app --port 8791"`).

### Demo mode (N/A — no new data-layer function)
This ticket adds a link to an **already-live** demo route (`/demo/overview`, shipped and
demo-nav-wired prior to this ticket per the ticket's own Notes). It does not add or
modify any function in `data/`, nor any new route. Step 5 (demo/live parity) does not
apply — there is no new live-only code path to check for a demo counterpart.

### Deviation ruling — TC14 assertion (explicit judgement requested)

**Claim to verify:** the Engineer says the ticket's literal instruction — replace TC14's
assertion with `assert "Your Leagues" not in body` — fails, because `home.html` has a
fixed `{% block title %}Your Leagues{% endblock %}` that renders on every branch.

**Verified independently:**
- `web/templates/home.html:3` — `{% block title %}Your Leagues{% endblock %}`. This is
  unconditional; it is not inside the `{% if leagues is none %}` branch, so it renders
  into `<title>Your Leagues</title>` regardless of auth state.
- `web/templates/base.html:12` — `<body>`, a bare tag with no attributes.
- Confirmed live: the unauthenticated `GET /` response fetched above does not contain
  "Your Leagues" anywhere in the rendered content (only the heading "Fantasy Hockey
  Waiver Wire" appears), but the `<title>` tag in `<head>` does contain it on every
  request regardless of branch (it's a static block, not conditional).
- Therefore `assert "Your Leagues" not in body` against the **full** response text,
  exactly as the ticket and the improvements.md item specify, would indeed always fail
  on the unauthenticated branch too, since `<title>Your Leagues</title>` is always
  present. The Engineer's claim is correct.

**Ruling: the deviation is correct and acceptable.** The Engineer's fix —
`body.split("<body>", 1)[1]` — is scoped past the exact, unconditional `<body>` string
confirmed above in `base.html`, so it reliably excludes `<head>`/`<title>` content and
correctly tests only what the AC actually cares about (no "Your Leagues" heading in the
rendered content). It preserves the sweep's real intent (drop the always-true `"<h1" in
body` guard) without introducing a false failure. I would not have asked for it to be
done differently: an alternative such as searching for `<h1>...Your Leagues` specifically
would be more surgical but functionally equivalent given `<body>` is unique and literal in
this template; the chosen fix is simpler and already green. The Engineer's disclosure of
this deviation (both in `043-done.md` and in the `docs/archive/improvements-closed.md`
resolution note) is exactly the transparency the persona expects — noting for the record,
not treating as a defect.

### Review checks (blocker checklist, Process: light)

| Check | Result |
|---|---|
| Framework import added to `data/`, `analysis/`, or `auth/` | Pass — no changes to those directories at all (`git diff -- data/ analysis/ auth/` is empty). |
| Raw `stat['value']` without `_coerce()`; Yahoo collection indexed without `_as_list()` | N/A — no data-layer code touched. |
| Per-entity Yahoo API loop where a bulk endpoint exists | N/A — no API-calling code touched. |
| New live data function with no demo counterpart | N/A — no new function; the diff links to an already-existing, already-demo-nav-wired route. |
| Contradiction of an active `docs/DECISIONS.md` entry | Pass — nothing in this diff touches session handling, caching, or API-call patterns that any DECISIONS.md entry governs. |
| Diff escapes the ticket's `Touches` list | Pass, with the two authorized exceptions the ticket itself directs. Full diff (`git diff --name-only`) is: `web/templates/home.html`, `tests/test_home_routes.py` (both in `Touches`), plus `docs/improvements.md` and `docs/archive/improvements-closed.md` (moving the three named items is explicitly instructed in the ticket's "Notes for the Engineer"), plus the ticket's own `## Status` line (`ready` → `qa`, ordinary workflow housekeeping). `web/routes/home.py` — the file the ticket explicitly calls out as out of scope — is confirmed untouched (`git diff --stat -- web/routes/home.py` empty; its last commit is unrelated to 043). The diff is exactly the ~3-line template addition plus the two sweep edits the ticket predicted, no more. |

No blockers found. Nothing about this diff smells architectural — it is a single
template anchor tag plus test-file housekeeping; the ticket was correctly classified as
`Process: light`.

### Out-of-scope observations
- `docs/ui-brief.md` is present in the working tree as an untracked file. It is not part
  of this diff (not staged, not modified, no git history), predates this ticket per the
  Engineer's note, and is unrelated to `home.html`/`test_home_routes.py`. Not a scope
  violation — just noting it exists, per the owner's own git-status snapshot at
  conversation start. No action taken on it.
- `docs/improvements.md`'s "Projection route test scaffolding duplicated across three
  test files" item is confirmed still present and untouched (correctly left out of scope
  per the ticket's explicit instruction).

### Issues found
None.

### Verdict: APPROVED

QA passes (all 5 acceptance criteria PASS, one — AC2 — with an explicit
owner-must-verify caveat on the pixel-level visual judgment since I could not render a
real screenshot) and zero review blockers. Status updated to `done`; ticket and its
artifacts moved to `tickets/done/`.
