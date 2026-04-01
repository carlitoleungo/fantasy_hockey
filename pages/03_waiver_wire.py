"""
Page 3 — Waiver Wire

Ranks available (unrostered) players by composite score across user-selected
stat categories. Supports position filtering and toggling between season and
last-30-day stats.

Full fidelity design implementation:
  - Position filter as pill buttons (All / C / LW / RW / D / G)
  - Stat categories as toggle chip buttons
  - Custom paginated HTML table (25 rows per page)
  - Refresh CTA button

Data is fetched on first category selection (not page load) and cached in
session state for the rest of the session.
"""

from datetime import date

import pandas as pd
import streamlit as st

from analysis.projection import _is_rate_stat
from analysis.team_scores import stat_columns
from analysis.waiver_ranking import filter_by_position, rank_players
from auth.oauth import clear_session, get_session
from data import schedule as schedule_module, scoreboard as scoreboard_module
from data import cache as cache_module
from data.client import get_stat_categories
from data.players import fetch_lastmonth_batch, fetch_season_pool
from utils.common import load_matchups, require_auth
from utils.theme import inject_css

# ---------------------------------------------------------------------------
# Guards + data load
# ---------------------------------------------------------------------------

inject_css()
league_key = require_auth()
load_matchups(league_key)

df_matchups = st.session_state.get("matchups_df")
if df_matchups is None or df_matchups.empty:
    st.info("No league data available yet — the season may not have started.")
    st.stop()

all_stat_cols = stat_columns(df_matchups)

# Abbreviation lookup — needed early so chip buttons can show short labels.
_STAT_FALLBACK_ABBREV: dict[str, str] = {
    "Goals": "G",
    "Assists": "A",
    "Points": "Pts",
    "Plus/Minus": "+/-",
    "Penalty Minutes": "PIM",
    "Power Play Goals": "PPG",
    "Powerplay Goals": "PPG",
    "Power Play Assists": "PPA",
    "Powerplay Assists": "PPA",
    "Power Play Points": "PPP",
    "Powerplay Points": "PPP",
    "Short Handed Goals": "SHG",
    "Short Handed Assists": "SHA",
    "Short Handed Points": "SHP",
    "Shots on Goal": "SOG",
    "Hits": "HIT",
    "Blocked Shots": "BLK",
    "Blocks": "BLK",
    "Wins": "W",
    "Save Percentage": "SV%",
    "Goals Against Average": "GAA",
    "Saves": "SV",
    "Shutouts": "SO",
    "Goals Against": "GA",
    "Faceoffs Won": "FOW",
}
_stat_cats = st.session_state.get("stat_categories", [])
_stat_abbrev: dict[str, str] = (
    {c["stat_name"]: c["abbreviation"] for c in _stat_cats if "stat_name" in c and "abbreviation" in c}
    or _STAT_FALLBACK_ABBREV
)

# ---------------------------------------------------------------------------
# Session-level lazy helpers
# ---------------------------------------------------------------------------

_session = None  # initialised on first authenticated API call


def _require_session():
    """Return an authenticated requests.Session, stopping the page on expiry."""
    global _session
    if _session is None:
        _session = get_session()
        if _session is None:
            st.error("Your session has expired. Please log in again.")
            clear_session()
            st.stop()
    return _session


