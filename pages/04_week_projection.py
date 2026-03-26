"""
Page 4 — Week Projection

Shows the current week's live matchup score and projects the final result
using each rostered player's last-30-day per-game average multiplied by
their team's remaining NHL games this week.

Data loading:
- Page-load data (scoreboard, live stats, team list) cached in session state
- Roster + schedule data fetched lazily after team selection, keyed by team pair
- A "Refresh" button clears all projection state to re-fetch live data
"""

from datetime import date

import pandas as pd
import streamlit as st

from analysis.matchup_sim import tally
from analysis.projection import _is_rate_stat, compare_projections, project_team_stats
from auth.oauth import clear_session, get_session
from data import client, players as players_module, roster as roster_module
from data import schedule as schedule_module
from data import scoreboard as scoreboard_module
from pages._common import require_auth

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

league_key = require_auth()

# ---------------------------------------------------------------------------
# Header + refresh
# ---------------------------------------------------------------------------

title_col, btn_col = st.columns([5, 1])
with title_col:
    st.title("Week Projection")
with btn_col:
    st.write("")  # vertical alignment nudge
    refresh = st.button("↻ Refresh", key="proj_refresh")

if refresh:
    # All projection state uses the "proj_" prefix or the two named keys below.
    # Per-team-pair data is keyed as f"proj_{my_key}_{opp_key}".
    # Do not add "proj_" keys that should survive a refresh.
    for key in list(st.session_state.keys()):
        if key.startswith("proj_") or key in ("projection_data", "projection_league_key"):
            del st.session_state[key]

# ---------------------------------------------------------------------------
# Page-load data (cached per session / league)
# ---------------------------------------------------------------------------

page_data_stale = (
    "projection_data" not in st.session_state
    or st.session_state.get("projection_league_key") != league_key
)

if page_data_stale:
    session = get_session()
    if session is None:
        st.error("Your session has expired. Please log in again.")
        clear_session()
        st.stop()

    with st.spinner("Loading current week data…"):
        try:
            # Single /settings call returns both week info and stat categories.
            settings, stat_categories = client.get_settings_and_categories(session, league_key)
            current_week = settings["current_week"]
            teams = client.get_teams(session, league_key)
            live_stats_rows = client.get_all_teams_week_stats(
                session, league_key, current_week, stat_categories
            )
            scoreboard_data = scoreboard_module.get_current_matchup(
                session, league_key, current_week
            )
        except Exception as e:
            st.error(f"Failed to load week data: {e}")
            st.stop()

    st.session_state["projection_data"] = {
        "current_week": current_week,
        "stat_categories": stat_categories,
        "teams": teams,
        "live_stats_rows": live_stats_rows,
        "scoreboard": scoreboard_data,
    }
    st.session_state["projection_league_key"] = league_key

data = st.session_state["projection_data"]
stat_categories = data["stat_categories"]
teams = data["teams"]
live_stats_rows = data["live_stats_rows"]
scoreboard_data = data["scoreboard"]
current_week = data["current_week"]

enabled_stats = [c["stat_name"] for c in stat_categories if c["is_enabled"]]

# ---------------------------------------------------------------------------
# Team selector
# ---------------------------------------------------------------------------

team_name_to_key = {t["team_name"]: t["team_key"] for t in teams}
team_names = sorted(team_name_to_key.keys())

my_team_name = st.selectbox("My team", options=team_names, key="proj_my_team")
my_team_key = team_name_to_key[my_team_name]

# Resolve opponent from scoreboard matchup pairings
opponent_key = None
for m in scoreboard_data["matchups"]:
    if m["team_a_key"] == my_team_key:
        opponent_key = m["team_b_key"]
        break
    elif m["team_b_key"] == my_team_key:
        opponent_key = m["team_a_key"]
        break

if opponent_key is None:
    st.warning("Your team has no matchup this week (bye week).")
    st.stop()

opponent_name = next(
    (t["team_name"] for t in teams if t["team_key"] == opponent_key),
    opponent_key,
)
st.caption(
    f"Week {current_week} · {scoreboard_data['week_start']} – {scoreboard_data['week_end']}"
    f" · vs **{opponent_name}**"
)

# ---------------------------------------------------------------------------
# Lazy roster + schedule fetch (keyed by team pair)
# ---------------------------------------------------------------------------

pair_key = f"proj_{my_team_key}_{opponent_key}"

if pair_key not in st.session_state:
    session = get_session()
    if session is None:
        st.error("Your session has expired. Please log in again.")
        clear_session()
        st.stop()

    with st.spinner("Fetching rosters and NHL schedule…"):
        try:
            my_roster = roster_module.get_team_roster(session, my_team_key, current_week)
            opp_roster = roster_module.get_team_roster(session, opponent_key, current_week)

            all_player_keys = [p["player_key"] for p in my_roster + opp_roster]
            all_abbrs = list({p["team_abbr"] for p in my_roster + opp_roster if p["team_abbr"]})

            lastmonth_stats = players_module.get_players_lastmonth_stats(
                session, league_key, all_player_keys
            )

            week_end = date.fromisoformat(scoreboard_data["week_end"])
            from_date = max(date.today(), date.fromisoformat(scoreboard_data["week_start"]))
            games_remaining = schedule_module.get_remaining_games(all_abbrs, from_date, week_end)

        except Exception as e:
            st.error(f"Failed to fetch roster/schedule data: {e}")
            st.stop()

    st.session_state[pair_key] = {
        "my_roster": my_roster,
        "opp_roster": opp_roster,
        "lastmonth_stats": lastmonth_stats,
        "games_remaining": games_remaining,
    }

