"""
Design system: "Tactical Organic"

Inject the full CSS into every Streamlit page via inject_css().
Handles:
  - Google Fonts (Newsreader, Inter, Manrope)
  - CSS custom properties (design tokens)
  - Global Streamlit overrides (backgrounds, sidebar, nav links, widgets)
  - Reusable component classes (cards, tables, headers, metric cards)
  - Grid-motif background and scrollbar
"""

import streamlit as st

# ── CSS ─────────────────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,700;1,400;1,700&family=Manrope:wght@400;500;600;700&family=Inter:wght@400;500;600&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap');

/* ── Design tokens ──────────────────────────────────────────────────────── */
:root {
    --c-surface:            #131312;
    --c-surface-low:        #1c1c1a;
    --c-surface-container:  #20201e;
    --c-surface-high:       #2a2a28;
    --c-surface-highest:    #353532;
    --c-primary:            #90d4c1;
    --c-primary-container:  #266b5c;
    --c-on-primary-container: #a5e9d6;
    --c-secondary:          #fbbb5b;
    --c-tertiary:           #ffb599;
    --c-tertiary-container: #9b4825;
    --c-on-surface:         #e5e2de;
    --c-on-surface-variant: #bfc9c4;
    --c-outline:            #89938f;
    --c-outline-variant:    #3f4945;
    --c-error:              #ffb4ab;
    --c-error-container:    #93000a;
    --c-yahoo-purple:       #6001D2;
}

/* ── Global ─────────────────────────────────────────────────────────────── */
.stApp {
    background-color: var(--c-surface) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--c-on-surface) !important;
}

/* Main content area: slightly lighter + grid motif */
[data-testid="stAppViewContainer"] > section.main {
    background-color: var(--c-surface-low) !important;
    background-image: radial-gradient(circle, rgba(229,226,222,0.02) 1px, transparent 1px) !important;
    background-size: 24px 24px !important;
}

/* Remove the default top padding on the main block container */
[data-testid="stMainBlockContainer"] {
    padding-top: 2rem !important;
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--c-surface) !important;
    border-right: 1px solid var(--c-surface-low) !important;
}

[data-testid="stSidebar"] > div:first-child {
    background-color: var(--c-surface) !important;
}

/* Sidebar text overrides */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: var(--c-on-surface) !important;
}

/* ── Sidebar navigation (st.navigation()) ───────────────────────────────── */
[data-testid="stSidebarNavLink"] {
    border-radius: 6px !important;
    padding: 10px 16px !important;
    color: var(--c-outline) !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    transition: background-color 0.15s, color 0.15s !important;
    text-decoration: none !important;
}

[data-testid="stSidebarNavLink"]:hover {
    background-color: var(--c-surface-low) !important;
    color: var(--c-on-surface) !important;
}

[data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: var(--c-primary-container) !important;
    color: var(--c-on-surface) !important;
    font-weight: 600 !important;
}

/* Nav icon colour */
[data-testid="stSidebarNavLink"] svg {
    color: inherit !important;
    fill: currentColor !important;
}

/* ── Sidebar branding element ───────────────────────────────────────────── */
.sidebar-brand {
    padding: 0 16px 8px 16px;
    margin-bottom: 4px;
}
.sidebar-team-name {
    font-family: 'Newsreader', serif !important;
    font-size: 1.25rem !important;
    font-style: italic !important;
    color: var(--c-on-surface) !important;
    margin: 0 !important;
    line-height: 1.3 !important;
}
.sidebar-subtitle {
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.625rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.2em !important;
    color: var(--c-outline) !important;
    margin: 0 !important;
}

/* ── Buttons ────────────────────────────────────────────────────────────── */
/* Base style — muted chip look. Applies to all buttons including secondary.
   Primary buttons override this below using the higher-specificity [kind] rule. */
.stButton > button {
    background: var(--c-surface-highest) !important;
    color: var(--c-outline) !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.6875rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 6px 12px !important;
    transition: background 0.12s, color 0.12s !important;
}
.stButton > button:hover {
    background: var(--c-surface-high) !important;
    color: var(--c-on-surface) !important;
}
.stButton > button:active {
    transform: scale(0.98) !important;
}

/* Active/primary button: flat green — same size as base to keep uniform height.
   [kind="primary"] specificity (0,2,1) beats base (0,1,1). */
