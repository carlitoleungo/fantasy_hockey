"""
QA-targeted tests for ticket 036a — supplementary to the engineer's TC17-TC19.

Covers gaps found during QA:
  - TC18 asserts nav ordering over the whole response body; these scope the
    assertions to the <nav> element itself.
  - TC18's `"Alpha League" in body` does not discriminate (the league list in
    the content area contains the same string). QA verified the existing TC9
    header-scoped assertion does catch a dropped `selected_league_name`; this
    file adds the same guard alongside the nav-order check so the AC2 pair
    lives in one test.
  - The `base.html` default path (neither `is_authenticated` nor `demo_mode`
    in context) is asserted directly against the template, independent of any
    route, since that default is the DECISIONS.md 2026-07-03 safety constraint
    that keeps every not-yet-migrated page rendering as before.
  - The demo branch of the nav shipped in 036a but is dormant (no route sets
    demo_mode until 036b), so it is exercised by direct template render.

Ticket 036b appended the demo/authenticated feature-page nav assertions at the
bottom of this file, reusing the <nav>- and <header>-scoped helpers above, and
removed 036a's `test_demo_pages_still_render_default_authenticated_nav`
tripwire (the before-state 036b flips).
"""

from __future__ import annotations

import re
import sqlite3
import time
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fastapi.testclient import TestClient

from db.connection import db_dep
from web.main import app
from web.routes.common import shell_context
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
        # AC3 safety constraint: neither flag present -> authenticated nav.
        ({}, AUTHENTICATED_NAV),
        # A route passing only demo=False must also fall through to authenticated.
        ({"demo_mode": False}, AUTHENTICATED_NAV),
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


@pytest.mark.parametrize("path", ["/overview", "/waiver", "/projection"])
def test_authenticated_nav_links_return_200(ctx, path):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    for href in ("/overview", "/waiver", "/projection"):
        assert _authenticated_feature_get(client, href).status_code == 200


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
