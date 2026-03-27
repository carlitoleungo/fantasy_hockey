"""
Fantasy Hockey Manager — entry point.

Handles three responsibilities every page load:
  1. OAuth callback — if Yahoo redirected back with ?code=, exchange it for tokens.
  2. Session restoration — reload tokens from disk so users don't re-auth on refresh.
  3. Navigation — unauthenticated users see only a Login page; authenticated users
     see the three content pages with the league selector and logout in the sidebar.
"""
import streamlit as st

from auth.oauth import clear_session, exchange_code, get_auth_url, get_session, try_restore_session, validate_and_consume_state
from data.leagues import get_user_hockey_leagues
from utils.theme import inject_css
from utils.version import get_build_id

st.set_page_config(page_title="Carlin's Fantasy Tools", layout="wide")

# ---------------------------------------------------------------------------
# Step 1: Handle OAuth callback
# Yahoo redirects to this app with ?code=... after the user authenticates.
# Exchange the code for tokens, store in session state, clear the URL, rerun.
# ---------------------------------------------------------------------------
params = st.query_params
if "error" in params:
    st.error(f"Yahoo authorization failed: {params.get('error_description', params.get('error', 'unknown error'))}. Please try again.")
    st.query_params.clear()
    st.stop()
if "code" in params and "tokens" not in st.session_state:
    # Validate state nonce to guard against CSRF
    if not validate_and_consume_state(params.get("state", "")):
        st.error("Authentication failed: invalid or expired state parameter. Please try logging in again.")
        st.query_params.clear()
        st.stop()
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
        /* Hide CSS-injection containers (only contain a <style> tag, no real content).
           :not(:has(*:not(style))) = has no children other than style elements.
           Style tags remain parsed and active even when their container is hidden. */
        [data-testid="stMarkdownContainer"]:not(:has(*:not(style))) {
            display: none !important;
        }
        /* Match page background to the login screen so any residual containers are invisible */
        html, body, [data-testid="stAppViewContainer"],
        section.main, [data-testid="stMainBlockContainer"],
        .block-container { background-color: #131312 !important; }
        [data-testid="stVerticalBlock"] { gap: 0 !important; }
        </style>
        """, unsafe_allow_html=True)

        try:
            auth_url = get_auth_url()
            has_creds = True
        except KeyError:
            auth_url = "#"
            has_creds = False

        button_html = (
            f'<div style="text-align:center;margin-top:1.5rem;">'
            f'<a href="{auth_url}" target="_top" class="yahoo-btn">Sign in with Yahoo</a>'
            f'</div>'
        ) if has_creds else ''

        st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,700;1,400;1,700&family=Manrope:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
.yahoo-btn {{
  display:inline-flex; align-items:center; justify-content:center;
  gap:10px; background:#ffffff; color:#6001D2; border-radius:8px;
  padding:13px 28px; font-family:'Manrope',sans-serif; font-weight:700;
  font-size:0.9375rem; text-decoration:none;
  box-shadow:0 2px 10px rgba(0,0,0,0.25);
  transition:background 0.15s,box-shadow 0.15s;
}}
.yahoo-btn:hover {{
  background:#f3ecff;
  box-shadow:0 4px 16px rgba(96,1,210,0.25);
}}
</style>
<div style="min-height:560px;display:flex;flex-direction:column;align-items:center;justify-content:center;background-color:#131312;background-image:radial-gradient(circle at 2px 2px,rgba(144,144,151,0.1) 1px,transparent 0);background-size:32px 32px;position:relative;overflow:hidden;padding:3rem 1rem 1.5rem 1rem;">
<div style="position:absolute;top:-20%;left:-10%;width:60%;height:60%;background:rgba(144,212,193,0.05);border-radius:50%;filter:blur(120px);pointer-events:none;"></div>
<div style="position:absolute;bottom:-10%;right:-5%;width:50%;height:50%;background:rgba(251,187,91,0.05);border-radius:50%;filter:blur(120px);pointer-events:none;"></div>
<div style="text-align:center;margin-bottom:3rem;position:relative;z-index:1;">
<div style="display:inline-flex;align-items:center;justify-content:center;width:64px;height:64px;border-radius:12px;background-color:#2a2a28;border:1px solid rgba(63,73,69,0.15);box-shadow:0 12px 40px rgba(6,14,32,0.4);margin-bottom:24px;"><svg xmlns="http://www.w3.org/2000/svg" height="32" width="32" viewBox="0 0 24 24" fill="#90d4c1"><path d="M9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4zm2 2H5V5h14v14zm0-16H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/></svg></div>
<h1 style="font-family:'Newsreader',serif;font-size:2.5rem;font-weight:900;letter-spacing:-0.04em;text-transform:uppercase;color:#e5e2de;margin:0;line-height:1.05;">Carlin's<br>Fantasy Tools</h1>
</div>
<div style="width:100%;max-width:420px;background:rgba(30,30,28,0.8);backdrop-filter:blur(20px);border:1px solid rgba(63,73,69,0.15);border-radius:12px;padding:2rem 2rem 1.5rem 2rem;box-shadow:0 24px 64px rgba(6,14,32,0.6);position:relative;z-index:1;">
<div style="text-align:center;"><h2 style="font-family:'Newsreader',serif;font-size:1.25rem;font-weight:700;color:#e5e2de;margin:0 0 8px 0;letter-spacing:-0.01em;">Connect your Yahoo account</h2>
<p style="font-family:'Inter',sans-serif;font-size:0.875rem;color:#89938f;margin:0;font-weight:500;">Sign in to access your leagues and start scouting</p></div>
{button_html}
</div>
</div>
        """, unsafe_allow_html=True)

        if not has_creds:
            st.error("Yahoo credentials not configured. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your client ID and secret.")
        st.markdown(
            f'<p style="font-family:\'Manrope\',sans-serif;font-size:0.5625rem;'
            f'color:rgba(137,147,143,0.35);text-align:center;margin-top:16px;'
            f'letter-spacing:0.1em;text-transform:uppercase;">'
            f'build {get_build_id()}</p>',
            unsafe_allow_html=True,
        )

    pg = st.navigation([st.Page(_login_page, title="Login")])
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

        # Warn if the selected league uses a scoring format not yet fully supported.
        # Don't filter it out — support for other formats is planned.
        _SCORING_LABELS = {
            "head":       "head-to-head categories",
            "headpoint":  "head-to-head points",
            "point":      "rotisserie points",
            "rotisserie": "rotisserie categories",
        }
        _SUPPORTED = {"head"}
        selected_league = next(
            (lg for lg in leagues if lg["league_key"] == selected_key), None
        )
        if selected_league:
            scoring = selected_league.get("scoring_type", "")
            if scoring not in _SUPPORTED:
                label = _SCORING_LABELS.get(scoring, scoring)
                st.warning(
                    f"This league uses **{label}** scoring. "
                    "Full support for this format is coming soon — "
                    "some features may not work correctly."
                )

    else:
        st.warning("No active leagues found for your account.")

    st.markdown('<div style="height:1px;background:rgba(63,73,69,0.1);margin:8px 0 4px 0;"></div>', unsafe_allow_html=True)

    if st.button("Log out", use_container_width=True, key="sidebar_logout"):
        clear_session()
        for key in ("leagues", "league_key", "matchups_df", "matchups_league_key", "current_week"):
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown(
        f'<p style="font-family:\'Manrope\',sans-serif;font-size:0.5625rem;'
        f'color:rgba(137,147,143,0.4);text-align:center;margin-top:12px;'
        f'letter-spacing:0.1em;text-transform:uppercase;">'
        f'build {get_build_id()}</p>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Step 6: Content navigation
# ---------------------------------------------------------------------------
pg = st.navigation([
    st.Page("pages/01_league_overview.py", title="League Overview"),
    st.Page("pages/03_waiver_wire.py",     title="Waiver Wire"),
    st.Page("pages/04_week_projection.py", title="Week Projection"),
])
pg.run()
