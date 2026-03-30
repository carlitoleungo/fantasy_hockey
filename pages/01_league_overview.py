"""
Page 1 — League Overview

Two sections, both driven by a shared week + team-selector control row:

  1. Weekly Scores — all teams' stat totals for the selected week, ranked by
     avg_rank. Best value per category is green; worst is red. The two teams
     chosen for comparison are outlined in blue.

  2. Team Comparison — head-to-head breakdown for the same week. Shows which
     team wins each scoring category; the winner's cell is highlighted green.

Data is loaded once per session to avoid re-hitting the API on every interaction.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis.matchup_sim import simulate, tally
from analysis.projection import _is_rate_stat
from analysis.team_scores import (
    LOWER_IS_BETTER,
    stat_columns,
    weekly_scores_ranked,
)
from utils.common import load_matchups, require_auth
from utils.theme import inject_css, render_mobile_nav

# ---------------------------------------------------------------------------
# Guards + data load
# ---------------------------------------------------------------------------

inject_css()
render_mobile_nav("league_overview")
league_key = require_auth()
load_matchups(league_key)

df = st.session_state.get("matchups_df")
current_week = st.session_state.get("current_week")

if df is None or df.empty:
    st.info("No matchup data available yet — the season may not have started.")
    st.stop()

# ---------------------------------------------------------------------------
# HTML table builder
# ---------------------------------------------------------------------------

# Embed the design system CSS within each st.html() call.
# st.html() renders in a shadow context, so global CSS from inject_css()
# may not reach it — we include the critical table styles inline here.
_TABLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,700;1,400;1,700&family=Manrope:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
:root {
    --c-surface:            #131312;
    --c-surface-low:        #1c1c1a;
    --c-surface-container:  #20201e;
    --c-surface-highest:    #353532;
    --c-primary:            #90d4c1;
    --c-primary-container:  #266b5c;
    --c-on-primary-container: #a5e9d6;
    --c-secondary:          #fbbb5b;
    --c-on-surface:         #e5e2de;
    --c-outline:            #89938f;
    --c-outline-variant:    #3f4945;
    --c-error:              #ffb4ab;
    --c-error-container:    #93000a;
}
* { box-sizing: border-box; }
.fh-table-wrap { overflow-x: auto; }
.fh-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.75rem;
}
.fh-table thead tr {
    background-color: rgba(53,53,50,0.3);
    border-bottom: 1px solid rgba(63,73,69,0.1);
}
.fh-table th {
    padding: 14px 16px;
    font-family: 'Manrope', sans-serif;
    font-size: 0.625rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--c-outline);
    font-weight: 700;
    text-align: left;
    white-space: nowrap;
}
.fh-table tbody tr {
    border-bottom: 1px solid rgba(63,73,69,0.05);
    transition: background-color 0.12s;
}
.fh-table tbody tr:hover { background-color: rgba(32,32,30,0.5); }
.fh-table td {
    padding: 14px 16px;
    font-family: 'Inter', sans-serif;
    font-size: 0.75rem;
    color: var(--c-on-surface);
    white-space: nowrap;
}
/* Selected (comparison team) rows — amber accent */
.fh-row-selected { background-color: rgba(251,187,91,0.08) !important; }
.fh-row-selected td:first-child {
    border-left: 3px solid #fbbb5b !important;
    color: #fbbb5b !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
}
/* Comparison table: winner / loser cells */
.fh-cell-win {
    background-color: rgba(38,107,92,0.4);
    color: var(--c-on-primary-container);
    font-weight: 700;
    font-family: 'Manrope', sans-serif;
}
.fh-cell-lose { color: var(--c-outline); }
/* Card header inside st.html */
.fh-card-inner-header {
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid rgba(63,73,69,0.05);
}
.fh-card-inner-title {
    font-family: 'Newsreader', serif;
    font-size: 1.5rem;
    color: var(--c-on-surface);
    margin: 0;
}
/* Metric row */
.fh-metric-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 1.5rem;
    margin: 0;
}
.fh-metric-card {
    background-color: var(--c-surface-container);
    border-radius: 12px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}
.fh-metric-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}
.fh-metric-label {
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    font-weight: 700;
}
.fh-metric-value {
    font-family: 'Newsreader', serif;
    font-size: 3rem;
    font-style: italic;
    font-weight: 700;
    color: var(--c-on-surface);
    line-height: 1;
}
/* Section header with rule */
.fh-section-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 0 0 1.5rem 0;
}
.fh-section-title {
    font-family: 'Newsreader', serif;
    font-size: 1.5rem;
    font-style: italic;
    color: var(--c-on-surface);
    margin: 0;
    white-space: nowrap;
}
.fh-section-rule {
    flex: 1;
    height: 1px;
    background-color: rgba(63,73,69,0.2);
}
/* Sticky first column for horizontal-scrolling tables on mobile */
.fh-table th:first-child,
.fh-table td:first-child {
    position: sticky;
    left: 0;
    background-color: var(--c-surface-low);
    z-index: 2;
}
.fh-row-selected td:first-child {
    background-color: rgba(38,107,92,0.08) !important;
}

/* Comparison detail table */
.fh-cmp-header {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    padding: 12px 16px;
    background-color: rgba(53,53,50,0.2);
    border-bottom: 1px solid rgba(63,73,69,0.1);
}
.fh-cmp-col-label {
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    font-weight: 700;
    color: var(--c-outline);
}
.fh-cmp-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    align-items: center;
    border-bottom: 1px solid rgba(63,73,69,0.05);
    transition: background-color 0.12s;
}
.fh-cmp-row:hover { background-color: rgba(255,255,255,0.02); }
.fh-cmp-cat {
    padding: 14px 16px;
    font-family: 'Manrope', sans-serif;
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #bfc9c4;
}
.fh-cmp-val {
    padding: 14px 16px;
    text-align: center;
    font-family: 'Manrope', sans-serif;
    font-size: 0.875rem;
    color: var(--c-outline);
}
</style>
"""


