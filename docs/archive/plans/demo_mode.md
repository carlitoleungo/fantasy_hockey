> **Archived — Streamlit prototype only.** This plan was written and implemented for the original Streamlit prototype. The data generation scripts (`scripts/generate_demo_data.py`, `scripts/extend_demo_data.py`) and the static demo data files (`demo/data/`) are preserved and still used. The `data/demo.py` loader functions are also preserved. However, the integration points described here — `app.py`, `utils/common.py`, `pages/03_waiver_wire.py`, `pages/04_week_projection.py` — are all Streamlit-specific and have been replaced. See [`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md) for how demo mode will work in the FastAPI stack (`web/routes/demo.py`).

---

# Demo Mode — Implementation Plan

## Context
Users without a Yahoo account, in the off-season, or with no eligible categories league (scoring_type != "head") currently hit a dead end. Demo mode lets them explore the full app using pre-saved static data. It surfaces at two points: the login page (before any OAuth) and the post-auth "no leagues" dead end. Zero API calls are made during demo mode.

---

## What we found in the codebase

**app.py (lines 54–152):** Unauthenticated path is a single `_login_page()` function with a Yahoo link button. The "no leagues" dead end is `st.warning("No active leagues found…")` at line 248. Auth guard is `"tokens" not in st.session_state`.

**utils/common.py:** `require_auth()` checks for `tokens` in session state. `load_matchups()` calls `matchups.get_matchups(session, ...)` and `get_current_week(session, ...)` — both need a live session.

**pages/03_waiver_wire.py:** Data is fetched lazily on category toggle. Key API calls:
- Line 260: `get_stat_categories(_require_session(), league_key)` — one-time per league
- Line 299: `fetch_season_pool(_require_session(), ...)` — once per (position, stat) combo
- Line 347: `fetch_lastmonth_batch(_require_session(), ...)` — on "Last 30 days" selection
- Line 370: `scoreboard_module.get_current_matchup(_require_session(), ...)` — schedule fetch
The `ww_season_pool` accumulates incrementally; `ww_fetched_sorts` tracks which (position, stat) combos are in the pool.

---

## Files to create

### `scripts/generate_demo_data.py`
One-time script, run offline, outputs committed static files. Not run at startup.

```
# At top of script — configure these once:
TARGET_LEAGUE_KEY = "nhl.l.XXXXX"
SNAPSHOT_WEEK = 14  # mid-season week to use as "now"
OUTPUT_DIR = Path("demo/data")
```

Steps:
1. Authenticate via existing `auth/oauth.py` flow (reuse token from `.streamlit/`)
2. Fetch `get_user_hockey_leagues(session)` → find target league, save to `league_meta.json`
3. Fetch matchup history weeks 1–SNAPSHOT_WEEK via `data/matchups.py` → save as `matchups.parquet`
4. Fetch waiver wire player pool (all positions) with season stats using `data/players.py:fetch_season_pool()` for each stat category → merge → save as `players_season.parquet`
5. Fetch last-30-day stats for that player pool via `data/players.py:fetch_lastmonth_batch()` → save as `players_lastmonth.parquet`
6. Fetch stat categories via `data/client.py:get_stat_categories()` → save as `stat_categories.json`
7. Save a `games_remaining.json` mapping team_abbr → int (snapshot of that week's games left)

Output files are committed to `demo/data/`. Script is not run at startup.

---

### `data/demo.py`
Pure Python, no Streamlit. Loads static files from `demo/data/`.

```python
DEMO_LEAGUE_KEY = "demo.l.000000"  # fake key used in session state
DEMO_WEEK = 14

def get_demo_league_context() -> dict:
    """Return a fake league dict matching the shape of get_user_hockey_leagues() output."""
    meta = _load_league_meta()
    return {
        "league_key": DEMO_LEAGUE_KEY,
        "league_id": "000000",
        "league_name": meta["league_name"],
        "scoring_type": "head",
        "season": meta["season"],
        "start_week": meta["start_week"],
        "start_date": meta["start_date"],
        "end_date": meta["end_date"],
    }

def get_matchups() -> pd.DataFrame:
    """Load matchups from demo/data/matchups.parquet."""

def get_current_week() -> int:
    """Return DEMO_WEEK."""

def get_stat_categories() -> list[dict]:
    """Load from demo/data/stat_categories.json."""

def load_season_pool() -> pd.DataFrame:
    """Load full player pool from demo/data/players_season.parquet."""

def load_lastmonth_pool() -> pd.DataFrame:
    """Load from demo/data/players_lastmonth.parquet."""

def get_games_remaining() -> dict[str, int]:
    """Load from demo/data/games_remaining.json."""
```

Note: function signatures deliberately **do not** accept `session` or `league_key` — these are static loaders, not API mirrors. The pages call them conditionally based on `demo_mode`.

---

## Files to modify

### `utils/common.py`

**`require_auth()`:** Add demo mode bypass at the top:
```python
def require_auth() -> str:
    if st.session_state.get("demo_mode"):
        return st.session_state["league_key"]  # set during demo init in app.py
    # ... existing tokens check unchanged
```

**`load_matchups()`:** Add demo mode branch:
```python
def load_matchups(league_key: str) -> None:
    if st.session_state.get("demo_mode"):
        if st.session_state.get("matchups_league_key") != league_key:
            from data.demo import get_matchups, get_current_week
            st.session_state["matchups_df"] = get_matchups()
            st.session_state["matchups_league_key"] = league_key
            st.session_state["current_week"] = get_current_week()
        return
    # ... existing session-based fetch unchanged
```

---

### `app.py`

**Auth check (line 54):** Widen the condition:
```python
if "tokens" not in st.session_state and not st.session_state.get("demo_mode"):
```

**Demo init helper** (new function, called from two places):
```python
def _enter_demo():
    from data.demo import get_demo_league_context
    ctx = get_demo_league_context()
    st.session_state["demo_mode"] = True
    st.session_state["leagues"] = [ctx]
    st.session_state["league_key"] = ctx["league_key"]
    st.rerun()
```

**Login page (inside `_login_page()`, after the Yahoo button):** Add a "Try Demo" button below the existing link button:
```python
_, col, _ = st.columns([3, 2, 3])
with col:
    if st.button("Try Demo", use_container_width=True, key="login_demo_btn"):
        _enter_demo()
```

**No-leagues dead end (line 247–248):** Replace the bare `st.warning` with:
```python
else:
    st.warning("No active fantasy categories leagues found for your account.")
    if st.button("Try Demo", key="noleague_demo_btn"):
        _enter_demo()
```

**Demo banner + exit button** (add inside the `with st.sidebar:` block, after the brand header, when demo_mode is True):
```python
if st.session_state.get("demo_mode"):
    st.info("Demo mode — viewing sample data")
    if st.button("Exit demo", use_container_width=True, key="sidebar_exit_demo"):
        for k in ("demo_mode", "leagues", "league_key", "matchups_df",
                  "matchups_league_key", "current_week"):
            st.session_state.pop(k, None)
        st.rerun()
```

**League selector:** Wrap the scoring-type warning block (lines 226–245) with `if not st.session_state.get("demo_mode"):` since the demo league is always `scoring_type = "head"`.

**Leagues load (lines 163–184):** Wrap with `if not st.session_state.get("demo_mode"):` to skip live API fetch when in demo mode (leagues already set by `_enter_demo()`).

---

### `pages/03_waiver_wire.py`

Add a demo init block immediately after the `inject_css() / require_auth() / load_matchups()` guards (around line 38–45):

```python
demo_mode = st.session_state.get("demo_mode", False)

if demo_mode:
    # Pre-populate all pools and stat categories from static demo data so
    # no API calls are triggered by filter interactions.
    from data.demo import (
        load_season_pool, load_lastmonth_pool,
        get_stat_categories as demo_stat_cats, get_games_remaining,
    )
    if st.session_state.get("ww_pool_league") != league_key:
        st.session_state["ww_season_pool"] = load_season_pool()
        st.session_state["ww_lm_pool"] = load_lastmonth_pool()
        st.session_state["ww_fetched_sorts"] = {"__demo__"}  # non-empty sentinel
        st.session_state["ww_pool_league"] = league_key
        st.session_state["ww_pool_position"] = "All"
    if st.session_state.get("ww_stat_cats_league") != league_key:
        st.session_state["ww_stat_categories"] = demo_stat_cats()
        st.session_state["ww_stat_cats_league"] = league_key
    if "ww_games_remaining" not in st.session_state:
        st.session_state["ww_games_remaining"] = get_games_remaining()
        st.session_state["ww_schedule_league"] = league_key
```

Guard each API-calling block with `if not demo_mode`:

| Line | Block | Guard |
|------|-------|-------|
| 259–262 | `get_stat_categories()` call | `if not demo_mode and ...` |
| 296–310 | `fetch_season_pool()` call inside the for-loop | `if not demo_mode and sort_key not in fetched_sorts` |
| 330–355 | `fetch_lastmonth_batch()` call | wrap with `if not demo_mode` |
| 363–398 | `scoreboard_module / schedule_module` calls | wrap with `if not demo_mode` |

---

## File layout after changes

```
demo/
  data/
    league_meta.json
    matchups.parquet
    players_season.parquet
    players_lastmonth.parquet
    stat_categories.json
    games_remaining.json
scripts/
  generate_demo_data.py
data/
  demo.py              ← new
utils/
  common.py            ← modified
app.py                 ← modified
pages/
  03_waiver_wire.py    ← modified
```

Other pages (`01_league_overview.py`, `04_week_projection.py`) load data via `load_matchups()` in `utils/common.py` which already handles demo mode — no changes needed there unless those pages make additional direct API calls.

---

## Verification

1. Run `streamlit run app.py` with no credentials configured → login page shows "Try Demo" button
2. Click "Try Demo" → app loads with demo league in sidebar, persistent "Demo mode" banner, no API calls
3. Navigate to Waiver Wire → full player pool loads immediately (no spinner on category toggle)
4. Toggle stat categories → filters apply client-side; no network activity
5. Toggle position filter → pool re-filters correctly
6. Switch to "Last 30 days" → pre-loaded lastmonth data used, no fetch
7. "Exit demo" clears session and returns to login page
8. Authenticate with real Yahoo account, get no-leagues result → "Try Demo" button appears in sidebar
9. Run `scripts/generate_demo_data.py` offline → all 6 files written to `demo/data/`; re-run is idempotent