.stButton > button[kind="primary"] {
    background: var(--c-primary-container) !important;
    color: var(--c-primary) !important;
    font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1e5a4d !important;
    color: var(--c-on-primary-container) !important;
    opacity: 1 !important;
}

/* ── Selectbox ──────────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background-color: var(--c-surface-container) !important;
    border: 1px solid rgba(63,73,69,0.2) !important;
    border-radius: 8px !important;
    color: var(--c-on-surface) !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.75rem !important;
}

/* ── Radio ──────────────────────────────────────────────────────────────── */
[data-testid="stRadio"] label {
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.8125rem !important;
    color: var(--c-on-surface) !important;
}
[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.6875rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.15em !important;
    color: var(--c-outline) !important;
    font-weight: 700 !important;
}

/* ── Multiselect ────────────────────────────────────────────────────────── */
[data-testid="stMultiSelect"] > div > div {
    background-color: var(--c-surface-container) !important;
    border: 1px solid rgba(63,73,69,0.2) !important;
    border-radius: 8px !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.75rem !important;
}

/* ── Checkbox ───────────────────────────────────────────────────────────── */
[data-testid="stCheckbox"] label {
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.8125rem !important;
    color: var(--c-on-surface-variant) !important;
}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-testid="stTab"] {
    font-family: 'Newsreader', serif !important;
    font-size: 1.0625rem !important;
    font-weight: 700 !important;
    color: var(--c-outline) !important;
}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
    color: var(--c-on-surface) !important;
    border-bottom-color: var(--c-primary) !important;
}
[data-testid="stTabs"] {
    border-bottom: 1px solid var(--c-surface-highest) !important;
}

/* ── Spinner ────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] {
    color: var(--c-primary) !important;
}

/* ── Metrics (fallback if still used) ──────────────────────────────────── */
[data-testid="stMetric"] {
    background-color: var(--c-surface-container) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Manrope', sans-serif !important;
    color: var(--c-outline) !important;
    font-size: 0.625rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.2em !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Newsreader', serif !important;
    color: var(--c-on-surface) !important;
    font-style: italic !important;
}

/* ── Dataframe ──────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border-left: 4px solid var(--c-primary-container) !important;
}
[data-testid="stDataFrame"] thead th {
    background-color: rgba(53,53,50,0.3) !important;
    color: var(--c-outline) !important;
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.625rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-weight: 700 !important;
}
[data-testid="stDataFrame"] tbody td {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8125rem !important;
    color: var(--c-on-surface) !important;
}

/* ── Alerts / info boxes ────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    background-color: var(--c-surface-container) !important;
    border-radius: 8px !important;
    border: none !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Captions ───────────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] {
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.75rem !important;
    color: var(--c-outline) !important;
}

/* ── Dividers ───────────────────────────────────────────────────────────── */
hr {
    border-color: rgba(63,73,69,0.2) !important;
    margin: 1.5rem 0 !important;
}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--c-surface); }
::-webkit-scrollbar-thumb { background: var(--c-surface-highest); border-radius: 10px; }

/* ── Page header component ──────────────────────────────────────────────── */
/* Overrides the Streamlit-rendered h1 and h2 in the main content area */
[data-testid="stMainBlockContainer"] h1 {
    font-family: 'Newsreader', serif !important;
    font-size: 2.5rem !important;
    font-style: italic !important;
    font-weight: 700 !important;
    color: var(--c-on-surface) !important;
    letter-spacing: -0.02em !important;
    line-height: 1.1 !important;
    margin-bottom: 0.25rem !important;
}
[data-testid="stMainBlockContainer"] h2 {
    font-family: 'Newsreader', serif !important;
    font-style: italic !important;
    color: var(--c-on-surface) !important;
    font-size: 1.75rem !important;
}
[data-testid="stMainBlockContainer"] h3 {
    font-family: 'Newsreader', serif !important;
    color: var(--c-on-surface) !important;
}

/* ── CSS-only component classes (used in st.html / st.markdown HTML) ─────── */

/* Page header */
.fh-page-header { margin-bottom: 2rem; }
.fh-page-title {
    font-family: 'Newsreader', serif;
    font-size: 2.5rem;
    font-style: italic;
    font-weight: 700;
    color: var(--c-on-surface);
    margin: 0;
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.fh-page-subtitle {
    font-family: 'Manrope', sans-serif;
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--c-outline);
    margin: 0.25rem 0 0 0;
    font-weight: 700;
}
.fh-page-instructions {
    font-family: 'Inter', sans-serif;
    font-size: 0.8125rem;
    color: var(--c-outline);
    margin: 0.75rem 0 0 0;
    line-height: 1.6;
    max-width: 640px;
}

