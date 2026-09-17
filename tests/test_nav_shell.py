"""
The nav shell contract — the canonical home for every nav/header assertion.

`base.html` renders the nav conditionally on the `is_authenticated` /
`demo_mode` / `selected_league_name` keys that `shell_context()` supplies
(DECISIONS.md 2026-07-03). This module owns that contract across all three
feature route modules, so a change to the nav has one place to fail.

What is asserted here, and why in this shape:
  - Nav assertions are scoped to the <nav> element via `_nav_links`, not to the
    whole response body, so link ordering (Overview -> Waiver -> Projection,
    DECISIONS.md 2026-04-19) is actually proved.
  - League-label assertions are scoped to the header-left region via
    `_header_left`. A whole-body `"Alpha League" in response.text` does not
    discriminate — the league list in the content area repeats the string, so a
    render that blanks the header label still passes.
  - The `base.html` default path (neither flag in context) is asserted directly
    against the template, independent of any route. Since 044 that default is
    fail-safe: absent flags render the nav-free header, so a page which forgets
    `shell_context()` degrades visibly instead of claiming the visitor is
    logged in (DECISIONS.md 2026-07-25).
  - Every full-page branch that spreads `**shell_context(...)` has a case here,
    including the empty-state branches. Those fail silently when the spread is
    dropped: the page still returns 200 and still renders, it just serves the
    wrong nav.

Ticket 036a established the helpers; 036b added the demo and authenticated
feature-page cases; 040 renamed the module off its `_qa` suffix (DECISIONS.md
2026-07-26) and closed the five uncovered `web/routes/overview.py` branches.
042 added the exception-handler cases: the two error pages declare
`auth_state_unknown` and render nav-free (DECISIONS.md 2026-07-25).
"""

from __future__ import annotations

import re
import sqlite3
import time
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from fastapi.testclient import TestClient

from db.connection import db_dep
from web.main import app
from web.routes.common import shell_context, unknown_auth_shell_context
from web.templates import templates


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

