# TODO

The single list of open work. Keep each item to a line or two; put long design notes in
`docs/specs/`. Remove items when they ship (git history is the record).

The previous trackers (`docs/ROADMAP.md`, `docs/backlog.md`, `docs/improvements.md`, and
`tickets/`) were folded into this file on 2026-11-04. Their full text is still available:
`git show 409b7ab:docs/backlog.md` (or `ROADMAP.md`, `improvements.md`, `tickets/...`).

## Launch for friends (owner steps)

- [ ] Add the production redirect URI (`https://<app>.fly.dev/auth/callback`) in the Yahoo
      developer console. If it only accepts one URI, create a separate production app.
- [ ] `fly apps create fantasy-hockey-waiver` (or rename `app` in `fly.toml` to match).
- [ ] `fly config validate`, then `fly volumes create data --size 1 --region iad`.
- [ ] `fly secrets set YAHOO_CLIENT_ID=… YAHOO_CLIENT_SECRET=… YAHOO_REDIRECT_URI=…`
- [ ] `fly deploy`; check `fly status`, `/health`, and sign in.
- [ ] While `fly.toml` is open: confirm `auto_stop_machines = false` is still accepted (newer
      flyctl prefers `"off"`), and note that `min_machines_running` has no effect with
      auto-stop off.
- [ ] Decommission the Streamlit Community Cloud app.

## After launch

- [ ] Delete the Streamlit prototype: `app.py`, `pages/`, `utils/`, `validate_api.py`,
      `requirements.txt`, and the Streamlit-only functions plus `_pending_states` in
      `auth/oauth.py`.
- [ ] Add CI: a GitHub Action that runs `pytest` and deploys to Fly on push to `main`.
- [ ] Pin Alpine to an exact version in `web/templates/base.html` (it floats on `3.x.x`).
- [ ] UI redesign, one page at a time, per `docs/ui-brief.md` (what each page does) and
      `docs/design-system.md` (how it looks). Waiver Wire, the app shell and the built
      stylesheet are done; next Overview/Leaderboard, Head-to-Head, Projection, landing and
      league picker. Then drop the `data-theme="light"` default from `base.html`.

## Next features

- [ ] **Off-night pickups**: show which nights a waiver player's team plays and flag off-night
      games. Ready specs, in order: `docs/specs/047-nhl-nightly-slate.md`,
      `048-off-night-analysis.md`, `049-waiver-off-night-column.md`.
- [ ] **Rank waivers on projected stats** (schedule-aware) instead of raw recent production.
      Intended to surface "hidden gems": a 4-game journeyman outranking a 1-game star is the
      point. Likely supersedes a simpler "games this week" ranking weight.
- [ ] **Landing page** for logged-out visitors that explains the app and links to the demo.

## Known issues

- [ ] League settings and stat categories are fetched from Yahoo on every page render
      (2 calls). Fine for friends; cache them before strangers arrive. Analysis in
      `docs/specs/046-scoping-brief-league-settings-cache.md`.
- [ ] `ww_lastmonth` and the NHL schedule are cached per league (or not at all) though they
      are league-independent. A shared cache tier is planned for wider launch.
- [ ] `data/matchups.py` `_merge_into_cache` reads and writes outside the per-league lock, so
      two concurrent calls can briefly drop a week (self-heals on the next call).
- [ ] `data/cache.py` `_atomic_write` doesn't `fsync`, so a machine restart mid-write could
      leave a truncated parquet; stale `.tmp` files are never swept.
- [ ] Waiver ranking: mixing a skater-only and a goalie-only stat buries one position group,
      because NaN composites sink to the bottom (`analysis/waiver_ranking.py`).
- [ ] Leaderboard: weeks with no activity show all-zero rows; tied "worst" cells may not get
      the red highlight.
- [ ] Goalie breakdown table on the projection page omits shared categories like Assists.
- [ ] Error page "Back to home" link doesn't look clickable.
- [ ] Yahoo tokens are stored unencrypted in SQLite and expired sessions are never pruned.
      Acceptable for friends; revisit before opening to strangers.

## Test and code tidy-ups

- [ ] Create `tests/conftest.py` with the shared in-memory session DB and client harness
      (about 13 test files each copy the schema today).
- [ ] Rename the remaining `*_qa.py` test modules for the feature they cover.
- [ ] Deduplicate projection route test scaffolding across three test files.
- [ ] Add direct tests for `optional_user`, including its session-deleting refresh branch.
- [ ] `cache.append()` has no production callers; remove it.
- [ ] Stale docstrings: `data/cache.py` (still describes Streamlit caching) and
      `tests/test_matchups.py` (still describes the append write path).
- [ ] Stale `position` form field in 14 `tests/test_waiver.py` call sites.

## Ideas (not planned)

- Trade analysis: how does my average category rank change if I swap player A for B?
  `analysis/matchup_sim.py` and `team_scores.avg_ranks()` are the starting points.
- Historical player-performance store for the owner's own analysis/ML. Note today's pool
  data is top-25-available only, so it's a biased sample.
- Capture a real past-week Yahoo response set as test fixtures, next time there's live access
  in season.
- Demo snapshot tooling: regenerate `demo/data/` from a live season
  (`scripts/generate_demo_data.py` is the starting point).
- Wider launch (strangers signing in) and paid access. Paid access needs a check of Yahoo's
  commercial terms first.
