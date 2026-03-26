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

import streamlit as st

from analysis.projection import _is_rate_stat
from analysis.team_scores import stat_columns
from analysis.waiver_ranking import filter_by_position, rank_players
from auth.oauth import clear_session, get_session
from data import schedule as schedule_module, scoreboard as scoreboard_module
from data.players import get_available_players
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

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="fh-page-header" style="display:flex;align-items:flex-end;justify-content:space-between;gap:1rem;">
    <div>
        <h1 class="fh-page-title">Waiver Wire</h1>
        <p class="fh-page-subtitle">Precision scouting for the deep league manager</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Refresh button (top-right)
_, refresh_col = st.columns([8, 1])
with refresh_col:
    st.markdown('<div class="fh-cta-btn">', unsafe_allow_html=True)
    refresh = st.button("↻ Refresh", key="ww_refresh")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Controls panel
# ---------------------------------------------------------------------------

st.markdown('<div class="fh-controls-panel">', unsafe_allow_html=True)
st.markdown('<div style="display:grid;grid-template-columns:1fr 1fr 3fr;gap:2rem;align-items:start;">', unsafe_allow_html=True)

# ── Position filter (pill buttons) ─────────────────────────────────────────
st.markdown('<div>', unsafe_allow_html=True)
st.markdown('<span class="fh-control-label">Position Filter</span>', unsafe_allow_html=True)

positions = ["All", "C", "LW", "RW", "D", "G"]
if "ww_position" not in st.session_state:
    st.session_state["ww_position"] = "All"

pill_cols = st.columns(len(positions))
for i, pos in enumerate(positions):
    is_active = st.session_state["ww_position"] == pos
    wrapper_class = "fh-pill-col active" if is_active else "fh-pill-col"
    with pill_cols[i]:
        st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
        if st.button(pos, key=f"ww_pos_{pos}"):
            st.session_state["ww_position"] = pos
            st.session_state.pop("ww_page", None)  # reset pagination on filter change
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── Rank by (radio) ────────────────────────────────────────────────────────
st.markdown('<div>', unsafe_allow_html=True)
ranking_period = st.radio(
    "Rank by",
    options=["Season", "Last 30 days"],
    horizontal=False,
    key="ww_period",
)
st.markdown('</div>', unsafe_allow_html=True)

# ── Stat category chips ────────────────────────────────────────────────────
st.markdown('<div>', unsafe_allow_html=True)
st.markdown('<span class="fh-control-label">Categorical Improvement (Select Target Stats)</span>', unsafe_allow_html=True)

# Initialise toggle state for each stat (default: all off)
for stat in all_stat_cols:
    key = f"ww_cat_{stat}"
    if key not in st.session_state:
        st.session_state[key] = False

# Render chips in rows of up to 8
CHIPS_PER_ROW = 8
for row_start in range(0, len(all_stat_cols), CHIPS_PER_ROW):
    row_stats = all_stat_cols[row_start : row_start + CHIPS_PER_ROW]
    chip_cols = st.columns(len(row_stats))
    for i, stat in enumerate(row_stats):
        is_on = st.session_state[f"ww_cat_{stat}"]
        wrapper_class = "fh-chip-col active" if is_on else "fh-chip-col"
        with chip_cols[i]:
            st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
            if st.button(stat, key=f"ww_chip_{stat}"):
                st.session_state[f"ww_cat_{stat}"] = not is_on
                st.session_state.pop("ww_page", None)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # stat chips div
st.markdown('</div>', unsafe_allow_html=True)  # grid div
st.markdown('</div>', unsafe_allow_html=True)  # controls panel div

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

# ---------------------------------------------------------------------------
# Fetch player data (deferred until categories are selected)
# ---------------------------------------------------------------------------

players_stale = (
    "players_season" not in st.session_state
    or st.session_state.get("players_league_key") != league_key
    or refresh
)