/* Section card with teal left border */
.fh-card {
    background-color: var(--c-surface-low);
    border-radius: 12px;
    border-left: 4px solid var(--c-primary-container);
    overflow: hidden;
    margin-bottom: 2.5rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}
.fh-card-header {
    padding: 1.5rem;
    border-bottom: 1px solid rgba(63,73,69,0.05);
}
.fh-card-title {
    font-family: 'Newsreader', serif;
    font-size: 1.5rem;
    color: var(--c-on-surface);
    margin: 0;
}

/* Section divider header (italic with faint line) */
.fh-section-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 2rem 0 1.5rem 0;
}
.fh-section-title {
    font-family: 'Newsreader', serif;
    font-size: 1.5rem;
    font-style: italic;
    color: var(--c-on-surface);
    margin: 0;
    white-space: nowrap;
}
.fh-section-rule {
    flex: 1;
    height: 1px;
    background-color: rgba(63,73,69,0.2);
}

/* Metric cards (3-up layout: my wins | tied | opp wins) */
.fh-metric-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2rem;
}
.fh-metric-card {
    background-color: var(--c-surface-container);
    border-radius: 12px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    position: relative;
    overflow: hidden;
}
.fh-metric-card-inner {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}
.fh-metric-label {
    font-family: 'Manrope', sans-serif;
    font-size: 0.625rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    font-weight: 700;
}
.fh-metric-icon { font-size: 0.875rem; }
.fh-metric-value {
    font-family: 'Newsreader', serif;
    font-size: 3rem;
    font-style: italic;
    font-weight: 700;
    color: var(--c-on-surface);
    line-height: 1;
}

/* Matchup summary cards (week projection: large centered numbers) */
.fh-matchup-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2rem;
}
.fh-matchup-card {
    background-color: var(--c-surface-low);
    border-radius: 12px;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.fh-matchup-card-label {
    font-family: 'Manrope', sans-serif;
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--c-outline);
    margin-bottom: 1rem;
    font-weight: 500;
}
.fh-matchup-card-value {
    font-family: 'Newsreader', serif;
    font-size: 4.5rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 0.5rem;
}
.fh-matchup-card-sublabel {
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--c-outline);
    font-weight: 700;
}
.fh-matchup-card-glow {
    position: absolute;
    top: -20%;
    right: -15%;
    width: 120px;
    height: 120px;
    border-radius: 50%;
    filter: blur(40px);
    opacity: 0.3;
}

/* Data table */
.fh-table-wrap {
    overflow-x: auto;
}
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
}
.fh-table td.fh-num { text-align: right; }

/* Best/worst cell highlights */
.fh-cell-best {
    background-color: rgba(38,107,92,0.4) !important;
    color: var(--c-on-primary-container) !important;
    font-weight: 700 !important;
}
.fh-cell-worst {
    background-color: rgba(147,0,10,0.2) !important;
    color: var(--c-error) !important;
}

/* Comparison table: winner cell */
.fh-cell-win {
    background-color: rgba(38,107,92,0.4);
    color: var(--c-on-primary-container);
    font-weight: 700;
    font-family: 'Manrope', sans-serif;
    font-size: 0.875rem;
}
.fh-cell-lose {
    color: var(--c-outline);
    font-family: 'Manrope', sans-serif;
    font-size: 0.875rem;
}

/* Selected row (team highlighted in weekly scores) */
.fh-row-selected { background-color: rgba(38,107,92,0.08) !important; }
.fh-row-selected td:first-child {
    border-left: 3px solid var(--c-primary-container);
    color: var(--c-primary) !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
}

/* Table footer (pagination) */
.fh-table-footer {
    padding: 12px 16px;
    background-color: rgba(53,53,50,0.2);
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: 'Manrope', sans-serif;
    font-size: 0.625rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--c-outline);
    font-weight: 700;
}

/* Player name cell (two-line) */
.fh-player-name {
    font-family: 'Newsreader', serif;
    font-size: 0.9375rem;
    font-weight: 700;
    color: var(--c-on-surface);
    margin: 0;
}
.fh-player-meta {
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    color: var(--c-primary);
    margin: 0;
    font-weight: 600;
    letter-spacing: 0.05em;
}

