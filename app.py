import streamlit as st

from auth.oauth import clear_session, exchange_code, get_auth_url, try_restore_session

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
    st.success("Authenticated with Yahoo!")
    st.write("Use the sidebar to navigate between pages.")

    if st.button("Log out"):
        clear_session()
        st.rerun()
