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
from utils.common import require_auth
from utils.theme import inject_css

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

inject_css()
league_key = require_auth()

# ---------------------------------------------------------------------------
# Header + refresh
# ---------------------------------------------------------------------------

title_col, btn_col = st.columns([5, 1])
with title_col:
    st.markdown("""
    <div class="fh-page-header">
        <h1 class="fh-page-title">Week Projection</h1>
        <p class="fh-page-subtitle">See how your current matchup is likely to end.</p>
        <p class="fh-page-instructions">Select your team and your opponent. Each category is projected using rostered players&#8217; last-30-day per-game averages multiplied by their remaining NHL games this week. Hit Refresh to update rosters and live stats.</p>
    </div>
    """, unsafe_allow_html=True)
with btn_col:
    st.markdown('<div style="margin-top:1.75rem;"></div>', unsafe_allow_html=True)
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

my_team_name = st.selectbox("My team", options=team_names, key="proj_my_team",
                           label_visibility="collapsed")
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
st.markdown(
    f'<p class="fh-page-subtitle" style="margin-bottom:1.5rem;">'
    f"Matchup: Week {current_week} vs {opponent_name} · "
    f"{scoreboard_data['week_start']} – {scoreboard_data['week_end']}"
    f"</p>",
    unsafe_allow_html=True,
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
            # Use today's date so dropped players are excluded from projections.
            # (A player dropped mid-week should no longer contribute projected points,
            # though their past points are already captured in the live team totals.)
            today_str = date.today().isoformat()
            my_roster = roster_module.get_team_roster(session, my_team_key, date=today_str)
            opp_roster = roster_module.get_team_roster(session, opponent_key, date=today_str)

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

st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.5rem;margin-bottom:2rem;">
    <!-- My team -->
    <div style="
        background:#1c1c1a; border-radius:12px; padding:2rem;
        border-left:4px solid #90d4c1;
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        text-align:center; position:relative; overflow:hidden;
        box-shadow:0 4px 24px rgba(0,0,0,0.3);
    ">
        <div style="position:absolute;top:-20%;right:-15%;width:120px;height:120px;
            background:rgba(144,212,193,0.08);border-radius:50%;filter:blur(40px);"></div>
        <p style="font-family:'Manrope',sans-serif;font-size:0.6875rem;text-transform:uppercase;
            letter-spacing:0.2em;color:#89938f;margin:0 0 1rem 0;font-weight:500;">{my_team_name}</p>
        <div style="font-family:'Newsreader',serif;font-size:4.5rem;font-weight:700;
            color:#90d4c1;line-height:1;">{counts[my_team_name]}</div>
        <p style="font-family:'Manrope',sans-serif;font-size:0.5625rem;text-transform:uppercase;
            letter-spacing:0.2em;color:#89938f;margin:0.5rem 0 0 0;font-weight:700;">Projected Wins</p>
    </div>
    <!-- Tied -->
    <div style="
        background:#1c1c1a; border-radius:12px; padding:2rem;
        border-left:4px solid rgba(137,147,143,0.2);
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        text-align:center; position:relative; overflow:hidden;
        box-shadow:0 4px 24px rgba(0,0,0,0.3);
    ">
        <div style="position:absolute;top:-20%;right:-15%;width:120px;height:120px;
            background:rgba(137,147,143,0.05);border-radius:50%;filter:blur(40px);"></div>
        <p style="font-family:'Manrope',sans-serif;font-size:0.6875rem;text-transform:uppercase;
            letter-spacing:0.2em;color:#89938f;margin:0 0 1rem 0;font-weight:500;">Tied</p>
        <div style="font-family:'Newsreader',serif;font-size:4.5rem;font-weight:700;
            color:#e5e2de;line-height:1;">{counts["Tie"]}</div>
        <p style="font-family:'Manrope',sans-serif;font-size:0.5625rem;text-transform:uppercase;
            letter-spacing:0.2em;color:#89938f;margin:0.5rem 0 0 0;font-weight:700;">Categories</p>
    </div>
    <!-- Opponent -->
    <div style="
        background:#1c1c1a; border-radius:12px; padding:2rem;
        border-left:4px solid #ffb599;
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        text-align:center; position:relative; overflow:hidden;
        box-shadow:0 4px 24px rgba(0,0,0,0.3);
    ">
        <div style="position:absolute;top:-20%;right:-15%;width:120px;height:120px;
            background:rgba(255,181,153,0.05);border-radius:50%;filter:blur(40px);"></div>
        <p style="font-family:'Manrope',sans-serif;font-size:0.6875rem;text-transform:uppercase;
            letter-spacing:0.2em;color:#89938f;margin:0 0 1rem 0;font-weight:500;">{opponent_name}</p>
        <div style="font-family:'Newsreader',serif;font-size:4.5rem;font-weight:700;
            color:#ffb599;line-height:1;">{counts[opponent_name]}</div>
        <p style="font-family:'Manrope',sans-serif;font-size:0.5625rem;text-transform:uppercase;
            letter-spacing:0.2em;color:#89938f;margin:0.5rem 0 0 0;font-weight:700;">Projected Wins</p>
    </div>
</div>
""", unsafe_allow_html=True)

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
    cols = list(row.index)
    winner = winners.iloc[row.name]
    if winner == "team_a":
        styles[cols.index(my_proj_col)] = (
            "background-color: rgba(38,107,92,0.15); color: #a5e9d6; font-weight: 600"
        )
    elif winner == "team_b":
        styles[cols.index(opp_proj_col)] = (
            "background-color: rgba(147,0,10,0.1); color: #ffb599; font-weight: 600"
        )
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

st.markdown("""
<div style="display:flex;align-items:center;gap:1rem;margin:2rem 0 1rem 0;">
    <h3 style="font-family:'Newsreader',serif;font-size:1.5rem;font-style:italic;
        color:#e5e2de;margin:0;white-space:nowrap;">Roster Breakdown</h3>
    <div style="flex:1;height:1px;background:rgba(63,73,69,0.2);"></div>
</div>
""", unsafe_allow_html=True)
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
