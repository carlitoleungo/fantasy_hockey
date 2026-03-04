import streamlit as st

from auth.oauth import clear_session, exchange_code, get_auth_url, get_session, try_restore_session
from data.leagues import get_user_hockey_leagues

st.set_page_config(page_title="Fantasy Hockey Manager", page_icon="🏒", layout="wide")

# ---------------------------------------------------------------------------
# Step 1: Handle OAuth callback
# Yahoo redirects back to this app with ?code=... after the user authenticates.
# We detect this on the first rerun after the redirect, exchange the code for
# tokens, store them in session state, clear the URL, and rerun cleanly.
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
# Step 2: Restore session from disk if this is a fresh browser session.
# This means users who already authenticated don't have to log in again
# until their refresh token expires (Yahoo refresh tokens are long-lived).
# ---------------------------------------------------------------------------
try_restore_session()

# ---------------------------------------------------------------------------
# Step 3: Render UI
# ---------------------------------------------------------------------------
st.title("Fantasy Hockey Manager")

if "tokens" not in st.session_state:
    # --- Unauthenticated ---
    st.write("Connect your Yahoo Fantasy account to get started.")

    try:
        auth_url = get_auth_url()
        st.link_button("Login with Yahoo", auth_url)
    except KeyError:
        st.error(
            "Yahoo credentials not configured. "
            "Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` "
            "and fill in your client ID and secret."
        )

else:
    # --- Authenticated ---
    st.success("Authenticated with Yahoo!")

    # Load the user's hockey leagues once per session. Doing this here (rather
    # than inside the selectbox callback) means we only hit the API on the
    # first load, not on every Streamlit interaction.
    if "leagues" not in st.session_state:
        session = get_session()
        if session is None:
            # Token refresh failed — force re-auth
            st.warning("Your session has expired. Please log in again.")
            clear_session()
            st.rerun()

        with st.spinner("Loading your leagues..."):
            try:
                st.session_state["leagues"] = get_user_hockey_leagues(session)
            except Exception as e:
                st.error(f"Failed to load leagues: {e}")
                st.session_state["leagues"] = []

    leagues = st.session_state.get("leagues", [])

    if not leagues:
        st.warning("No Yahoo Fantasy Hockey leagues found for your account.")
    else:
        # Build a display label for each league: "2024 — My League Name"
        def league_label(league: dict) -> str:
            return f"{league['season']} — {league['league_name']}"

        league_keys = [lg["league_key"] for lg in leagues]
        league_labels = {lg["league_key"]: league_label(lg) for lg in leagues}

        # Preserve existing selection across reruns
        current_key = st.session_state.get("league_key")
        default_index = league_keys.index(current_key) if current_key in league_keys else 0

        selected_key = st.selectbox(
            "Select league:",
            options=league_keys,
            format_func=lambda k: league_labels[k],
            index=default_index,
        )
        st.session_state["league_key"] = selected_key

        st.write("Use the sidebar to navigate between pages.")

    if st.button("Log out"):
        # Clear auth tokens AND league state so a fresh login starts clean
        clear_session()
        for key in ("leagues", "league_key"):
            st.session_state.pop(key, None)
        st.rerun()
