# 034 — Week Projection roster-breakdown readability

## Status
ready

## Type
feature

## Process
full

## Touches
- web/templates/projection/_matchup.html
- web/routes/projection.py

## Why
The per-team roster breakdown rendered by `_matchup.html` (ticket 030) is hard to
read. Goalie rate stats (GAA, SV%) share the same columns as skater counting
stats, so every skater row shows a meaningless `0.00` under the goalie columns and
every goalie row shows `0.0` under the skater columns — the reader can't tell which
numbers are real. On top of that the table is very wide (one column per enabled
category plus player name / position / team), forcing horizontal scroll on typical
screens. A manager scanning "who is actually contributing this week" currently has
to mentally filter out noise columns and scroll sideways to see them. This ticket
makes the breakdown legible without changing any of the underlying projection math.

## Acceptance criteria
- [ ] For a team roster containing both skaters and goalies, the breakdown makes it unambiguous which stat columns apply to which player type: goalie stats (GAA, SV%, and any other `stat_group == "goaltending"` categories) are visually separated from skater stats. Observable anchor: a **skater** row never displays a computed `0.00` in a goalie-only column — that cell is either absent from the skater section or rendered blank / `–` (and symmetrically for goalies in skater columns).
- [ ] Stat column headers show the Yahoo category **abbreviation** (e.g. `G`, `A`, `Pts`, `SOG`, `GAA`, `SV%`), not the full stat name.
- [ ] Player names are abbreviated to first-initial + surname (e.g. `Connor McDavid` → `C. McDavid`), with the full name preserved in a `title` attribute for hover.
- [ ] Both `GET /projection/matchup?team_key=<key>` (authenticated) and `GET /demo/projection/matchup?team_key=<key>` (demo, no auth) return 200 and render the improved breakdown — demo parity is preserved.
- [ ] The tally cards and the category-comparison table are unchanged, and a spot-checked player's projected stat value matches what ticket 030 rendered (presentation-only change — no recomputation).

## Out of scope
- Any change to the projection math, `analysis/projection.py`, or the data/analysis layer. This is presentation only — do not touch how numbers are computed.
- The tally cards and the category-comparison table at the top of `_matchup.html` — only the **roster breakdown** (the `roster_table` macro / its data) changes.
- `projection/index.html` (the shell) and the shell route — untouched.
- Regenerating or editing the demo snapshot JSON (`demo/data/projection_*.json`).
- Converging the `team_key` / `my_team` query-param aliases (tracked separately in `docs/improvements.md`, "Converge Week Projection matchup route on a single team query-param name") — do not fold that cleanup in here.

## Notes for the Engineer

**Architectural surface — no Tech Lead consult required.** This edits content *inside*
an existing fragment (`_matchup.html`) and adds presentation-only context shaping to
existing route handlers; it does **not** change the HTMX shell + fragment *split*, add a
route, a dependency, or an env var. Per the PM escalation carve-out this is a UI tweak
inside an established pattern. Still conform to these two entries:
- `docs/DECISIONS.md` 2026-05-30 "Feature pages: HTMX fragment pattern with shell + fragment template split" — `_matchup.html` must stay a bare fragment (no `base.html`), returned by the matchup handlers.
- `docs/DECISIONS.md` 2026-04-19 "Feature pages: rank → Tailwind class mapping lives in templates" — presentation mapping (how a stat renders) lives in the template using Tailwind utilities, not in `analysis/`. (Note the *abbreviation* itself is real Yahoo data, not a derived mapping — see below — so it should come from the route, not be re-invented in the template.)

