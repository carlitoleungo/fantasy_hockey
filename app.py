"""
Fantasy Hockey Manager — entry point.

Handles three responsibilities every page load:
  1. OAuth callback — if Yahoo redirected back with ?code=, exchange it for tokens.
  2. Session restoration — reload tokens from disk so users don't re-auth on refresh.
  3. Navigation — unauthenticated users see only a Login page; authenticated users
     see the three content pages with the league selector and logout in the sidebar.
"""
import streamlit as st

from auth.oauth import clear_session, exchange_code, get_auth_url, get_session, try_restore_session
from data.leagues import get_user_hockey_leagues

st.set_page_config(page_title="Fantasy Hockey Manager", page_icon="🏒", layout="wide")

# ---------------------------------------------------------------------------
# Step 1: Handle OAuth callback
# Yahoo redirects to this app with ?code=... after the user authenticates.
# Exchange the code for tokens, store in session state, clear the URL, rerun.
# ---------------------------------------------------------------------------
params = st.query_params
if "code" in params and "tokens" not in st.session_state:
    with st.spinner("Authenticating with Yahoo..."):
        try:
            tokens = exchange_code(params["code"])
            st.session_state["tokens"] = tokens
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            st.stop()

# ---------------------------------------------------------------------------
# Step 2: Restore session from disk
# Long-lived refresh tokens mean users stay logged in across browser sessions.
# ---------------------------------------------------------------------------
try_restore_session()

# ---------------------------------------------------------------------------
# Step 3: Unauthenticated — show only the Login page
# ---------------------------------------------------------------------------
if "tokens" not in st.session_state:
    def _login_page():
        st.title("Fantasy Hockey Manager")
        st.write("Connect your Yahoo Fantasy account to get started.")
        try:
            st.link_button("Login with Yahoo", get_auth_url())
        except KeyError:
            st.error(
                "Yahoo credentials not configured. "
                "Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` "
                "and fill in your client ID and secret."
            )

    pg = st.navigation([st.Page(_login_page, title="Login", icon="🏒")])
    pg.run()
    st.stop()

# ---------------------------------------------------------------------------
# Step 4: Authenticated — load leagues once per session
# Filter to the current (most recent) season so past-season leagues are hidden.
# ---------------------------------------------------------------------------
if "leagues" not in st.session_state:
    session = get_session()
    if session is None:
        st.warning("Your session has expired. Please log in again.")
        clear_session()
        st.rerun()

    with st.spinner("Loading your leagues..."):
        try:
            all_leagues = get_user_hockey_leagues(session)
        except Exception as e:
            st.error(f"Failed to load leagues: {e}")
            all_leagues = []

    # Keep only the current (highest) season to hide inactive past-season leagues
    if all_leagues:
        current_season = max(lg["season"] for lg in all_leagues)
        st.session_state["leagues"] = [
            lg for lg in all_leagues if lg["season"] == current_season
        ]
    else:
        st.session_state["leagues"] = []

# ---------------------------------------------------------------------------
# Step 5: Sidebar — league selector + logout (visible on all content pages)
# ---------------------------------------------------------------------------
leagues = st.session_state.get("leagues", [])

with st.sidebar:
    st.markdown("### 🏒 Fantasy Hockey")

    if leagues:
        league_keys = [lg["league_key"] for lg in leagues]
        league_labels = {
            lg["league_key"]: f"{lg['season']} — {lg['league_name']}"
            for lg in leagues
        }

        current_key = st.session_state.get("league_key")
        default_index = league_keys.index(current_key) if current_key in league_keys else 0

        selected_key = st.selectbox(
            "League",
            options=league_keys,
            format_func=lambda k: league_labels[k],
            index=default_index,
            key="sidebar_league_selector",
            label_visibility="collapsed",
        )

        # Invalidate matchups cache eagerly when the league changes
        if selected_key != st.session_state.get("league_key"):
            for key in ("matchups_df", "matchups_league_key", "current_week"):
                st.session_state.pop(key, None)

        st.session_state["league_key"] = selected_key

    else:
        st.warning("No active leagues found for your account.")

    st.divider()

    if st.button("Log out", use_container_width=True):
        clear_session()
        for key in ("leagues", "league_key", "matchups_df", "matchups_league_key", "current_week"):
            st.session_state.pop(key, None)
        st.rerun()

# ---------------------------------------------------------------------------
# Step 6: Content navigation
# ---------------------------------------------------------------------------
pg = st.navigation([
    st.Page("pages/01_league_overview.py", title="League Overview", icon="📊"),
    st.Page("pages/03_waiver_wire.py",     title="Waiver Wire",     icon="🎣"),
    st.Page("pages/04_week_projection.py", title="Week Projection", icon="📈"),
])
pg.run()
