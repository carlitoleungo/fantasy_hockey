"""
Page 2 — Matchup Simulation

Select two teams, choose a period range, and see a side-by-side category
comparison with win/loss highlighting and an overall tally.

Data loading follows the same session-state pattern as 01_league_overview.py:
matchups are fetched once per session (or when the league changes) and stored
in st.session_state["matchups_df"].
"""

import streamlit as st

from analysis.matchup_sim import simulate, tally
from analysis.team_scores import stat_columns
from auth.oauth import clear_session, get_session
from data import matchups

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
# Load data (shared session-state cache with league overview page)
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
        except Exception as e:
            st.error(f"Failed to load matchup data: {e}")
            st.stop()

    st.session_state["matchups_df"] = df
    st.session_state["matchups_league_key"] = league_key

df = st.session_state.get("matchups_df")

if df is None or df.empty:
    st.info("No matchup data available yet — the season may not have started.")
    st.stop()

# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

st.title("Matchup Simulation")

team_names = sorted(df["team_name"].unique())
available_weeks = sorted(df["week"].unique())
min_week = int(available_weeks[0])
max_week = int(available_weeks[-1])
total_weeks = len(available_weeks)

# --- Controls ---

col_a, col_b = st.columns(2)
with col_a:
    team_a = st.selectbox("Team A", options=team_names, index=0, key="sim_team_a")
with col_b:
    default_b = min(1, len(team_names) - 1)
    team_b = st.selectbox("Team B", options=team_names, index=default_b, key="sim_team_b")

if team_a == team_b:
    st.warning("Please select two different teams.")
    st.stop()

# Period selector — preset options plus a custom range
period_options = ["All weeks"]
if total_weeks >= 3:
    period_options.append("Last 3 weeks")
if total_weeks >= 5:
    period_options.append("Last 5 weeks")
period_options.append("Custom range")

period = st.selectbox("Period", options=period_options, key="sim_period")

if period == "All weeks":
    from_week = min_week
    to_week = max_week
elif period == "Last 3 weeks":
    from_week = max_week - 2
    to_week = max_week
elif period == "Last 5 weeks":
    from_week = max_week - 4
    to_week = max_week
else:
    # Custom range
    range_col1, range_col2 = st.columns(2)
    with range_col1:
        from_week = st.selectbox("From week", options=available_weeks,
                                 index=0, key="sim_from_week")
    with range_col2:
        # Default to latest week; filter to weeks >= from_week
        valid_to = [w for w in available_weeks if w >= from_week]
        to_week = st.selectbox("To week", options=valid_to,
                               index=len(valid_to) - 1, key="sim_to_week")

st.caption(f"Comparing averages over weeks {from_week}–{to_week}")

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

sim_df = simulate(df, team_a, team_b, from_week=from_week, to_week=to_week)
counts = tally(sim_df, team_a, team_b)

# --- Tally header ---
a_wins = counts[team_a]
b_wins = counts[team_b]
ties = counts["Tie"]

tcol1, tcol2, tcol3 = st.columns(3)
tcol1.metric(team_a, f"{a_wins} wins")
tcol2.metric("Tied", str(ties))
tcol3.metric(team_b, f"{b_wins} wins")

# --- Comparison table ---

# Rename columns for display: team_a/team_b → actual team names
display_df = sim_df.rename(columns={
    "category": "Category",
    "team_a": team_a,
    "team_b": team_b,
    "winner": "Winner",
})


def _highlight_winner(row):
    """Apply background colour to the winning team's cell in each row."""
    winner = row["Winner"]
    styles = [""] * len(row)
    green = "background-color: rgba(0, 180, 0, 0.15)"
    if winner == team_a:
        styles[1] = green   # team_a column
    elif winner == team_b:
        styles[2] = green   # team_b column
    return styles


stat_cols = stat_columns(df)
format_map = {team_a: "{:.2f}", team_b: "{:.2f}"}

styled = (
    display_df
    .style
    .apply(_highlight_winner, axis=1)
    .format(format_map)
)

st.dataframe(styled, use_container_width=True, hide_index=True)
