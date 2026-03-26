"""
Shared helpers used at the top of every Streamlit page.

  require_auth()  — auth + league-key guard; stops the page if not satisfied
  load_matchups() — load matchup data into session state (cached per session/league)
"""
from __future__ import annotations

import streamlit as st

from auth.oauth import clear_session, get_session
from data import matchups
from data.matchups import get_current_week


def require_auth() -> str:
    """
    Guard: stop the page if the user is not authenticated or has no league selected.

    Call this at the top of every page before any other logic. Returns the
    league_key from session state so callers don't need to read it separately.
    """
    if "tokens" not in st.session_state:
        st.warning("Please log in first.")
        st.stop()
    league_key = st.session_state.get("league_key")
    if not league_key:
        st.warning("Please select a league on the home page.")
        st.stop()
    return league_key  # type: ignore[return-value]  # st.stop() guarantees non-None


def load_matchups(league_key: str) -> None:
    """
    Ensure matchup data is loaded into session state.

    Fetches from the API (updating the local parquet cache) if data is absent
    or the league has changed. Stores results under:
      st.session_state["matchups_df"]         — full matchup DataFrame
      st.session_state["matchups_league_key"] — league the data belongs to
      st.session_state["current_week"]        — current week number

    Stops the page on auth expiry or fetch failure.
    """
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
                current_week = get_current_week(session, league_key)
            except Exception as e:
                st.error(f"Failed to load matchup data: {e}")
                st.stop()

        st.session_state["matchups_df"] = df
        st.session_state["matchups_league_key"] = league_key
        st.session_state["current_week"] = current_week