**Separating goalie vs skater stats — options (engineer's choice within the stack):**
Partition robustly on data, not guesswork. The stat category dicts already carry
`stat_group` (`"offense"` for skaters, `"goaltending"` for goalies — confirmed in
`data/client.py:120` and `demo/data/stat_categories.json`). Players are goalies when
`display_position` contains `G` (e.g. `"G"`); skaters otherwise. Do **not** infer
"goalie column" from `_is_rate_stat` alone — goalies also have counting stats (Wins,
Shutouts, Saves) that are `goaltending` group but not rate stats.
- **Option A — two tables/sections per team ("Skaters" / "Goalies"):** each shows only its own columns. Clearest, removes all noise columns; most markup. *Good if you want the cleanest read.*
- **Option B — one table, non-applicable cells blanked:** keep a single table but render `–` (not `0.00`) where a stat's group doesn't match the player's type. Smallest diff, still one wide table. *Good if minimising markup churn.*
- **Option C — Alpine `x-data` skater/goalie tabs:** already sanctioned by ticket 030's notes ("tabs may be an Alpine `x-data` toggle or two stacked tables"). Hides the other group entirely. *Good if vertical space is the concern.*
- A pure visual column-group divider that still shows `0.00` in mismatched cells does **not** satisfy AC1 on its own — combine it with cell-blanking (Option B) if you go that route.
Recommendation: Option A or B for clarity; all three are acceptable.

**Abbreviations (AC2/AC3):**
- Column headers: the route currently passes `enabled_stats` as a list of stat-*name* strings only, and the per-player `stats` dict is keyed by stat name. To show abbreviations, pass the enabled categories' `abbreviation` field through (Yahoo `display_name`, mapped in `data/client.py:119`). Suggested shape: pass the enabled categories as a list of dicts like `{"name", "abbr", "group"}` (name still keys `p.stats[...]`; `abbr` is the header; `group` drives the skater/goalie partition). Keep the `stats` dict keyed by name so the existing `_player_breakdown` output needs no change.
- Player names: abbreviate in the template with Jinja string ops — first token's initial + the remainder of the name (e.g. `p.player_name.split(' ', 1)` → `"{{ first[0] }}. {{ rest }}"`), and put the full `p.player_name` in `title=`. Doing this in the template means it works for demo automatically.

**Demo parity (AC4) — this is why the ticket depends on 031.** Ticket 031 adds the
demo fragment handler (`/demo/projection/matchup`) in `web/routes/projection.py`,
reusing `_matchup.html` unchanged. If you add a new context variable (e.g. the
enabled-categories-with-abbr list, or a skater/goalie split), you MUST pass it from
**both** the authenticated `_matchup_impl` and the demo fragment handler in that same
file — otherwise the demo view will render a broken/empty table. Both handlers live in
`web/routes/projection.py`, so this stays within the two `Touches` files.

**Keep `_matchup.html` demo-reusable:** no hardcoded route URLs in the template (ticket 025/031 lesson).

**Yahoo/data facts (already handled upstream — don't re-derive):** GAA is `stat_id==23`
and is recomputed for last-month inside `data/players.py`; rate-stat identification is
`analysis/projection._is_rate_stat` (`GAA`, `SV%`, `GSAA`); enabled-only via
`is_enabled`. You only need `stat_group`, `abbreviation`, and `display_position` for
this ticket — all already present on the objects the route builds.

## Verification
- **Authenticated:** Log in, open `/projection`, let a team's matchup auto-load. In the roster breakdown: confirm skater rows show no `0.00` under GAA/SV% (blank/`–` or a separate goalies section), and goalie rows show no `0.0` under skater columns. Confirm headers read `G / A / Pts / SOG / GAA / SV%` (abbreviations), and player names read like `C. McDavid` with the full name on hover.
- Confirm the table needs less horizontal scrolling than before (narrower headers + abbreviated names; and, if Option A/C, fewer columns per section).
- Spot-check one player's projected stat value against the pre-change render (or the Streamlit page for the same league/week) — the number must be identical; only its placement/formatting changed.
- Confirm the tally cards and category-comparison table are visually unchanged.
- **Demo (no auth):** In an incognito window open `/demo/projection`, let the default matchup auto-load, and confirm the same improvements render against the Week 14 demo snapshot. Change the selected team; the demo fragment re-renders correctly.
- Run `python -m pytest tests/` (use `python3` if `python` is unavailable in this environment).

## Dependencies
- Ticket 031 (Week Projection demo parity) must complete first — its demo fragment handler must exist so any new context variable is passed consistently to both the authenticated and demo renders of `_matchup.html`.
