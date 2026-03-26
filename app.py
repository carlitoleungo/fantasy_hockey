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
from utils.theme import inject_css

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
        inject_css()
        # Hide the Streamlit header/toolbar and centre the content for the login page
        st.markdown("""
        <style>
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stSidebarNav"],
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stAppViewContainer"] > section.main { padding: 0 !important; }
        [data-testid="stMainBlockContainer"] {
            padding: 0 !important;
            max-width: 100% !important;
        }
        .block-container { padding: 0 !important; max-width: 100% !important; }
        </style>
        """, unsafe_allow_html=True)

        try:
            auth_url = get_auth_url()
            login_btn_html = f"""
            <a href="{auth_url}" target="_self" style="
                display: flex; align-items: center; justify-content: center; gap: 12px;
                width: 100%; padding: 16px;
                background-color: #6001D2;
                color: #ffffff;
                font-family: 'Newsreader', serif;
                font-size: 1.0625rem;
                font-weight: 800;
                letter-spacing: -0.01em;
                text-decoration: none;
                border-radius: 8px;
                box-shadow: 0 8px 20px rgba(96,1,210,0.3);
                transition: transform 0.15s;
            ">
                <svg xmlns="http://www.w3.org/2000/svg" height="20" width="20" viewBox="0 0 24 24" fill="white">
                    <path d="M11 7L9.6 8.4l2.6 2.6H2v2h10.2l-2.6 2.6L11 17l5-5-5-5zm9 12h-8v2h8c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-8v2h8v14z"/>
                </svg>
                Login with Yahoo
            </a>
            """
            error_html = ""
        except KeyError:
            login_btn_html = ""
            error_html = """
            <div style="
                background-color: rgba(147,0,10,0.15);
                border-radius: 8px;
                padding: 12px 16px;
                font-family: 'Inter', sans-serif;
                font-size: 0.8125rem;
                color: #ffb4ab;
            ">
                Yahoo credentials not configured. Copy
                <code>.streamlit/secrets.toml.example</code> to
                <code>.streamlit/secrets.toml</code> and fill in your client ID and secret.
            </div>
            """

        # Use st.html() to bypass the Markdown parser, which corrupts complex HTML.
        # Include fonts inline since st.html() renders in an isolated context.
        st.html(f"""
        <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,700;1,400;1,700&family=Manrope:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: transparent; }}
        </style>
        <div style="
            min-height: 650px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background-color: #131312;
            background-image: radial-gradient(circle at 2px 2px, rgba(144,144,151,0.1) 1px, transparent 0);
            background-size: 32px 32px;
            position: relative;
            overflow: hidden;
            padding: 3rem 1rem;
        ">
            <div style="position:absolute;top:-20%;left:-10%;width:60%;height:60%;background:rgba(144,212,193,0.05);border-radius:50%;filter:blur(120px);pointer-events:none;"></div>
            <div style="position:absolute;bottom:-10%;right:-5%;width:50%;height:50%;background:rgba(251,187,91,0.05);border-radius:50%;filter:blur(120px);pointer-events:none;"></div>

            <div style="text-align:center;margin-bottom:3rem;position:relative;z-index:1;">
                <div style="display:inline-flex;align-items:center;justify-content:center;width:64px;height:64px;border-radius:12px;background-color:#2a2a28;border:1px solid rgba(63,73,69,0.15);box-shadow:0 12px 40px rgba(6,14,32,0.4);margin-bottom:24px;">
                    <svg xmlns="http://www.w3.org/2000/svg" height="32" width="32" viewBox="0 0 24 24" fill="#90d4c1"><path d="M9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4zm2 2H5V5h14v14zm0-16H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/></svg>
                </div>
                <h1 style="font-family:'Newsreader',serif;font-size:2.5rem;font-weight:900;letter-spacing:-0.04em;text-transform:uppercase;color:#e5e2de;margin:0 0 8px 0;line-height:1.05;">Fantasy Hockey<br>Manager</h1>
                <p style="font-family:'Newsreader',serif;font-size:1.0625rem;font-weight:600;color:#ffb599;letter-spacing:-0.01em;margin:0;">Your tactical edge on the waiver wire</p>
            </div>

            <div style="width:100%;max-width:420px;background:rgba(30,30,28,0.8);backdrop-filter:blur(20px);border:1px solid rgba(63,73,69,0.15);border-radius:12px;padding:2rem;box-shadow:0 24px 64px rgba(6,14,32,0.6);position:relative;z-index:1;">
                <div style="text-align:center;margin-bottom:2rem;">
                    <h2 style="font-family:'Newsreader',serif;font-size:1.25rem;font-weight:700;color:#e5e2de;margin:0 0 8px 0;letter-spacing:-0.01em;">Connect your Yahoo account</h2>
                    <p style="font-family:'Inter',sans-serif;font-size:0.875rem;color:#89938f;margin:0;font-weight:500;">Sign in to access your leagues and start scouting</p>
                </div>

                {login_btn_html}
                {error_html}

                <div style="margin-top:1.5rem;text-align:center;">
                    <div style="display:flex;align-items:center;gap:8px;justify-content:center;font-family:'Manrope',sans-serif;font-size:0.625rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:#89938f;">
                        <span style="height:1px;width:32px;background:rgba(63,73,69,0.3);display:inline-block;"></span>
                        Secure Infrastructure
                        <span style="height:1px;width:32px;background:rgba(63,73,69,0.3);display:inline-block;"></span>
                    </div>
                </div>
            </div>

            <div style="margin-top:3rem;display:flex;align-items:center;gap:8px;font-family:'Manrope',sans-serif;font-size:0.625rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:#89938f;position:relative;z-index:1;">
                <div style="width:6px;height:6px;border-radius:50%;background-color:#90d4c1;box-shadow:0 0 8px rgba(144,212,193,0.6);"></div>
                Tactical Core Active
            </div>
        </div>
        """)

    pg = st.navigation([st.Page(_login_page, title="Login", icon="🏒")])
    pg.run()
    st.stop()

# ---------------------------------------------------------------------------
# Step 3.5: Inject design system CSS (authenticated pages only)
# ---------------------------------------------------------------------------
inject_css()

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
    st.markdown("""
    <div class="sidebar-brand">
        <p class="sidebar-team-name">Fantasy Hockey</p>
        <p class="sidebar-subtitle">Manager</p>
    </div>
    """, unsafe_allow_html=True)

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

    st.markdown('<div style="height:1px;background:rgba(63,73,69,0.1);margin:8px 0 4px 0;"></div>', unsafe_allow_html=True)

    if st.button("Log out", use_container_width=True, key="sidebar_logout"):
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
