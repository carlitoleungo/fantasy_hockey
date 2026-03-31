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

import html as _html
from datetime import date

import pandas as pd
import streamlit as st

from analysis.matchup_sim import tally
from analysis.projection import _is_rate_stat, compare_projections, project_team_stats
from analysis.team_scores import lower_is_better_from_categories
from auth.oauth import clear_session, get_session
from data import client, players as players_module, roster as roster_module
from data import schedule as schedule_module
from data import scoreboard as scoreboard_module
from utils.common import require_auth
from utils.theme import inject_css, render_mobile_nav

# ---------------------------------------------------------------------------
# Embedded CSS for st.html() shadow contexts
# ---------------------------------------------------------------------------

_TABLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,700;1,400;1,700&family=Manrope:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
:root {
    --c-surface:              #131312;
    --c-surface-low:          #1c1c1a;
    --c-surface-container:    #20201e;
    --c-surface-highest:      #353532;
    --c-primary:              #90d4c1;
    --c-primary-container:    #266b5c;
    --c-on-primary-container: #a5e9d6;
    --c-on-surface:           #e5e2de;
    --c-outline:              #89938f;
    --c-outline-variant:      #3f4945;
}
* { box-sizing: border-box; }
.fh-table-wrap { overflow-x: auto; }
.fh-table {
    width: 100%;
    border-collapse: collapse;
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
/* Sticky first column */
.fh-table th:first-child,
.fh-table td:first-child {
    position: sticky;
    left: 0;
    background-color: #1c1c1a;
    z-index: 2;
}
/* Winner / loser cells */
.fh-cell-win {
    background-color: rgba(38,107,92,0.4);
    color: #a5e9d6;
    font-weight: 700;
    text-align: right;
    padding: 14px 16px;
    font-family: 'Manrope', sans-serif;
}
.fh-cell-lose {
    color: #89938f;
    text-align: right;
    padding: 14px 16px;
}
.fh-cell-num {
    text-align: right;
    padding: 14px 16px;
}
/* Player name / meta */
.fh-player-name {
    font-family: 'Newsreader', serif;
    font-size: 0.9375rem;
    font-weight: 700;
    color: #e5e2de;
    margin: 0;
    line-height: 1.2;
}
.fh-player-meta {
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    color: #90d4c1;
    margin: 0;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.fh-swipe-hint {
    font-family: 'Manrope', sans-serif;
    font-size: 0.625rem;
    text-align: center;
    color: #89938f;
    font-style: italic;
    padding: 8px 0;
    margin: 0;
}
</style>
"""

# ---------------------------------------------------------------------------
# HTML table builders
# ---------------------------------------------------------------------------

def _build_category_table(comparison, my_team_name, opponent_name):
    """3-column projection comparison table (Category | My Proj | Opp Proj)."""
    my_label  = _html.escape(f"{my_team_name} (Proj)")
    opp_label = _html.escape(f"{opponent_name} (Proj)")

    header = (
        f'<thead><tr>'
        f'<th>Category</th>'
        f'<th style="text-align:right;">{my_label}</th>'
        f'<th style="text-align:right;">{opp_label}</th>'
        f'</tr></thead>'
    )

    body_rows = []
    for r in comparison:
        stat   = _html.escape(r["category"])
        winner = r["winner"]
        fmt    = ".2f" if _is_rate_stat(r["category"]) else ".1f"
        my_val  = format(float(r["team_a"]), fmt)
        opp_val = format(float(r["team_b"]), fmt)

        if winner == "team_a":
            my_td  = f'<td class="fh-cell-win">{my_val}</td>'
            opp_td = f'<td class="fh-cell-lose">{opp_val}</td>'
        elif winner == "team_b":
            my_td  = f'<td class="fh-cell-lose">{my_val}</td>'
            opp_td = f'<td class="fh-cell-win">{opp_val}</td>'
        else:
            my_td  = f'<td class="fh-cell-num">{my_val}</td>'
            opp_td = f'<td class="fh-cell-num">{opp_val}</td>'

        body_rows.append(f'<tr><td>{stat}</td>{my_td}{opp_td}</tr>')

    return (
        f'<div class="fh-table-wrap">'
        f'<table class="fh-table">'
        f'{header}'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
        f'</div>'
    )


def _build_roster_table(rows, enabled_stats):
    """Horizontally scrollable roster table with sticky player name column."""
    stat_headers = "".join(
        f'<th style="text-align:right;">{_html.escape(s)}</th>'
        for s in ["GL"] + enabled_stats
    )
    header_row = (
        f'<th style="min-width:160px;">Player</th>'
        f'{stat_headers}'
    )

    body_rows = []
    for p in rows:
        safe_name = _html.escape(p["Player"])
        meta      = _html.escape(f'{p.get("Position", "")} · {p.get("Team", "")}')
        games_left = int(p["Games Left"])

        name_cell = (
            f'<td>'
            f'<p class="fh-player-name">{safe_name}</p>'
            f'<p class="fh-player-meta">{meta}</p>'
            f'</td>'
        )
        stat_cells = f'<td style="text-align:right;">{games_left}</td>'
        for s in enabled_stats:
            fmt = ".2f" if _is_rate_stat(s) else ".1f"
            val = format(float(p.get(s, 0.0)), fmt)
            stat_cells += f'<td style="text-align:right;">{val}</td>'

        body_rows.append(f'<tr>{name_cell}{stat_cells}</tr>')

    return (
        f'<div class="fh-table-wrap">'
        f'<table class="fh-table" style="white-space:nowrap;">'
        f'<thead><tr>{header_row}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
        f'</div>'
        f'<p class="fh-swipe-hint">Swipe to view all stats</p>'
    )


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

inject_css()
render_mobile_nav("week_projection")
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

comparison = compare_projections(
    my_projected, opp_projected, stat_categories,
    lower_is_better=lower_is_better_from_categories(stat_categories),
)

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
<div class="fh-matchup-row">
  <div class="fh-matchup-card" style="border-left:4px solid #90d4c1;box-shadow:0 4px 24px rgba(0,0,0,0.3);">
    <div class="fh-matchup-card-glow" style="background:rgba(144,212,193,0.08);"></div>
    <p class="fh-matchup-card-label">{_html.escape(my_team_name)}</p>
    <div class="fh-matchup-card-value" style="color:#90d4c1;">{counts[my_team_name]}</div>
    <p class="fh-matchup-card-sublabel">Projected Wins</p>
  </div>
  <div class="fh-matchup-card" style="border-left:4px solid rgba(137,147,143,0.2);box-shadow:0 4px 24px rgba(0,0,0,0.3);">
    <div class="fh-matchup-card-glow" style="background:rgba(137,147,143,0.05);"></div>
    <p class="fh-matchup-card-label">Tied</p>
    <div class="fh-matchup-card-value" style="color:#e5e2de;">{counts["Tie"]}</div>
    <p class="fh-matchup-card-sublabel">Categories</p>
  </div>
  <div class="fh-matchup-card" style="border-left:4px solid #ffb599;box-shadow:0 4px 24px rgba(0,0,0,0.3);">
    <div class="fh-matchup-card-glow" style="background:rgba(255,181,153,0.05);"></div>
    <p class="fh-matchup-card-label">{_html.escape(opponent_name)}</p>
    <div class="fh-matchup-card-value" style="color:#ffb599;">{counts[opponent_name]}</div>
    <p class="fh-matchup-card-sublabel">Projected Wins</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Projection table
# ---------------------------------------------------------------------------

st.html(_TABLE_CSS + _build_category_table(comparison, my_team_name, opponent_name))

# ---------------------------------------------------------------------------
# Per-team player breakdown
# ---------------------------------------------------------------------------

def _player_breakdown(roster, lastmonth_stats, games_remaining, stat_categories):
    """Build a per-player projection breakdown as a list of dicts for one team."""
    enabled = [c["stat_name"] for c in stat_categories if c["is_enabled"]]
    rows = []
    for player in roster:
        remaining = games_remaining.get(player["team_abbr"], 0)
        lm = lastmonth_stats.get(player["player_key"], {})
        gp = lm.get("games_played", 0)
        row = {
            "Player":    player["player_name"],
            "Slot":      player["roster_slot"],
            "Position":  player.get("display_position", ""),
            "Team":      player.get("team_abbr", ""),
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
    return df.sort_values("Games Left", ascending=False).to_dict("records")


st.markdown("""
<div class="fh-section-header">
    <h3 class="fh-section-title">Roster Breakdown</h3>
    <div class="fh-section-rule"></div>
</div>
""", unsafe_allow_html=True)

tab_my, tab_opp = st.tabs([my_team_name, opponent_name])

with tab_my:
    rows = _player_breakdown(
        pair_data["my_roster"],
        pair_data["lastmonth_stats"],
        pair_data["games_remaining"],
        stat_categories,
    )
    st.html(_TABLE_CSS + _build_roster_table(rows, enabled_stats))

with tab_opp:
    rows = _player_breakdown(
        pair_data["opp_roster"],
        pair_data["lastmonth_stats"],
        pair_data["games_remaining"],
        stat_categories,
    )
    st.html(_TABLE_CSS + _build_roster_table(rows, enabled_stats))