def _merge_pool(existing: pd.DataFrame, new_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Union two DataFrames on player_key, keeping existing rows on conflict.

    New rows whose player_key is already present are discarded — the existing
    data is preferred so we don't overwrite season stats with a different sort's
    copy of the same player.
    """
    if new_rows.empty:
        return existing
    if existing.empty:
        return new_rows.copy()
    fresh = new_rows[~new_rows["player_key"].isin(existing["player_key"])]
    return pd.concat([existing, fresh], ignore_index=True)


# ---------------------------------------------------------------------------
# Page header (title left, refresh button right)
# ---------------------------------------------------------------------------

st.markdown(
    '<h1 class="fh-page-title">Waiver Wire</h1>'
    '<p class="fh-page-subtitle">Find the best available players for your weakest categories.</p>',
    unsafe_allow_html=True,
)
instr_col, refresh_col = st.columns([10, 2])
with instr_col:
    st.markdown(
        '<p class="fh-page-instructions">Pick the stats you want to improve, then narrow by position if needed. '
        'Players are ranked by combined performance across your selected categories — lower composite rank is better. '
        'Toggle between season totals and last 30 days to separate consistent producers from hot streaks. '
        'Refresh pulls live availability from Yahoo.</p>',
        unsafe_allow_html=True,
    )
with refresh_col:
    refresh = st.button("↻", key="ww_refresh", type="primary")

# ---------------------------------------------------------------------------
# Controls panel — three sections side by side:
#   [Position Filter | Rank By] | [Stat Categories]
# ---------------------------------------------------------------------------

positions = ["All", "C", "LW", "RW", "D", "G"]
if "ww_position" not in st.session_state:
    st.session_state["ww_position"] = "All"

# Initialise toggle state for each stat (default: all off)
for stat in all_stat_cols:
    key = f"ww_cat_{stat}"
    if key not in st.session_state:
        st.session_state[key] = False

# ── Position filter | Rank by | Stat categories — all side by side on desktop
pos_col, rank_col, cat_col = st.columns([1, 1, 2])

with pos_col:
    st.markdown('<span class="fh-control-label">Position Filter</span>', unsafe_allow_html=True)
    # Two rows of 3 position buttons
    row1_cols = st.columns(3)
    row2_cols = st.columns(3)
    for i, pos in enumerate(positions):
        col = row1_cols[i] if i < 3 else row2_cols[i - 3]
        is_active = st.session_state["ww_position"] == pos
        with col:
            if st.button(
                pos,
                key=f"ww_pos_{pos}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state["ww_position"] = pos
                st.session_state.pop("ww_page", None)
                st.rerun()

with rank_col:
    ranking_period = st.radio(
        "Rank by",
        options=["Season", "Last 30 days"],
        horizontal=False,
        key="ww_period",
    )

with cat_col:
    st.markdown('<span class="fh-control-label ww-cat-marker">Categories</span>', unsafe_allow_html=True)
    CHIPS_PER_ROW = 3
    for row_start in range(0, len(all_stat_cols), CHIPS_PER_ROW):
        row_stats = all_stat_cols[row_start : row_start + CHIPS_PER_ROW]
        # Always create CHIPS_PER_ROW columns so every chip is the same width,
        # even on the last (possibly shorter) row.
        chip_cols = st.columns(CHIPS_PER_ROW)
        for i, stat in enumerate(row_stats):
            is_on = st.session_state[f"ww_cat_{stat}"]
            abbrev = _stat_abbrev.get(stat, stat)
            with chip_cols[i]:
                if st.button(
                    abbrev,
                    key=f"ww_chip_{stat}",
                    type="primary" if is_on else "secondary",
                    use_container_width=True,
                ):
                    st.session_state[f"ww_cat_{stat}"] = not is_on
                    st.session_state.pop("ww_page", None)
                    st.rerun()

# Derive selected categories from toggle state
selected_cats = [s for s in all_stat_cols if st.session_state.get(f"ww_cat_{s}")]

if not selected_cats:
    st.markdown(
        '<p style="font-family:\'Manrope\',sans-serif;font-size:0.875rem;color:#89938f;'
        'margin:1.5rem 0;text-align:center;">'
        'Select one or more stat categories above to rank available players.</p>',
        unsafe_allow_html=True,
    )
    st.stop()

position_group = st.session_state.get("ww_position", "All")
# Pass position to the API for specific filters so top-N results are drawn
# from that position pool, not the overall pool where positions may be sparse.
api_position: str | None = None if position_group == "All" else position_group

# ---------------------------------------------------------------------------
# Pool state management
# ---------------------------------------------------------------------------
# The pool accumulates incrementally as the user selects stat categories.
# It is invalidated (cleared) on position change, league change, or Refresh.

def _pool_valid() -> bool:
    return (
        "ww_season_pool" in st.session_state
        and st.session_state.get("ww_pool_league") == league_key
        and st.session_state.get("ww_pool_position") == position_group
    )


def _clear_pool() -> None:
    for k in ("ww_season_pool", "ww_lm_pool", "ww_fetched_sorts",
               "ww_pool_league", "ww_pool_position", "ww_page"):
        st.session_state.pop(k, None)


if refresh or not _pool_valid():
    _clear_pool()
    st.session_state["ww_pool_league"] = league_key
    st.session_state["ww_pool_position"] = position_group

if "ww_fetched_sorts" not in st.session_state:
    st.session_state["ww_fetched_sorts"] = set()
if "ww_season_pool" not in st.session_state:
    st.session_state["ww_season_pool"] = pd.DataFrame()
if "ww_lm_pool" not in st.session_state:
    st.session_state["ww_lm_pool"] = pd.DataFrame()

# ---------------------------------------------------------------------------
# Ensure stat categories are loaded (needed for stat_name → stat_id mapping)
# ---------------------------------------------------------------------------

if st.session_state.get("ww_stat_cats_league") != league_key:
    cats = get_stat_categories(_require_session(), league_key)
    st.session_state["ww_stat_categories"] = cats
    st.session_state["ww_stat_cats_league"] = league_key

stat_cats = st.session_state["ww_stat_categories"]
id_to_name: dict[str, str] = {
    c["stat_id"]: c["stat_name"] for c in stat_cats if c["is_enabled"]
}
name_to_id: dict[str, str] = {
    c["stat_name"]: c["stat_id"] for c in stat_cats if c["is_enabled"]
}

# ---------------------------------------------------------------------------
# Fetch season pool slices for any newly-selected categories
# ---------------------------------------------------------------------------

fetched_sorts: set = st.session_state["ww_fetched_sorts"]
season_pool: pd.DataFrame = st.session_state["ww_season_pool"]

for stat in selected_cats:
    sort_key = (position_group, stat)
    if sort_key in fetched_sorts:
        continue  # already in pool

    sort_id = name_to_id.get(stat)
    if sort_id is None:
        continue  # stat not found in league's scoring categories

    # Check disk cache first (skipped on explicit Refresh)
    if not refresh and not cache_module.is_player_pool_stale(league_key, position_group, stat):
        cached_df = cache_module.read_player_pool(league_key, position_group, stat)
        if cached_df is not None and not cached_df.empty:
            season_pool = _merge_pool(season_pool, cached_df)
            fetched_sorts.add(sort_key)
            continue

    # Cache miss or stale — fetch from Yahoo API
    with st.spinner(f"Fetching top players by {_stat_abbrev.get(stat, stat)}…"):
        try:
            new_df = fetch_season_pool(
                _require_session(), league_key, sort_id, id_to_name,
                position=api_position,
            )
        except Exception as e:
            st.error(f"Failed to fetch player data: {e}")
            st.stop()

    if not new_df.empty:
        cache_module.write_player_pool(league_key, position_group, stat, new_df)
    season_pool = _merge_pool(season_pool, new_df)
    fetched_sorts.add(sort_key)

st.session_state["ww_season_pool"] = season_pool
st.session_state["ww_fetched_sorts"] = fetched_sorts

if season_pool.empty:
    st.info("No available players match the selected filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Fetch lastmonth stats lazily — only when the user requests that ranking
# ---------------------------------------------------------------------------

lm_pool: pd.DataFrame = st.session_state["ww_lm_pool"]

if ranking_period == "Last 30 days":
    pool_keys = set(season_pool["player_key"].tolist())
    lm_keys = set(lm_pool["player_key"].tolist()) if not lm_pool.empty else set()
    missing_keys = list(pool_keys - lm_keys)

    if missing_keys:
        # Check disk cache first (skipped on explicit Refresh)
        if not refresh and not cache_module.is_lastmonth_stale(league_key):
            disk_lm = cache_module.read_lastmonth_cache(league_key)
            if disk_lm is not None and not disk_lm.empty:
                cached_for_missing = disk_lm[disk_lm["player_key"].isin(missing_keys)]
                if not cached_for_missing.empty:
                    lm_pool = _merge_pool(lm_pool, cached_for_missing)
                    missing_keys = [
                        k for k in missing_keys
                        if k not in set(cached_for_missing["player_key"].tolist())
                    ]

        # Fetch any remaining players not in disk cache
        if missing_keys:
            with st.spinner("Fetching last 30-day stats…"):
                try:
                    new_lm = fetch_lastmonth_batch(
                        _require_session(), missing_keys, id_to_name
                    )
                except Exception as e:
                    st.error(f"Failed to fetch recent stats: {e}")
                    st.stop()
            if not new_lm.empty:
                cache_module.upsert_lastmonth_cache(league_key, new_lm)
                lm_pool = _merge_pool(lm_pool, new_lm)

    st.session_state["ww_lm_pool"] = lm_pool

# ---------------------------------------------------------------------------
# Schedule: games remaining this week (fetched once per session)
# ---------------------------------------------------------------------------

if (
    "ww_games_remaining" not in st.session_state
    or st.session_state.get("ww_schedule_league") != league_key
    or refresh
):
    try:
        current_week = int(df_matchups["week"].max())
        sb = scoreboard_module.get_current_matchup(
            _require_session(), league_key, current_week
        )
        week_end = date.fromisoformat(sb["week_end"])
        from_date = max(date.today(), date.fromisoformat(sb["week_start"]))
        st.session_state["ww_week_end"] = week_end
        st.session_state["ww_from_date"] = from_date
        st.session_state["ww_games_remaining"] = {}
        st.session_state["ww_schedule_league"] = league_key
    except Exception as e:
        st.warning(f"Could not load week schedule: {e}")

# Update games_remaining for any team abbrs newly seen in the pool
week_end = st.session_state.get("ww_week_end")
from_date_val = st.session_state.get("ww_from_date")
games_remaining_map: dict = st.session_state.get("ww_games_remaining", {})

if week_end and from_date_val and not season_pool.empty:
    all_abbrs = set(season_pool["team_abbr"].dropna().unique())
    new_abbrs = list(all_abbrs - set(games_remaining_map.keys()))
    if new_abbrs:
        try:
            new_map = schedule_module.get_remaining_games(
                new_abbrs, from_date_val, week_end
            )
            games_remaining_map.update(new_map)
            st.session_state["ww_games_remaining"] = games_remaining_map
        except Exception:
            pass  # non-fatal; games_remaining column will show 0

# ---------------------------------------------------------------------------
# Build base_df + rank
# ---------------------------------------------------------------------------

if ranking_period == "Last 30 days" and not lm_pool.empty:
    # Join metadata from season pool with lastmonth stats
    meta_cols = ["player_key", "player_name", "team_abbr", "display_position", "status"]
    season_meta = season_pool[[c for c in meta_cols if c in season_pool.columns]]
    base_df = season_meta.merge(lm_pool, on="player_key", how="inner")
else:
    base_df = season_pool

# Position filter is already applied at the API level (api_position).
# filter_by_position is still called for "All" (no-op) and as a safety net.
filtered_df = filter_by_position(base_df, position_group)
ranked_df = rank_players(filtered_df, selected_cats)

if ranked_df.empty:
    st.info("No available players match the selected filters.")
    st.stop()

ranked_df["games_remaining"] = ranked_df["team_abbr"].map(
    lambda a: games_remaining_map.get(a, 0)
)

# "Show all stats" toggle
show_all = st.checkbox("Show all stats", value=False, key="ww_show_all")

meta_cols = ["player_name", "team_abbr", "display_position", "status", "games_remaining"]
if ranking_period == "Last 30 days" and "games_played" in ranked_df.columns:
    meta_cols = ["player_name", "team_abbr", "display_position", "status",
                 "games_remaining", "games_played"]

if show_all:
    stat_cols_to_show = [c for c in ranked_df.columns if c in all_stat_cols]
else:
    stat_cols_to_show = [c for c in selected_cats if c in ranked_df.columns]

# ranked_df is sorted by composite_rank; keep rank for ordering but don't display it
display_cols = meta_cols + stat_cols_to_show
display_df = ranked_df[[c for c in display_cols if c in ranked_df.columns]].copy()

# Format stat columns (guard against NaN)
for col in stat_cols_to_show:
    fmt = ".2f" if _is_rate_stat(col) else ".0f"
    display_df[col] = display_df[col].apply(
        lambda v, f=fmt: format(float(v), f) if pd.notna(v) else "—"
    )
if "games_remaining" in display_df.columns:
    display_df["games_remaining"] = display_df["games_remaining"].apply(
        lambda v: f"{int(v)}" if pd.notna(v) else "—"
    )
if "games_played" in display_df.columns:
    display_df["games_played"] = display_df["games_played"].apply(
        lambda v: f"{int(v)}" if pd.notna(v) else "—"
    )

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

PAGE_SIZE = 25
total_rows = len(display_df)
total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)

if "ww_page" not in st.session_state:
    st.session_state["ww_page"] = 0

current_page = min(st.session_state["ww_page"], total_pages - 1)
page_start = current_page * PAGE_SIZE
page_df = display_df.iloc[page_start : page_start + PAGE_SIZE]

# ---------------------------------------------------------------------------
# Build the HTML table
# ---------------------------------------------------------------------------

_STATUS_COLORS = {
    "Healthy": ("background-color:rgba(53,53,50,1);color:#89938f;", "HEALTHY"),
    "DTD":     ("background-color:rgba(155,72,37,0.3);color:#ffb599;", "DTD"),
    "IR":      ("background-color:rgba(147,0,10,0.3);color:#ffb4ab;", "IR"),
    "O":       ("background-color:rgba(147,0,10,0.3);color:#ffb4ab;", "OUT"),
}

# Column header labels — metadata columns
_COL_LABELS = {
    "player_name": "Player",
    "team_abbr": "Team",
    "display_position": "Pos",
    "status": "Status",
    "games_remaining": "Games",
    "games_played": "GP",
}

def _col_label(col: str) -> str:
    """Return the display label for a table column."""
    if col in _COL_LABELS:
        return _COL_LABELS[col]
    return _stat_abbrev.get(col, col)

header_cells = []
for col in display_df.columns:
    label = _col_label(col)
    color = "#90d4c1" if col in selected_cats else "#89938f"
    header_cells.append(
        f'<th style="color:{color};text-align:left;">{label}</th>'
    )

row_htmls = []
for _, row in page_df.iterrows():
    cells = []
    for col in display_df.columns:
        val = row[col]

        if col == "player_name":
            # Two-line player cell
            team = row.get("team_abbr", "")
            pos  = row.get("display_position", "")
            cells.append(
                f'<td style="min-width:110px;">'
                f'<p class="fh-player-name">{val}</p>'
                f'<p class="fh-player-meta">{team} · {pos}</p>'
                f'</td>'
            )
        elif col == "status":
            style, label = _STATUS_COLORS.get(str(val), ("background-color:#353532;color:#89938f;", str(val)))
            cells.append(
                f'<td><span class="fh-badge" style="{style}">{label}</span></td>'
            )
        elif col in ("team_abbr", "display_position"):
            # Already shown in the player name cell
            cells.append(f'<td style="color:#89938f;font-size:0.6875rem;">{val}</td>')
        else:
            cells.append(f'<td style="text-align:right;">{val}</td>')

    row_htmls.append(f'<tr>{"".join(cells)}</tr>')

table_html = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,700;1,400;1,700&family=Manrope:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
* {{ box-sizing: border-box; }}
.ww-card {{
    background: #1c1c1a;
    border-radius: 12px;
    border-left: 4px solid #266b5c;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}}
.ww-table-wrap {{ overflow-x: auto; }}
.ww-table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 900px;
}}
.ww-table thead tr {{
    background-color: rgba(53,53,50,0.3);
    border-bottom: 1px solid rgba(63,73,69,0.2);
}}
.ww-table th {{
    padding: 14px 12px;
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
    white-space: nowrap;
}}
.ww-table tbody tr {{
    border-bottom: 1px solid rgba(63,73,69,0.08);
    transition: background-color 0.12s;
}}
.ww-table tbody tr:hover {{ background-color: rgba(32,32,30,0.6); }}
.ww-table td {{
    padding: 14px 12px;
    font-family: 'Inter', sans-serif;
    font-size: 0.75rem;
    color: #e5e2de;
    white-space: nowrap;
}}
.fh-player-name {{
    font-family: 'Newsreader', serif;
    font-size: 0.9375rem;
    font-weight: 700;
    color: #e5e2de;
    margin: 0;
}}
.fh-player-meta {{
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    color: #90d4c1;
    margin: 2px 0 0 0;
    font-weight: 600;
    letter-spacing: 0.05em;
}}
.fh-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}}
.ww-footer {{
    padding: 12px 16px;
    background-color: rgba(53,53,50,0.2);
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #89938f;
    font-weight: 700;
}}
.ww-table th:first-child,
.ww-table td:first-child {{
    position: sticky;
    left: 0;
    background-color: #1c1c1a;
    z-index: 2;
}}
@media (max-width: 768px) {{
    .ww-table {{ table-layout: fixed; }}
    .ww-table th:first-child,
    .ww-table td:first-child {{ width: 130px; overflow: hidden; }}
    .fh-player-name {{ font-size: 0.75rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
}}
</style>
<div class="ww-card">
    <div class="ww-table-wrap">
        <table class="ww-table">
            <thead><tr>{"".join(header_cells)}</tr></thead>
            <tbody>{"".join(row_htmls)}</tbody>
        </table>
    </div>
    <div class="ww-footer">
        <span>{total_rows} players &middot; {ranking_period.lower()} stats</span>
        <span>Page {current_page + 1} of {total_pages}</span>
    </div>
</div>
"""

st.html(table_html)

# ---------------------------------------------------------------------------
# Pagination controls
# ---------------------------------------------------------------------------

pg_cols = st.columns([1, 1])
with pg_cols[0]:
    if st.button("← Prev", key="ww_prev", type="secondary", use_container_width=True, disabled=(current_page == 0)):
        st.session_state["ww_page"] = current_page - 1
        st.rerun()
with pg_cols[1]:
    if st.button("Next →", key="ww_next", type="secondary", use_container_width=True, disabled=(current_page >= total_pages - 1)):
        st.session_state["ww_page"] = current_page + 1
        st.rerun()