LEAGUE_A = {
    "league_key": "419.l.11111",
    "league_name": "Alpha League",
    "season": "2025",
}


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE user_sessions (
            session_id  TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at   REAL,
            created_at   REAL,
            league_key   TEXT
        );
        CREATE TABLE oauth_states (
            state TEXT PRIMARY KEY,
            expires_at REAL
        );
    """)
    return conn


def _insert_session(conn, session_id="sid-test", league_key=None):
    conn.execute(
        "INSERT INTO user_sessions"
        " (session_id, access_token, refresh_token, expires_at, created_at, league_key)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, "acc-token", "ref-token", time.time() + 3600, time.time(), league_key),
    )
    conn.commit()


@pytest.fixture()
def ctx():
    conn = _make_db()

    def override_db():
        yield conn

    app.dependency_overrides[db_dep] = override_db
    client = TestClient(app, follow_redirects=False)
    yield conn, client
    app.dependency_overrides.clear()
    conn.close()


def _nav_links(html: str) -> list[tuple[str, str]]:
    """Return [(href, link_text)] for anchors inside the <nav> element only."""
    nav = html.split("<nav", 1)[1].split("</nav>", 1)[0]
    return re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', nav)


def _header_left(html: str) -> str:
    """The part of <header> before <nav> — where the league label renders."""
    header = html.split("<header", 1)[1].split("</header>", 1)[0]
    return header.split("<nav", 1)[0]


AUTHENTICATED_NAV = [
    ("/overview", "Overview"),
    ("/waiver", "Waiver"),
    ("/projection", "Projection"),
    ("/auth/logout", "Logout"),
]

DEMO_NAV = [
    ("/demo/overview", "Overview"),
    ("/demo/waiver", "Waiver"),
    ("/demo/projection", "Projection"),
    ("/auth/login", "Log in with Yahoo"),
]


# ---------------------------------------------------------------------------
# shell_context() unit behaviour
# ---------------------------------------------------------------------------

def test_shell_context_derives_is_authenticated_from_user():
    assert shell_context(None) == {
        "is_authenticated": False,
        "demo_mode": False,
        "selected_league_name": None,
    }
    user = MagicMock()
    assert shell_context(user, demo=True, league_name="Alpha League") == {
        "is_authenticated": True,
        "demo_mode": True,
        "selected_league_name": "Alpha League",
    }


# ---------------------------------------------------------------------------
# base.html branch matrix, asserted directly against the template
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "context,expected",
    [
        # 044 fail-safe default: no is_authenticated key at all -> nav-free.
        ({}, []),
        # A route passing only demo=False still has no auth flag -> nav-free.
        ({"demo_mode": False}, []),
        ({"is_authenticated": True, "demo_mode": False}, AUTHENTICATED_NAV),
        ({"is_authenticated": False, "demo_mode": False},
         [("/auth/login", "Log in with Yahoo")]),
        # Demo branch shipped in 036a, dormant until 036b adopts it.
        ({"is_authenticated": False, "demo_mode": True}, DEMO_NAV),
    ],
)
def test_base_html_nav_branches(context, expected):
    html = templates.env.get_template("base.html").render(**context)
    assert _nav_links(html) == expected


def test_base_html_absent_flags_keep_the_brand_link():
    html = templates.env.get_template("base.html").render()
    assert '<a href="/" class="font-semibold text-gray-800 hover:text-gray-600">Fantasy Hockey</a>' in _header_left(html)
    assert _nav_links(html) == []


def test_base_html_demo_nav_has_no_logout():
    html = templates.env.get_template("base.html").render(
        is_authenticated=False, demo_mode=True
    )
    assert 'href="/auth/logout"' not in html


# ---------------------------------------------------------------------------
# AC1 — logged-out home, scoped to the <nav> element
# ---------------------------------------------------------------------------

def test_logged_out_home_nav_is_login_only(ctx):
    _, client = ctx
    response = client.get("/")

    assert response.status_code == 200
    assert _nav_links(response.text) == [("/auth/login", "Log in with Yahoo")]
    # No auth-gated href anywhere on the page, not just in the nav.
    for href in ("/overview", "/waiver", "/projection", "/auth/logout"):
        assert f'href="{href}"' not in response.text


def test_logged_out_home_header_has_no_league_label(ctx):
    _, client = ctx
    response = client.get("/")

    # shell_context(None) passes selected_league_name=None, so the label span
    # must not render (this branch previously omitted the key entirely).
    assert "&middot;" not in _header_left(response.text)


# ---------------------------------------------------------------------------
# AC2 — authenticated home, scoped to <nav> and to the header-left region
# ---------------------------------------------------------------------------

def test_authenticated_home_nav_and_league_label(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch("web.routes.home.get_user_hockey_leagues", return_value=[LEAGUE_A]),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    # Exact link set and roadmap order, inside <nav> only.
    assert _nav_links(response.text) == AUTHENTICATED_NAV
    # Label must be in the header, not merely somewhere in the body: the league
    # list in the content area also contains "Alpha League".
    assert "Alpha League" in _header_left(response.text)


def test_authenticated_home_without_selected_league_has_no_label(ctx):
    conn, client = ctx
    _insert_session(conn, league_key=None)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch("web.routes.home.get_user_hockey_leagues", return_value=[LEAGUE_A]),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert _nav_links(response.text) == AUTHENTICATED_NAV
    assert "Alpha League" not in _header_left(response.text)


# ---------------------------------------------------------------------------
# Ticket 036b — demo and authenticated feature pages adopt shell_context().
#
# These replace 036a's `test_demo_pages_still_render_default_authenticated_nav`
# tripwire, which locked in the before-state that 036b deliberately flips.
# ---------------------------------------------------------------------------

DEMO_PAGES = [
    "/demo/overview",
    "/demo/waiver",
    "/demo/projection",
    "/demo/overview/head-to-head",
]


def _authenticated_feature_get(client, path):
    """GET an authenticated feature page with every Yahoo call mocked out.

    Each route module binds its data helpers by name at import time, so the
    patch target is the route module's namespace (docs/LEARNINGS.md "Tests must
    patch the importing module's namespace").
    """
    df = pd.DataFrame([
        {"team_key": "t1", "team_name": "Alpha", "week": 1, "games_played": 7,
         "Goals": 10.0, "Assists": 5.0},
        {"team_key": "t2", "team_name": "Beta", "week": 1, "games_played": 7,
         "Goals": 7.0, "Assists": 9.0},
    ])
    module = {
        "/overview": "overview",
        "/overview/head-to-head": "overview",
        "/waiver": "waiver",
        "/projection": "projection",
    }[path]

    with ExitStack() as stack:
        stack.enter_context(
            patch(f"web.routes.{module}.make_session", return_value=MagicMock())
        )
        stack.enter_context(
            patch(f"web.routes.{module}.get_user_hockey_leagues", return_value=[LEAGUE_A])
        )
        if module in ("overview", "waiver"):
            stack.enter_context(patch(f"web.routes.{module}.get_matchups", return_value=df))
        if module == "waiver":
            stack.enter_context(
                patch("web.routes.waiver.get_stat_categories", return_value=[])
            )
        if module == "projection":
            stack.enter_context(patch("web.routes.projection.get_teams", return_value=[]))
        return client.get(path, cookies={"session_id": "sid-test"})


# AC1/AC2 — demo pages render the demo nav, with no Logout link

@pytest.mark.parametrize("path", DEMO_PAGES)
def test_demo_pages_render_demo_nav(ctx, path):
    _, client = ctx
    response = client.get(path)

    assert response.status_code == 200
    assert _nav_links(response.text) == DEMO_NAV
    # No session to end, and no auth-gated feature link anywhere on the page.
    for href in ('href="/auth/logout"', 'href="/overview"', 'href="/waiver"',
                 'href="/projection"'):
        assert href not in response.text


# AC1 — every demo nav feature link stays inside demo mode (200, not 302 to login)

@pytest.mark.parametrize("source", DEMO_PAGES)
def test_demo_nav_links_stay_in_demo_mode(ctx, source):
    _, client = ctx
    links = [href for href, _ in _nav_links(client.get(source).text)]

    for href in links:
        if href == "/auth/login":
            continue  # the deliberate exit affordance, not a demo page
        target = client.get(href)
        assert target.status_code == 200, f"{source} -> {href} returned {target.status_code}"


# Guards the `**shell_context(...)` ordering trap: spreading the helper after an
# explicit selected_league_name key silently blanks the header label.

@pytest.mark.parametrize("path", DEMO_PAGES)
def test_demo_pages_header_keeps_demo_league_label(ctx, path):
    _, client = ctx
    response = client.get(path)

    assert "Demo League" in _header_left(response.text)


# AC3 — authenticated feature pages are unchanged

@pytest.mark.parametrize("path", ["/overview", "/waiver", "/projection"])
def test_authenticated_feature_pages_render_authenticated_nav(ctx, path):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    response = _authenticated_feature_get(client, path)

    assert response.status_code == 200
    assert _nav_links(response.text) == AUTHENTICATED_NAV
    assert "Alpha League" in _header_left(response.text)


# ---------------------------------------------------------------------------
# Ticket 040 — the five `web/routes/overview.py` branches 036b left unguarded.
#
# Each of these fails if its branch's `**shell_context(...)` spread is dropped,
# verified by mutation probe. The empty-state branches are the ones most likely
# to lose the spread in a future edit and the ones that fail most quietly.
# ---------------------------------------------------------------------------

# Branch 1 — authenticated /overview/head-to-head, populated (>= 2 teams).
# The helper's df already has two teams (Alpha, Beta), so `len(teams) < 2` is
# false and this lands on the populated branch.

def test_authenticated_head_to_head_renders_authenticated_nav(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    response = _authenticated_feature_get(client, "/overview/head-to-head")

    assert response.status_code == 200
    assert _nav_links(response.text) == AUTHENTICATED_NAV
    assert "Alpha League" in _header_left(response.text)


# Branches 2 and 3 — the authenticated empty states: `df is None or df.empty`
# on /overview, and `len(teams) < 2` on /overview/head-to-head. Both handlers
# bind `get_matchups` at import time, so the target is the route module.

@pytest.mark.parametrize("path", ["/overview", "/overview/head-to-head"])
def test_authenticated_empty_state_renders_authenticated_nav(ctx, path):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.overview.make_session", return_value=MagicMock()),
        patch("web.routes.overview.get_user_hockey_leagues", return_value=[LEAGUE_A]),
        patch("web.routes.overview.get_matchups", return_value=None),
    ):
        response = client.get(path, cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert _nav_links(response.text) == AUTHENTICATED_NAV
    assert "Alpha League" in _header_left(response.text)


# Branches 4 and 5 — the demo empty states: `df is None or df.empty` on
# /demo/overview, and `len(teams) < 2` on /demo/overview/head-to-head.
# The demo handlers import `data.demo` lazily *inside the function body*, so
# the patch target inverts: `data.demo.get_matchups`, not the route module
# (docs/LEARNINGS.md "Tests must patch the importing module's namespace",
# exception clause). Patching the route module here does nothing and the test
# would silently run against the populated branch instead.

@pytest.mark.parametrize("path", ["/demo/overview", "/demo/overview/head-to-head"])
def test_demo_empty_state_renders_demo_nav(ctx, path):
    _, client = ctx

    with patch("data.demo.get_matchups", return_value=None):
        response = client.get(path)

    assert response.status_code == 200
    assert _nav_links(response.text) == DEMO_NAV
    assert "Demo League" in _header_left(response.text)


# AC4 — the demo nav and the authenticated nav differ

def test_demo_nav_differs_from_authenticated_nav(ctx):
    conn, client = ctx

    demo_body = client.get("/demo/overview").text

    _insert_session(conn, league_key="419.l.11111")
    authenticated_body = _authenticated_feature_get(client, "/overview").text

    assert 'href="/demo/waiver"' in demo_body
    assert 'href="/waiver"' not in demo_body
    assert 'href="/auth/logout"' not in demo_body
    assert "Log in with Yahoo" in demo_body

    assert 'href="/waiver"' in authenticated_body
    assert 'href="/demo/waiver"' not in authenticated_body
    assert 'href="/auth/logout"' in authenticated_body


# ---------------------------------------------------------------------------
# Ticket 042 — the two exception handlers in web/main.py.
#
# They receive only the Request and get no dependency injection, so they cannot
# resolve a user. Instead of guessing they spread `unknown_auth_shell_context()`
# and base.html renders the header brand link only (DECISIONS.md 2026-07-25
# "Nav shell: render sites that cannot resolve a user declare the state unknown
# and render nav-free; exception handlers never derive auth").
# ---------------------------------------------------------------------------

ERROR_PATHS = [("/test/nav-http-error", 502), ("/test/nav-unhandled", 500)]


@pytest.fixture()
def error_client():
    """Client for the two exception handlers, with a real session row seeded.

    Mirrors the fixture in tests/test_error_handling.py (its own route paths, so
    the two modules never register the same path on the shared `app`): a handler
    only fires for a route that raises, and the 500 handler only fires when
    `raise_server_exceptions=False`.
    """

    @app.get("/test/nav-http-error")
    def _raise_http_error():
        raise requests.HTTPError("Yahoo said no")

    @app.get("/test/nav-unhandled")
    def _raise_unhandled():
        raise Exception("boom")

    conn = _make_db()
    _insert_session(conn, league_key="419.l.11111")

    def override_db():
        yield conn

    app.dependency_overrides[db_dep] = override_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
    conn.close()


# The `auth_state_unknown` branch wins over both flags it precedes in base.html.

def test_base_html_auth_state_unknown_renders_nav_free():
    for context in (
        {"auth_state_unknown": True},
        {"auth_state_unknown": True, "demo_mode": True},
        {"auth_state_unknown": True, "is_authenticated": True},
        {"auth_state_unknown": True, "is_authenticated": False},
    ):
        html = templates.env.get_template("base.html").render(**context)
        assert _nav_links(html) == [], context


def test_unknown_auth_shell_context_takes_no_user_and_sets_one_key():
    assert unknown_auth_shell_context() == {"auth_state_unknown": True}


# AC1/AC2 — both error pages render a nav with no links at all.

@pytest.mark.parametrize("path,status", ERROR_PATHS)
def test_error_pages_render_nav_free(error_client, path, status):
    response = error_client.get(path)

    assert response.status_code == status
    assert _nav_links(response.text) == []
    for href in ("/overview", "/waiver", "/projection", "/auth/logout",
                 "/auth/login"):
        assert f'href="{href}"' not in response.text


# AC2 — the handlers derive nothing: a valid session cookie changes no byte.

@pytest.mark.parametrize("path,status", ERROR_PATHS)
def test_error_pages_identical_with_and_without_session_cookie(
    error_client, path, status
):
    anonymous = error_client.get(path)
    authenticated = error_client.get(path, cookies={"session_id": "sid-test"})

    assert anonymous.status_code == authenticated.status_code == status
    assert authenticated.text == anonymous.text


# AC3 — shared <head>, brand link in the header, "Back to home" in the body.

@pytest.mark.parametrize("path,status", ERROR_PATHS)
def test_error_pages_keep_brand_link_and_shared_head(error_client, path, status):
    response = error_client.get(path)

    assert "<title>Error</title>" in response.text
    assert "https://cdn.tailwindcss.com" in response.text
    header_left = _header_left(response.text)
    assert '<a href="/"' in header_left
    assert "Fantasy Hockey" in header_left
    # No league label: the handlers pass no selected_league_name.
    assert "&middot;" not in header_left


@pytest.mark.parametrize("path,status", ERROR_PATHS)
def test_error_pages_offer_back_to_home_in_the_body(error_client, path, status):
    response = error_client.get(path)

    body = response.text.split("</header>", 1)[1]
    assert '<a href="/"' in body
    assert "Back to home" in body