pair_data = st.session_state[pair_key]

# ---------------------------------------------------------------------------
# Compute projections
# ---------------------------------------------------------------------------

live_by_key = {row["team_key"]: row for row in live_stats_rows}

my_current = {s: float(live_by_key.get(my_team_key, {}).get(s, 0.0)) for s in enabled_stats}
opp_current = {s: float(live_by_key.get(opponent_key, {}).get(s, 0.0)) for s in enabled_stats}

my_projected = project_team_stats(
    my_current,
    pair_data["my_roster"],
    pair_data["lastmonth_stats"],
    pair_data["games_remaining"],
    stat_categories,
)
opp_projected = project_team_stats(
    opp_current,
    pair_data["opp_roster"],
    pair_data["lastmonth_stats"],
    pair_data["games_remaining"],
    stat_categories,
)

comparison = compare_projections(my_projected, opp_projected, stat_categories)

# ---------------------------------------------------------------------------
# Tally
# ---------------------------------------------------------------------------

# compare_projections returns "team_a"/"team_b" — map to names for tally()
sim_rows = [
    {
        "category": r["category"],
        "team_a": r["team_a"],
        "team_b": r["team_b"],
        "winner": my_team_name if r["winner"] == "team_a"
                  else (opponent_name if r["winner"] == "team_b" else "Tie"),
    }
    for r in comparison
]
sim_df = pd.DataFrame(sim_rows)
counts = tally(sim_df, my_team_name, opponent_name)

tcol1, tcol2 = st.columns(2)
with tcol1:
    st.markdown(f"### {my_team_name}")
    st.markdown(f"## {counts[my_team_name]}")
with tcol2:
    st.markdown(f"### {opponent_name}")
    st.markdown(f"## {counts[opponent_name]}")

# ---------------------------------------------------------------------------
# Projection table
# ---------------------------------------------------------------------------

my_now_col = f"{my_team_name} now"
my_proj_col = f"{my_team_name} proj"
opp_proj_col = f"{opponent_name} proj"
opp_now_col = f"{opponent_name} now"

rows = []
for r in comparison:
    stat = r["category"]
    rows.append({
        "Category": stat,
        my_now_col: my_current.get(stat, 0.0),
        my_proj_col: r["team_a"],
        opp_proj_col: r["team_b"],
        opp_now_col: opp_current.get(stat, 0.0),
        "_winner": r["winner"],
    })

raw_df = pd.DataFrame(rows)
winners = raw_df["_winner"]
display_df = raw_df.drop(columns=["_winner"])


def _highlight_winner(row):
    styles = [""] * len(row)
    green = "background-color: rgba(0, 180, 0, 0.25)"
    cols = list(row.index)
    winner = winners.iloc[row.name]
    if winner == "team_a":
        styles[cols.index(my_proj_col)] = green
    elif winner == "team_b":
        styles[cols.index(opp_proj_col)] = green
    return styles


format_map = {
    my_now_col: "{:.0f}",
    my_proj_col: "{:.1f}",
    opp_proj_col: "{:.1f}",
    opp_now_col: "{:.0f}",
}

n_rows = len(display_df)
table_height = n_rows * 35 + 38

styled = (
    display_df
    .style
    .apply(_highlight_winner, axis=1)
    .format(format_map)
)

st.dataframe(styled, use_container_width=True, hide_index=True, height=table_height)

# ---------------------------------------------------------------------------
# Per-team player breakdown
# ---------------------------------------------------------------------------

def _player_breakdown(roster, lastmonth_stats, games_remaining, stat_categories):
    """Build a per-player projection breakdown DataFrame for one team."""
    enabled = [c["stat_name"] for c in stat_categories if c["is_enabled"]]
    rows = []
    for player in roster:
        remaining = games_remaining.get(player["team_abbr"], 0)
        lm = lastmonth_stats.get(player["player_key"], {})
        gp = lm.get("games_played", 0)
        row = {
            "Player": player["player_name"],
            "Slot": player["roster_slot"],
            "Games Left": remaining,
        }
        for stat in enabled:
            if _is_rate_stat(stat):
                # Rate stats (GAA, SV%) are already per-game — show the lastmonth rate directly.
                row[stat] = lm.get(stat, 0.0)
            else:
                row[stat] = (lm.get(stat, 0.0) / gp * remaining) if gp > 0 else 0.0
        rows.append(row)
    df = pd.DataFrame(rows)
    return df.sort_values("Games Left", ascending=False)


breakdown_fmt = {s: "{:.1f}" for s in enabled_stats}
breakdown_fmt["Games Left"] = "{:.0f}"

st.subheader("Projection breakdown")
tab_my, tab_opp = st.tabs([my_team_name, opponent_name])

with tab_my:
    bd = _player_breakdown(
        pair_data["my_roster"],
        pair_data["lastmonth_stats"],
        pair_data["games_remaining"],
        stat_categories,
    )
    st.dataframe(bd.style.format(breakdown_fmt), use_container_width=True, hide_index=True)

with tab_opp:
    bd = _player_breakdown(
        pair_data["opp_roster"],
        pair_data["lastmonth_stats"],
        pair_data["games_remaining"],
        stat_categories,
    )
    st.dataframe(bd.style.format(breakdown_fmt), use_container_width=True, hide_index=True)