if players_stale:
    session = get_session()
    if session is None:
        st.error("Your session has expired. Please log in again.")
        clear_session()
        st.stop()

    with st.spinner("Fetching available players…"):
        try:
            season_df, lastmonth_df = get_available_players(session, league_key)

            current_week = int(df_matchups["week"].max())
            sb = scoreboard_module.get_current_matchup(session, league_key, current_week)
            week_end = date.fromisoformat(sb["week_end"])
            from_date = max(date.today(), date.fromisoformat(sb["week_start"]))
            all_abbrs = list(set(season_df["team_abbr"].dropna().unique()))
            games_remaining_map = schedule_module.get_remaining_games(all_abbrs, from_date, week_end)
        except Exception as e:
            st.error(f"Failed to fetch player data: {e}")
            st.stop()

    st.session_state["players_season"] = season_df
    st.session_state["players_lastmonth"] = lastmonth_df
    st.session_state["players_league_key"] = league_key
    st.session_state["players_games_remaining"] = games_remaining_map
    st.session_state.pop("ww_page", None)

season_df = st.session_state["players_season"]
lastmonth_df = st.session_state["players_lastmonth"]
games_remaining_map = st.session_state.get("players_games_remaining", {})

# ---------------------------------------------------------------------------
# Filter + rank
# ---------------------------------------------------------------------------

position_group = st.session_state.get("ww_position", "All")
base_df = lastmonth_df if ranking_period == "Last 30 days" else season_df
filtered_df = filter_by_position(base_df, position_group)
ranked_df = rank_players(filtered_df, selected_cats)

if ranked_df.empty:
    st.info("No available players match the selected position filter.")
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

display_cols = meta_cols + stat_cols_to_show + ["composite_rank"]
display_df = ranked_df[[c for c in display_cols if c in ranked_df.columns]].copy()

# Format stat columns
for col in stat_cols_to_show:
    fmt = ".2f" if _is_rate_stat(col) else ".0f"
    display_df[col] = display_df[col].apply(lambda v, f=fmt: format(float(v), f))
display_df["composite_rank"] = display_df["composite_rank"].apply(lambda v: f"#{int(v)}")
if "games_remaining" in display_df.columns:
    display_df["games_remaining"] = display_df["games_remaining"].apply(lambda v: f"{int(v)}")
if "games_played" in display_df.columns:
    display_df["games_played"] = display_df["games_played"].apply(lambda v: f"{int(v)}")

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

# Human-readable column headers
_COL_LABELS = {
    "player_name": "Player",
    "team_abbr": "Team",
    "display_position": "Pos",
    "status": "Status",
    "games_remaining": "Rem",
    "games_played": "GP",
    "composite_rank": "Rank",
}

header_cells = []
for col in display_df.columns:
    label = _COL_LABELS.get(col, col)
    color = "#90d4c1" if col in selected_cats else "#89938f"
    align = "right" if col == "composite_rank" else "left"
    header_cells.append(
        f'<th style="color:{color};text-align:{align};">{label}</th>'
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
                f'<td style="min-width:160px;">'
                f'<p class="fh-player-name">{val}</p>'
                f'<p class="fh-player-meta">{team} · {pos}</p>'
                f'</td>'
            )
        elif col == "status":
            style, label = _STATUS_COLORS.get(str(val), ("background-color:#353532;color:#89938f;", str(val)))
            cells.append(
                f'<td><span class="fh-badge" style="{style}">{label}</span></td>'
            )
        elif col == "composite_rank":
            cells.append(
                f'<td style="text-align:right;font-family:\'Newsreader\',serif;'
                f'font-size:1rem;font-style:italic;font-weight:700;color:#fbbb5b;">'
                f'{val}</td>'
            )
        elif col in ("team_abbr", "display_position"):
            # Skip — already shown in the player name cell
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

pg_cols = st.columns([6, 1, 1])
with pg_cols[1]:
    if st.button("← Prev", key="ww_prev", disabled=(current_page == 0)):
        st.session_state["ww_page"] = current_page - 1
        st.rerun()
with pg_cols[2]:
    if st.button("Next →", key="ww_next", disabled=(current_page >= total_pages - 1)):
        st.session_state["ww_page"] = current_page + 1
        st.rerun()
