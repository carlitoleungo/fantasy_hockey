"""
Page 1 — League Overview

Shows two views of the matchup data:

  1. Weekly Scores — raw stat totals for every team in a selected week,
     color-coded per category (green = strong, red = weak), ranked by
     avg_rank for that week.
  2. Season Rankings — each team's average rank per scoring category across
     all completed weeks. Green = category strength, red = weakness.
     The current in-progress week is excluded from averages.

Data is loaded once per session (guarded by st.session_state) to avoid
re-hitting the API on every Streamlit interaction. The parquet cache in
data/cache.py handles persistence across sessions.
"""

import streamlit as st

from analysis.team_scores import (
    LOWER_IS_BETTER,
    avg_ranks,
    stat_columns,
    weekly_scores_ranked,
)
from auth.oauth import clear_session, get_session
from data import matchups
from data.matchups import get_current_week

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

if "tokens" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()

league_key = st.session_state.get("league_key")
if not league_key:
    st.warning("Please select a league on the home page.")
    st.stop()

# ---------------------------------------------------------------------------
# Load data
# Fetch + update the local parquet cache, then read back into session state.
# Re-fetches if the user switches leagues.
# ---------------------------------------------------------------------------

if (
    "matchups_df" not in st.session_state
    or st.session_state.get("matchups_league_key") != league_key
):
    session = get_session()
    if session is None:
        st.error("Your session has expired. Please log in again.")
        clear_session()
        st.stop()

    with st.spinner("Loading matchup data…"):
        try:
            df = matchups.get_matchups(session, league_key)
            current_week = get_current_week(session, league_key)
        except Exception as e:
            st.error(f"Failed to load matchup data: {e}")
            st.stop()

    st.session_state["matchups_df"] = df
    st.session_state["matchups_league_key"] = league_key
    st.session_state["current_week"] = current_week

df = st.session_state.get("matchups_df")
current_week = st.session_state.get("current_week")

if df is None or df.empty:
    st.info("No matchup data available yet — the season may not have started.")
    st.stop()

# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

st.title("League Overview")

available_weeks = sorted(df["week"].unique())

# ---------------------------------------------------------------------------
# Section 1: Weekly scores
# ---------------------------------------------------------------------------

st.subheader("Weekly Scores")

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

week_df = weekly_scores_ranked(df, selected_week)

# Format: counting stats as integers, rate stats (Average, Percentage, %)
# with 2 decimal places.
stat_cols = stat_columns(df)


def _is_rate_stat(name: str) -> bool:
    lower = name.lower()
    return "average" in lower or "percentage" in lower or "%" in name


format_map = {
    col: "{:.2f}" if _is_rate_stat(col) else "{:.0f}"
    for col in stat_cols
}
format_map["avg_rank"] = "{:.2f}"


def _style_weekly_scores(week_df, stat_cols, format_map):
    styler = week_df.style.format(format_map)
    normal_cols = [c for c in stat_cols if c not in LOWER_IS_BETTER]
    lower_better_cols = [c for c in stat_cols if c in LOWER_IS_BETTER]
    if normal_cols:
        styler = (
            styler
            .highlight_max(subset=normal_cols, color="#4ade80", axis=0)
            .highlight_min(subset=normal_cols, color="#f87171", axis=0)
        )
    if lower_better_cols:
        styler = (
            styler
            .highlight_min(subset=lower_better_cols, color="#4ade80", axis=0)
            .highlight_max(subset=lower_better_cols, color="#f87171", axis=0)
        )
    styler = styler.set_properties(subset=["avg_rank"], **{"font-weight": "bold"})
    return styler


st.dataframe(
    _style_weekly_scores(week_df, stat_cols, format_map),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Section 2: Season average ranks
# ---------------------------------------------------------------------------

st.subheader("Season Rankings")
st.caption(
    "Average rank per scoring category across all **completed** weeks. "
    "**Rank 1 = best.** "
    "Green = team strength, red = team weakness."
)


@st.cache_data
def _compute_avg_ranks(df: "pd.DataFrame", current_week: int | None):  # type: ignore[name-defined]  # noqa: F821
    exclude = {current_week} if current_week else None
    return avg_ranks(df, exclude_weeks=exclude)


ranks_df = _compute_avg_ranks(df, current_week)

# Separate the team_name column from the numeric columns for styling
display_ranks = ranks_df.set_index("team_name")

styled = (
    display_ranks
    .style
    # Background gradient per column: low rank (green) → high rank (red)
    # RdYlGn_r: green at low values, red at high values
    .background_gradient(cmap="RdYlGn_r", axis=0)
    .format("{:.2f}")
    # Highlight avg_rank column more prominently
    .set_properties(subset=["avg_rank"], **{"font-weight": "bold"})
)

st.dataframe(styled, use_container_width=True)
