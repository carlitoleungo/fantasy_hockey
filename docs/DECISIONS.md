# Decisions

The choices currently in force, one line each with the reason. The full reasoning (options
considered, "revisit if" triggers) is in `docs/archive/decisions-history.md`, under the same
titles; superseded entries are in `docs/archive/decisions-superseded.md`.

When you make a new architectural choice, add a line here (newest at the top of its section)
and, if it needs more than a few sentences, a full entry in the history file.

## Stack and runtime

- **FastAPI + Jinja2 + HTMX + Alpine + Tailwind via CDN, no JS build** (2026-04-10). The UI is
  tables and filters, so a Python-only stack keeps `data/` and `analysis/` directly importable.
- **Responsive web only; no native app or PWA for now** (2026-04-10).
- **Single uvicorn worker on one pinned Fly machine with a 1 GB volume at `/data`** (2026-04-10,
  2026-07-23). A Fly volume belongs to one machine, so a second machine would split sessions
  and the cache, and the in-process cache locks only work with one process. Change all of
  these together or not at all.

## Auth and sessions

- **Server-side sessions: tokens in SQLite, opaque `session_id` cookie (30 days)** (2026-04-10).
  Tokens never leave the server; SQLite needs no extra service.
- **OAuth is hand-rolled with `requests` in `auth/oauth.py`; `yahoo_oauth` is not used**
  (2026-03-03). That library only supports an interactive terminal flow.
- **`optional_user` for pages that serve both logged-in and logged-out visitors** (2026-05-30);
  `require_user` for protected pages.

## Cache

- **The parquet cache stays keyed by league, not user** (2026-07-23). It holds no user-private
  data, and per-user keys would multiply Yahoo calls. Writes use temp-file + `os.replace()`,
  and read-modify-write paths take a per-league `threading.Lock`.
- **League-independent data (`ww_lastmonth`, NHL schedule) should move to a shared tier
  (`CACHE_DIR/_shared/`) before wider launch** (2026-07-23). Not built yet.
- **Matchups: the current week is always re-fetched; earlier weeks are delta-fetched using
  `max(week)` in the cached data** (2026-05-31, 2026-03-03).

## Yahoo API usage

- **Prefer collection endpoints**: one `/league/{key}/teams/stats;type=week;week={w}` call for
  all teams (2026-03-23); per-stat bulk fetches for waiver and projection, never per-player
  (2026-05-30).
- **`type=lastmonth` is the only param that returns last-30-day player stats** (2026-03-23).
  Available players take 2 calls per page of 25 (season list, then batch lastmonth).
- **`_as_list()` and `_coerce()` in `data/client.py` are the shared fixes for xmltodict
  single-item lists and `'-'`/`None` stat values** (2026-03-03, 2026-03-23).
- **Unknown and display-only stats are silently skipped** (2026-03-03).
- **Leagues are filtered on `game_code == "nhl"`, not the game name** (2026-03-03).

## Web layer

- **Feature pages are a full-page shell plus HTMX fragments** (2026-05-30); shared route helpers
  live in `web/routes/common.py` (2026-05-30).
- **Live and demo handlers share one compute/render helper** so they cannot drift (2026-07-03);
  `web/routes/projection.py` `_render_matchup` is the reference. Every authenticated feature
  route needs a `/demo/*` counterpart, or a TODO entry if it is deferred (2026-05-30).
- **The nav comes from one shared shell-context helper; pages that can't resolve the user
  (error pages) render nav-free, and exception handlers never derive auth** (2026-07-03,
  2026-07-25).
- **Rank-to-colour mapping lives in templates, not `analysis/`** (2026-04-19). `analysis/`
  may return shade *levels* (0–4, `shade_levels`); templates map them to classes (2026-11-05).
- **Waiver Wire shows games remaining in every period, and the current week's dates are kept
  in memory per league for the day** (2026-11-08, owner's call). One scoreboard call per league
  per day instead of one per filter change; safe because of the single worker. The "Rest of
  week" period projects last-30 per-game pace × games left (`project_rest_of_week`), the same
  maths as the Projection page, from data Last 30 days already fetches.
- **The visual design system is `docs/design-system.md`** (2026-11-05). Tailwind is a built
  stylesheet, not the CDN: sources in `web/styles/`, output committed to `web/static/app.css`
  so the Docker image needs no Node. Fonts are self-hosted from `web/static/fonts/` (no Google
  Fonts call). Redesigned pages follow the system light/dark setting; pages not yet redesigned
  pin light via `base.html`'s `theme_attr` block, because their gray utility classes are
  unreadable on dark tokens.
- **The selected league is stored in the session (`user_sessions.league_key`); routes stay
  bare (`/overview`, `/waiver`, `/projection`)** (2026-04-19).

## Analysis

- **Ties rank with `method='min'` (both tied teams get the better rank)** (2026-03-03).
- **`LOWER_IS_BETTER` lists both full stat names and abbreviations** (2026-03-03).

## Testing

- **Fixtures only, no live Yahoo calls in tests.** There is no runtime "pretend it's week N"
  override; use captured fixtures and demo mode for off-season work (2026-07-03).
- **Patch the importing module's namespace** (e.g. `data.leagues._get`, not `data.client._get`)
  (2026-03-03). See `docs/LEARNINGS.md` for the demo-route exception.
- **Test modules are named for the feature they cover; the shared session-DB/client harness
  belongs in `tests/conftest.py`** (2026-07-26). The conftest has not been created yet (see
  `docs/TODO.md`).