def _html_table(
    df: pd.DataFrame,
    cell_colors: dict[tuple[int, int], str] | None = None,
    selected_rows: set[int] | None = None,
    col_styles: dict[str, str] | None = None,
) -> str:
    """
    Build a self-contained HTML table string for use with st.html().

    Parameters
    ----------
    df            : Pre-formatted DataFrame. All values are rendered as-is.
    cell_colors   : (row_idx, col_idx) → inline CSS background-color string.
    selected_rows : Row indices that receive the amber left-border highlight.
    col_styles    : column_name → CSS style string applied to both <th> and <td>.
    """
    cell_colors = cell_colors or {}
    selected_rows = selected_rows or set()
    col_styles = col_styles or {}

    headers = list(df.columns)
    header_html = ""
    for h in headers:
        extra = col_styles.get(h, "")
        header_html += f'<th style="{extra}">{h}</th>' if extra else f"<th>{h}</th>"

    rows_html: list[str] = []
    for r_idx, row in df.iterrows():
        row_class = "fh-row-selected" if r_idx in selected_rows else ""
        cells: list[str] = []
        for c_idx, col in enumerate(headers):
            color = cell_colors.get((int(r_idx), c_idx))
            extra = col_styles.get(col, "")
            parts = []
            if color:
                parts.append(f"background-color:{color}")
            if extra:
                parts.append(extra)
            style = f' style="{";".join(parts)}"' if parts else ""
            cells.append(f"<td{style}>{row[col]}</td>")
        rows_html.append(f'<tr class="{row_class}">{"".join(cells)}</tr>')

    return (
        f"{_TABLE_CSS}"
        f'<div class="fh-table-wrap">'
        f"<table class='fh-table'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        f"</table>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Helpers: colour computation and value formatting
# ---------------------------------------------------------------------------

def _weekly_cell_colors(
    week_df: pd.DataFrame,
    stat_cols: list[str],
) -> dict[tuple[int, int], str]:
    """
    Return (row_idx, col_idx) → color for the weekly scores table.

    Best value per stat → green (#4ade80).
    Worst value per stat → red (#f87171).
    Ties are handled: all rows sharing the best/worst value are coloured.
    LOWER_IS_BETTER stats invert the green/red assignment.
    """
    col_list = list(week_df.columns)
    colors: dict[tuple[int, int], str] = {}

    for col in stat_cols:
        if col not in week_df.columns:
            continue
        c_idx = col_list.index(col)
        lower_better = col in LOWER_IS_BETTER
        series = week_df[col]

        best_val = series.min() if lower_better else series.max()
        worst_val = series.max() if lower_better else series.min()

        for r_idx in series[series == best_val].index:
            colors[(int(r_idx), c_idx)] = "rgba(38,107,92,0.4)"
        for r_idx in series[series == worst_val].index:
            # Don't overwrite best (can happen if all teams have the same value)
            if (int(r_idx), c_idx) not in colors:
                colors[(int(r_idx), c_idx)] = "rgba(147,0,10,0.2)"

    return colors


def _fmt_weekly(week_df: pd.DataFrame, stat_cols: list[str]) -> pd.DataFrame:
    """
    Return a copy of week_df with numeric columns formatted as display strings.

    Rate stats (GAA, SV%, etc.) → 2 decimal places.
    Counting stats → 0 decimal places (no trailing ".0").
    avg_rank → 2 decimal places.
    """
    display = week_df.copy()
    for col in stat_cols:
        fmt = ".2f" if _is_rate_stat(col) else ".0f"
        display[col] = display[col].apply(lambda v, f=fmt: format(float(v), f))
    if "avg_rank" in display.columns:
        display["avg_rank"] = display["avg_rank"].apply(lambda v: f"{float(v):.2f}")
    return display


def _fmt_comparison(
    sim_df: pd.DataFrame,
    team_a: str,
    team_b: str,
) -> tuple[pd.DataFrame, dict[tuple[int, int], str]]:
    """
    Build a display DataFrame and cell_colors dict for the comparison table.

    Columns: Category | <team_a name> | <team_b name>
    The winner's value cell is coloured green. Ties produce no colour.

    Returns (display_df, cell_colors).
    """
    rows: list[dict] = []
    cell_colors: dict[tuple[int, int], str] = {}

    for r_idx, row in enumerate(sim_df.itertuples(index=False)):
        cat: str = row.category
        fmt = ".2f" if _is_rate_stat(cat) else ".0f"
        rows.append({
            "Category": cat,
            team_a: format(float(row.team_a), fmt),
            team_b: format(float(row.team_b), fmt),
        })
        # Column indices: 0 = Category, 1 = team_a, 2 = team_b
        if row.winner == team_a:
            cell_colors[(r_idx, 1)] = "rgba(38,107,92,0.4)"
        elif row.winner == team_b:
            cell_colors[(r_idx, 2)] = "rgba(38,107,92,0.4)"

    return pd.DataFrame(rows), cell_colors


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

available_weeks = sorted(df["week"].unique())
team_names = sorted(df["team_name"].unique())

# --- Page header ---
st.markdown("""
<div class="fh-page-header">
    <h1 class="fh-page-title">League Overview</h1>
    <p class="fh-page-subtitle">See where your team stands, week by week.</p>
    <p class="fh-page-instructions">Select a week and two teams to compare. Green highlights the category leader for that week; red marks the weakest. The head-to-head breakdown below shows exactly which categories each team wins for the selected matchup.</p>
</div>
""", unsafe_allow_html=True)

# --- Controls: week selector (full width), then teams side-by-side ---

last_complete = current_week - 1 if current_week else None
default_idx = (
    available_weeks.index(last_complete)
    if last_complete in available_weeks
    else len(available_weeks) - 1
)
selected_week = st.selectbox(
    "Week",
    options=available_weeks,
    format_func=lambda w: f"Week {w} (in progress)" if w == current_week else f"Week {w}",
    index=default_idx,
    key="overview_week_selector",
)

ctrl_a, ctrl_b = st.columns(2)

with ctrl_a:
    team_a = st.selectbox("Team A", options=team_names, index=0, key="cmp_team_a")

with ctrl_b:
    team_b = st.selectbox(
        "Team B",
        options=team_names,
        index=min(1, len(team_names) - 1),
        key="cmp_team_b",
    )

# ---------------------------------------------------------------------------
# Section 1: Weekly Scores
# ---------------------------------------------------------------------------

week_df = weekly_scores_ranked(df, selected_week).reset_index(drop=True)
stat_cols = stat_columns(df)

# Abbreviation lookup for column headers
_STAT_ABBREV: dict[str, str] = {
    "Goals": "G", "Assists": "A", "Points": "Pts", "Plus/Minus": "+/-",
    "Penalty Minutes": "PIM", "Power Play Goals": "PPG", "Powerplay Goals": "PPG",
    "Power Play Assists": "PPA", "Powerplay Assists": "PPA",
    "Power Play Points": "PPP", "Powerplay Points": "PPP",
    "Short Handed Goals": "SHG", "Short Handed Assists": "SHA",
    "Short Handed Points": "SHP", "Shots on Goal": "SOG",
    "Hits": "HIT", "Blocked Shots": "BLK", "Blocks": "BLK",
    "Wins": "W", "Save Percentage": "SV%", "Goals Against Average": "GAA",
    "Saves": "SV", "Shutouts": "SO", "Goals Against": "GA", "Faceoffs Won": "FOW",
}
_stat_cats_ss = st.session_state.get("stat_categories", [])
_stat_abbrev: dict[str, str] = (
    {c["stat_name"]: c["abbreviation"] for c in _stat_cats_ss if "stat_name" in c and "abbreviation" in c}
    or _STAT_ABBREV
)

# Amber highlight for the two comparison teams
selected_rows: set[int] = {
    int(r_idx)
    for r_idx, row in week_df.iterrows()
    if row["team_name"] in {team_a, team_b}
}

cell_colors = _weekly_cell_colors(week_df, stat_cols)
display_week_df = _fmt_weekly(week_df, stat_cols)

# Rename columns: team_name → Team, stat cols → abbreviations
rename_map: dict[str, str] = {"team_name": "Team"}
for col in stat_cols:
    rename_map[col] = _stat_abbrev.get(col, col)
display_week_df = display_week_df.rename(columns=rename_map)
abbrev_stat_cols = [rename_map.get(c, c) for c in stat_cols]

# Compact style for stat columns: narrow, right-aligned, reduced padding
_STAT_COL_STYLE = "width:50px;padding:14px 6px;text-align:right;"
stat_col_styles = {abbrev: _STAT_COL_STYLE for abbrev in abbrev_stat_cols}

leaderboard_html = (
    f'<div style="background:#1c1c1a;border-radius:12px;border-left:4px solid #266b5c;'
    f'overflow:hidden;margin-bottom:2.5rem;box-shadow:0 4px 24px rgba(0,0,0,0.3);">'
    f'<div style="padding:1.5rem;border-bottom:1px solid rgba(63,73,69,0.05);">'
    f'<h3 style="font-family:Newsreader,serif;font-size:1.5rem;color:#e5e2de;margin:0;">Weekly Leaderboard</h3>'
    f'</div>'
    + _html_table(display_week_df, cell_colors, selected_rows, stat_col_styles).replace(_TABLE_CSS, "", 1)
    + f"</div>"
)
# Build the full card including embedded CSS
st.html(_TABLE_CSS + leaderboard_html)

# ---------------------------------------------------------------------------
# Section 2: Team Comparison
# ---------------------------------------------------------------------------

if team_a == team_b:
    st.info("Select two different teams above to see a head-to-head breakdown.")
    st.stop()

sim_df = simulate(df, team_a, team_b, from_week=selected_week, to_week=selected_week)
counts = tally(sim_df, team_a, team_b)

# Section header
st.html(f"""
{_TABLE_CSS}
<div class="fh-section-header">
    <h3 class="fh-section-title">Head-to-Head Comparison</h3>
    <div class="fh-section-rule"></div>
</div>
<div class="fh-metric-row">
    <div class="fh-metric-card" style="border:1px solid rgba(144,212,193,0.2);">
        <div class="fh-metric-top">
            <span class="fh-metric-label" style="color:#90d4c1;">{team_a} Wins</span>
        </div>
        <div class="fh-metric-value">{counts[team_a]}</div>
    </div>
    <div class="fh-metric-card" style="border:1px solid rgba(137,147,143,0.2);">
        <div class="fh-metric-top">
            <span class="fh-metric-label" style="color:#89938f;">Category Ties</span>
        </div>
        <div class="fh-metric-value">{counts["Tie"]}</div>
    </div>
    <div class="fh-metric-card" style="border:1px solid rgba(251,187,91,0.2);">
        <div class="fh-metric-top">
            <span class="fh-metric-label" style="color:#fbbb5b;">{team_b} Wins</span>
        </div>
        <div class="fh-metric-value">{counts[team_b]}</div>
    </div>
</div>
""")

display_cmp_df, cmp_colors = _fmt_comparison(sim_df, team_a, team_b)
st.html(_html_table(display_cmp_df, cmp_colors))
