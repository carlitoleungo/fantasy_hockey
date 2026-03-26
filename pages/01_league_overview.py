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

# ---------------------------------------------------------------------------
# Guards + data load
# ---------------------------------------------------------------------------

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

_TABLE_CSS = """
<style>
.fh-table {
    border-collapse: collapse;
    width: 100%;
    font-size: 0.875rem;
}
.fh-table th {
    background-color: #262730;
    color: #fafafa;
    padding: 6px 10px;
    text-align: left;
    border-bottom: 2px solid rgba(148,163,184,0.3);
}
.fh-table td {
    padding: 5px 10px;
    border-bottom: 1px solid rgba(148,163,184,0.15);
}
/* Blue outer border for selected rows — no internal cell borders within the row */
.fh-table tr.selected td {
    border-top: 2px solid #4A90D9 !important;
    border-bottom: 2px solid #4A90D9 !important;
    border-left: none;
    border-right: none;
}
.fh-table tr.selected td:first-child { border-left: 2px solid #4A90D9 !important; }
.fh-table tr.selected td:last-child  { border-right: 2px solid #4A90D9 !important; }
</style>
"""


def _html_table(
    df: pd.DataFrame,
    cell_colors: dict[tuple[int, int], str] | None = None,
    selected_rows: set[int] | None = None,
) -> str:
    """
    Build a self-contained HTML table string for use with st.html().

    Parameters
    ----------
    df            : Pre-formatted DataFrame. All values are rendered as-is
                    (call _fmt_* helpers first). Index must be a clean
                    0-based RangeIndex so row positions match the dicts below.
    cell_colors   : (row_idx, col_idx) → CSS color string. Applied as the
                    background-color of that cell.
    selected_rows : Row indices that receive a blue outer border (used to
                    highlight the two comparison teams in the weekly scores table).
    """
    cell_colors = cell_colors or {}
    selected_rows = selected_rows or set()

    headers = list(df.columns)
    header_html = "".join(f"<th>{h}</th>" for h in headers)

    rows_html: list[str] = []
    for r_idx, row in df.iterrows():
        row_class = ' class="selected"' if r_idx in selected_rows else ""
        cells: list[str] = []
        for c_idx, col in enumerate(headers):
            color = cell_colors.get((int(r_idx), c_idx))
            style = f' style="background-color:{color};"' if color else ""
            cells.append(f"<td{style}>{row[col]}</td>")
        rows_html.append(f"<tr{row_class}>{''.join(cells)}</tr>")

    return (
        f"{_TABLE_CSS}"
        f"<table class='fh-table'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        f"</table>"
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
            colors[(int(r_idx), c_idx)] = "#4ade80"
        for r_idx in series[series == worst_val].index:
            # Don't overwrite green (can happen if all teams have the same value)
            if (int(r_idx), c_idx) not in colors:
                colors[(int(r_idx), c_idx)] = "#f87171"

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
            cell_colors[(r_idx, 1)] = "#4ade80"
        elif row.winner == team_b:
            cell_colors[(r_idx, 2)] = "#4ade80"

    return pd.DataFrame(rows), cell_colors


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

st.title("League Overview")

available_weeks = sorted(df["week"].unique())
team_names = sorted(df["team_name"].unique())

# --- Controls: week + team selectors side-by-side ---

ctrl_week, ctrl_a, ctrl_b = st.columns(3)

with ctrl_week:
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

st.subheader("Weekly Scores")

week_df = weekly_scores_ranked(df, selected_week).reset_index(drop=True)
stat_cols = stat_columns(df)

# Blue-border rows for the two comparison teams
selected_rows: set[int] = {
    int(r_idx)
    for r_idx, row in week_df.iterrows()
    if row["team_name"] in {team_a, team_b}
}

cell_colors = _weekly_cell_colors(week_df, stat_cols)
display_week_df = _fmt_weekly(week_df, stat_cols)

st.html(_html_table(display_week_df, cell_colors, selected_rows))

st.divider()

# ---------------------------------------------------------------------------
# Section 2: Team Comparison
# ---------------------------------------------------------------------------

if team_a == team_b:
    st.info("Select two different teams above to see a head-to-head breakdown.")
    st.stop()

st.subheader(f"{team_a} vs {team_b} — Week {selected_week}")

sim_df = simulate(df, team_a, team_b, from_week=selected_week, to_week=selected_week)
counts = tally(sim_df, team_a, team_b)

tcol1, tcol2, tcol3 = st.columns(3)
tcol1.metric(team_a, f"{counts[team_a]} wins")
tcol2.metric("Tied", str(counts["Tie"]))
tcol3.metric(team_b, f"{counts[team_b]} wins")

display_cmp_df, cmp_colors = _fmt_comparison(sim_df, team_a, team_b)
st.html(_html_table(display_cmp_df, cmp_colors))
