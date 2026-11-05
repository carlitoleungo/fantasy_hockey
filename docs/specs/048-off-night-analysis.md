> Written under the old ticket workflow (pre-2026-11-04). References to `tickets/`, `docs/ROADMAP.md`, `docs/backlog.md`, `docs/improvements.md` or persona roles point to files now removed; read them with `git show 409b7ab:<path>`. "Touches" is guidance, not a hard limit.

# 048 — Off-night rule: derive off-nights from a week's slate

## Status
ready

## Type
feature

## Milestone
none

## Touches
- analysis/off_nights.py
- tests/test_off_nights.py

## Why
A waiver-wire pickup is worth more when his games land on nights when most of the league is idle:
those are the nights a manager has empty active slots to fill. The owner settled the definition on
2026-07-23 — an off-night is a night when **fewer than half the teams in the league have games**,
judged relative to the week being viewed. Ticket 047 makes the per-night slate available; this
ticket turns it into the rule, as a pure function the waiver page can call in ticket 049. No user
sees anything change until 049 lands, but the rule is where the judgement lives and it is worth
testing on its own.

## Acceptance criteria
- [ ] `analysis.off_nights.off_nights(slate, week_start, week_end)` returns the sorted list of
      `"YYYY-MM-DD"` dates within `[week_start, week_end]` inclusive on which fewer than half the
      league's teams have games, computed from the slate's per-date team lists (each game already
      contributes two teams in the 047 slate shape).
- [ ] The threshold is a **proportion of teams, not a game count**: `teams_playing * 2 <
      total_teams`. `total_teams` defaults to the number of distinct teams appearing anywhere in
      the supplied slate, and is overridable by keyword, so a 32-team league yields the owner's
      "fewer than ~8 games" without hardcoding 8 or 32 anywhere.
- [ ] A date inside the week with no entry in the slate (no games at all) counts as an off-night,
      and a date outside `[week_start, week_end]` is never returned even when present in the slate.
- [ ] `analysis.off_nights.off_night_games(team_abbr, slate, off_nights)` returns the count of that
      team's games falling on the given off-nights, and `0` for a team absent from the slate.
- [ ] `tests/test_off_nights.py` covers, with hand-built slates: a clear off-night, a clear busy
      night, the exact boundary (exactly half the league playing is **not** an off-night), an empty
      slate (returns every night in the week), and the `total_teams` override.

## Out of scope
- Fetching anything. This module takes a slate in and returns dates out; it makes no HTTP calls
  and imports nothing from `data/`.
- Using off-nights as a ranking input, weight, or sort key. This ticket produces a flag and a
  count for display only. Two neighbouring `docs/backlog.md` entries ("playing this week games
  weighting" and "rank on projected stats rather than raw recent production") own the ranking
  question and explicitly warn against stacking schedule effects — do not pre-empt them.
- Any roster or lineup-conflict logic (Part C of the backlog entry; not scoped, see Notes).
- Route and template changes — ticket 049.

## Acceptance note on the rule
The boundary case is deliberate: the owner said *fewer than half*, so exactly half is a normal
night. With 32 teams, 8 games (16 teams) is not an off-night; 7 games (14 teams) is.

## Notes for the Engineer
- **Read first:** ticket 047 and its `tickets/047-done.md` for the exact slate shape, and
  `analysis/waiver_ranking.py` for the house style of an `analysis/` module (module docstring,
  plain functions, no framework imports).
- **New module, deliberately.** None of `waiver_ranking.py`, `projection.py`, `team_scores.py`,
  `matchup_sim.py` is a natural home — they all take DataFrames of player stats. Off-night
  detection is a schedule rule. Keep it in its own small module with no pandas dependency.
- **Layer purity:** `analysis/` is framework-free pure Python (`docs/ARCHITECTURE.md` Key patterns
  #6) and must not import from `data/` for I/O. Take the slate as an argument.
- **Derive, don't hardcode.** The backlog entry is explicit that "fewer than half of 32" landing
  near 8 games is a consequence, not the rule — deriving `total_teams` from the slate keeps it
  correct if the NHL expands. Do not write `8` or `32` as a literal in the module.
- **DECISIONS.md entries this ticket must conform to** (verified active in `docs/DECISIONS.md`):
  - **2026-07-26 "Tests: one module per feature surface, named for the surface, never for the
    author"** — hence `tests/test_off_nights.py`.
  - **2026-07-26 "Tests: tests/conftest.py is the canonical home for the session-DB and client
    harness"** — not needed here (no client, no DB), so do not add fixtures to `conftest.py` for
    this module.
  - **2026-05-31 "Team process: Engineer owns automated test coverage; QA does not fill gaps"** —
    the test module ships with the code, not after QA asks for it.
  - **2026-07-03 "Dev/test: no runtime past-week override; use captured fixtures + demo mode
    instead"** — tests use hand-built slate dicts; no date-override knob.
  - No demo counterpart is required: this module is pure computation with no live data source, so
    the demo-parity rule in **2026-05-30 "Web routes: demo route pairing policy"** is satisfied by
    047's `load_nightly_slate()` and 049's shared demo/live path.
- **Yahoo API gotchas:** none apply. This module never touches the Yahoo API or `xmltodict`; the
  slate originates from the public NHL JSON API.
- **Open `docs/improvements.md` items on files in `Touches`:** none — both files are new.

## Verification
- `.venv/bin/python -m pytest tests/test_off_nights.py tests/` — new module green, full suite green.
- Walk the boundary by hand in a Python shell: build a 32-team slate with one date carrying 7
  games and another carrying 8, and confirm only the 7-game date is returned.
- Demo-mode steps: not applicable — this ticket adds no data function and no route. Nothing in the
  running app changes; `/waiver` and `/projection/matchup` must render exactly as before.

## Dependencies
- Ticket 047 must complete first (this module consumes the slate shape 047 defines).
