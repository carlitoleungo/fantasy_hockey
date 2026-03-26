"""
Page 3 — Waiver Wire

Ranks available (unrostered) players by composite score across user-selected
stat categories. Supports position filtering and toggling between season and
last-30-day stats.

Data is fetched on first category selection (not page load) and cached in
session state for the rest of the session. Two API calls per page × 4 pages
= 8 calls total, so deferring until the user actually wants results avoids
unnecessary network traffic.
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

# ---------------------------------------------------------------------------
# Guards + data load
# We need the matchup DataFrame for stat category names to drive the multi-select.
# ---------------------------------------------------------------------------

league_key = require_auth()
load_matchups(league_key)

df_matchups = st.session_state.get("matchups_df")
if df_matchups is None or df_matchups.empty:
    st.info("No league data available yet — the season may not have started.")
    st.stop()

all_stat_cols = stat_columns(df_matchups)

# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

st.title("Waiver Wire")

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])

with ctrl_col1:
    position_group = st.selectbox(
        "Position",
        options=["All", "Skaters", "Forwards", "Defence", "Goalies"],
        key="ww_position",
    )

with ctrl_col2:
    ranking_period = st.radio(
        "Rank by",
        options=["Season", "Last 30 days"],
        horizontal=True,
        key="ww_period",
    )

with ctrl_col3:
    st.write("")  # vertical alignment spacer
    refresh = st.button("↻ Refresh", key="ww_refresh")

selected_cats = st.multiselect(
    "Stat categories to improve",
    options=all_stat_cols,
    key="ww_categories",
)

if not selected_cats:
    st.info("Select one or more stat categories above to rank available players.")
    st.stop()

# ---------------------------------------------------------------------------
# Fetch player data (deferred until categories are selected)
# Invalidate cache on league change or manual refresh.
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

season_df = st.session_state["players_season"]
lastmonth_df = st.session_state["players_lastmonth"]
games_remaining_map = st.session_state.get("players_games_remaining", {})

# ---------------------------------------------------------------------------
# Filter, rank, display
# ---------------------------------------------------------------------------

base_df = lastmonth_df if ranking_period == "Last 30 days" else season_df
filtered_df = filter_by_position(base_df, position_group)
ranked_df = rank_players(filtered_df, selected_cats)

if ranked_df.empty:
    st.info("No available players match the selected position filter.")
    st.stop()

# Columns to show: metadata + selected stats + composite_rank.
# "Show all stats" checkbox reveals all stat columns.
show_all = st.checkbox("Show all stats", value=False, key="ww_show_all")

ranked_df["games_remaining"] = ranked_df["team_abbr"].map(
    lambda a: games_remaining_map.get(a, 0)
)

meta_cols = ["player_name", "team_abbr", "display_position", "status", "games_remaining"]
if ranking_period == "Last 30 days" and "games_played" in ranked_df.columns:
    meta_cols = ["player_name", "team_abbr", "display_position", "status", "games_remaining", "games_played"]

if show_all:
    stat_cols_to_show = [c for c in ranked_df.columns if c in all_stat_cols]
else:
    stat_cols_to_show = [c for c in selected_cats if c in ranked_df.columns]

display_cols = meta_cols + stat_cols_to_show + ["composite_rank"]
display_df = ranked_df[[c for c in display_cols if c in ranked_df.columns]]

# Format stat columns: integers for counting stats, 2dp for rate stats (GAA, SV%, etc.)
format_map = {"games_remaining": "{:.0f}"}
for col in stat_cols_to_show:
    format_map[col] = "{:.2f}" if _is_rate_stat(col) else "{:.0f}"
format_map["composite_rank"] = "{:.0f}"

st.caption(
    f"{len(display_df)} available players · "
    f"ranked by **{', '.join(selected_cats)}** · "
    f"{'last 30 days' if ranking_period == 'Last 30 days' else 'season'} stats"
)

st.dataframe(
    display_df.style.format(format_map),
    use_container_width=True,
    hide_index=True,
)