/* Status badges */
.fh-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}
.fh-badge-healthy { background-color: var(--c-surface-highest); color: var(--c-outline); }
.fh-badge-dtd     { background-color: rgba(155,72,37,0.3); color: var(--c-tertiary); }
.fh-badge-out     { background-color: rgba(147,0,10,0.3); color: var(--c-error); }

/* Controls section panel */
.fh-controls-panel {
    background-color: var(--c-surface-low);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 2rem;
}
.fh-control-label {
    font-family: 'Manrope', sans-serif;
    font-size: 0.5625rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--c-outline);
    font-weight: 700;
    margin-bottom: 0.75rem;
    display: block;
}

/* ── Mobile bottom navigation ───────────────────────────────────────────── */
/* Hidden on desktop; shown via the @media block below */
.fh-mobile-nav {
    display: none;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 64px;
    background-color: rgba(32,32,30,0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-top: 1px solid rgba(63,73,69,0.15);
    z-index: 999;
    align-items: center;
    justify-content: space-around;
    padding-bottom: env(safe-area-inset-bottom, 0px);
}
.fh-mobile-nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    text-decoration: none;
    color: var(--c-outline);
    padding: 8px 16px;
    min-width: 56px;
    transition: color 0.15s;
}
.fh-mobile-nav-item.active { color: var(--c-primary); }
.fh-mobile-nav-icon {
    font-family: 'Material Symbols Outlined';
    font-size: 1.375rem;
    font-weight: normal;
    font-style: normal;
    line-height: 1;
    letter-spacing: normal;
    text-transform: none;
    white-space: nowrap;
    word-wrap: normal;
    direction: ltr;
    -webkit-font-smoothing: antialiased;
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}
.fh-mobile-nav-item.active .fh-mobile-nav-icon {
    font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}
.fh-mobile-nav-label {
    font-family: 'Manrope', sans-serif;
    font-size: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 700;
}

/* ── Mobile layout overrides ────────────────────────────────────────────── */
@media (max-width: 768px) {
    /* Show bottom nav */
    .fh-mobile-nav { display: flex !important; }

    /* Pad content so it doesn't hide under the nav bar */
    [data-testid="stAppViewContainer"] > section.main {
        padding-bottom: 72px !important;
    }

    /* Tighten the main block container padding */
    [data-testid="stMainBlockContainer"] {
        padding-top: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* Scale down the page title on small screens */
    [data-testid="stMainBlockContainer"] h1 {
        font-size: 1.75rem !important;
    }

    /* Keep all column rows in a single line — let columns shrink proportionally
       rather than wrapping to full width. Works for chip grids, position buttons,
       and any other st.columns() layout on this page. */
    [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 0 !important;
        flex-shrink: 1 !important;
    }

    /* Score cards: 2-col on mobile, hide the Tied middle card */
    .fh-matchup-row { grid-template-columns: 1fr 1fr; gap: 0.75rem; }
    .fh-matchup-card:nth-child(2) { display: none; }
    .fh-matchup-card { padding: 1.25rem; }
    .fh-matchup-card-value { font-size: 3rem; }

}
</style>
"""


def inject_css() -> None:
    """Inject the Tactical Organic design system CSS into the current page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def render_mobile_nav(active: str) -> None:
    """Inject the fixed bottom navigation bar (only visible on mobile ≤768px).

    Parameters
    ----------
    active : str
        The slug of the current page — one of:
        "league_overview", "waiver_wire", "week_projection".
    """
    _pages = [
        ("league_overview", "sports_hockey", "League"),
        ("waiver_wire",     "add_circle",    "Waiver"),
        ("week_projection", "trending_up",   "Week"),
    ]
    items_html = ""
    for slug, icon, label in _pages:
        cls = "fh-mobile-nav-item active" if active == slug else "fh-mobile-nav-item"
        items_html += (
            f'<a class="{cls}" href="/{slug}">'
            f'<span class="fh-mobile-nav-icon">{icon}</span>'
            f'<span class="fh-mobile-nav-label">{label}</span>'
            f"</a>"
        )
    st.markdown(
        f'<nav class="fh-mobile-nav">{items_html}</nav>',
        unsafe_allow_html=True,
    )
