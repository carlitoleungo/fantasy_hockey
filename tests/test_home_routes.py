"""
Tests for GET / and POST /leagues/select (tickets 011, 014).

Uses an in-memory SQLite DB injected via dependency override on db_dep.
get_user_hockey_leagues and make_session are mocked so no live Yahoo API
calls are made.
"""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient  # noqa: E402

from db.connection import db_dep  # noqa: E402
from web.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


LEAGUE_2025_A = {
    "league_key": "419.l.11111",
    "league_name": "Alpha League",
    "season": "2025",
}
LEAGUE_2025_B = {
    "league_key": "419.l.22222",
    "league_name": "Beta League",
    "season": "2025",
}
LEAGUE_2024_OLD = {
    "league_key": "411.l.99999",
    "league_name": "Old League",
    "season": "2024",
}


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


# ---------------------------------------------------------------------------
# TC1 — GET / with valid session: returns 200 and filters to current season
# ---------------------------------------------------------------------------

def test_home_filters_to_current_season(ctx):
    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B, LEAGUE_2024_OLD],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert "Alpha League" in body
    assert "Beta League" in body
    assert "Old League" not in body
    assert "2025" in body


# ---------------------------------------------------------------------------
# TC2 — GET / with empty league list: returns 200 with empty-state message
# ---------------------------------------------------------------------------

def test_home_empty_leagues(ctx):
    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch("web.routes.home.get_user_hockey_leagues", return_value=[]),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert "No active NHL leagues found for your account." in response.text


# ---------------------------------------------------------------------------
# TC3 — GET / with a pre-selected league: highlight shown for that league
# ---------------------------------------------------------------------------

def test_home_shows_selected_league_indicator(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    # The template emits "✓ Selected" (HTML entity ✓) next to the active league
    assert "Selected" in body
    # Confirm the selected league key appears in a highlighted context
    assert "419.l.11111" in body


# ---------------------------------------------------------------------------
# TC4 — POST /leagues/select: updates DB row and redirects 302 to /
# ---------------------------------------------------------------------------

def test_select_league_updates_db_and_redirects(ctx):
    conn, client = ctx
    _insert_session(conn)

    response = client.post(
        "/leagues/select",
        data={"league_key": "419.l.11111"},
        cookies={"session_id": "sid-test"},
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/"

    row = conn.execute(
        "SELECT league_key FROM user_sessions WHERE session_id = 'sid-test'"
    ).fetchone()
    assert row["league_key"] == "419.l.11111"


# ---------------------------------------------------------------------------
# TC5 — GET / with no cookie: 200 with login CTA (not a redirect) (023)
# ---------------------------------------------------------------------------

def test_home_no_cookie_returns_login_cta(ctx):
    _, client = ctx
    response = client.get("/")
    assert response.status_code == 200
    assert 'href="/auth/login"' in response.text
    assert "Log in with Yahoo" in response.text


# ---------------------------------------------------------------------------
# TC6 — POST /leagues/select with no cookie: 302 to /auth/login
# ---------------------------------------------------------------------------

def test_select_league_no_cookie_redirects_to_login(ctx):
    _, client = ctx
    response = client.post("/leagues/select", data={"league_key": "419.l.11111"})
    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"


# ---------------------------------------------------------------------------
# TC7 — GET / when Yahoo API raises HTTPError: 502 error page (not 500)
# ---------------------------------------------------------------------------

def test_home_yahoo_api_error_returns_502(ctx):
    import requests as req_lib

    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            side_effect=req_lib.HTTPError("Yahoo API error"),
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 502


# ---------------------------------------------------------------------------
# TC8 — GET / renders nav header with app-name anchor and logout link (014)
# ---------------------------------------------------------------------------

def test_home_renders_nav_header(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert 'href="/"' in body
    assert "Fantasy Hockey" in body
    assert '<a href="/auth/logout"' in body


# ---------------------------------------------------------------------------
# TC9 — GET / with selected league renders league name in header (014)
# ---------------------------------------------------------------------------

def test_home_header_shows_selected_league_name(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    # Isolate the header element so we confirm the league name appears there,
    # not merely somewhere in the page body.
    header_start = body.index("<header")
    header_end = body.index("</header>") + len("</header>")
    header_html = body[header_start:header_end]
    assert "Alpha League" in header_html


# ---------------------------------------------------------------------------
# TC10 — GET / with no selected league renders header without league label (014)
# ---------------------------------------------------------------------------

def test_home_header_no_league_label_when_unselected(ctx):
    conn, client = ctx
    _insert_session(conn)  # no league_key

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert 'href="/"' in body
    assert "Fantasy Hockey" in body
    # No separator character should appear in the header when no league is selected
    assert "&middot;" not in body


# ---------------------------------------------------------------------------
# TC11 — GET /?logged_out=1: banner "You have been logged out." is visible (022)
# ---------------------------------------------------------------------------

def test_home_shows_logged_out_banner_when_param_present(ctx):
    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch("web.routes.home.get_user_hockey_leagues", return_value=[LEAGUE_2025_A]),
    ):
        response = client.get("/?logged_out=1", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert "You have been logged out." in response.text


# ---------------------------------------------------------------------------
# TC12 — GET /: banner is absent when query param is not present (022)
# ---------------------------------------------------------------------------

def test_home_no_banner_without_logged_out_param(ctx):
    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch("web.routes.home.get_user_hockey_leagues", return_value=[LEAGUE_2025_A]),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert "You have been logged out." not in response.text


# ---------------------------------------------------------------------------
# TC13 — GET /?logged_out=0: banner is absent for any value other than "1" (022)
# ---------------------------------------------------------------------------

def test_home_no_banner_when_logged_out_param_is_not_one(ctx):
    conn, client = ctx
    _insert_session(conn)

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch("web.routes.home.get_user_hockey_leagues", return_value=[LEAGUE_2025_A]),
    ):
        response = client.get("/?logged_out=0", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    assert "You have been logged out." not in response.text


# ---------------------------------------------------------------------------
# TC14 — GET / unauthenticated: 200 with login CTA, no league list (023)
# ---------------------------------------------------------------------------

def test_home_unauthenticated_shows_login_cta(ctx):
    _, client = ctx
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert 'href="/auth/login"' in body
    assert "Log in with Yahoo" in body
    # The authenticated heading must not appear in the page body
    assert "Fantasy Hockey Waiver Wire" in body
    assert "<h1" in body and "Your Leagues" not in body.split("</head>", 1)[1]


# ---------------------------------------------------------------------------
# TC15 — GET /?logged_out=1 unauthenticated: 200 with banner + login CTA (023)
# ---------------------------------------------------------------------------

def test_home_unauthenticated_with_logged_out_param_shows_banner(ctx):
    _, client = ctx
    response = client.get("/?logged_out=1")
    assert response.status_code == 200
    body = response.text
    assert "You have been logged out." in body
    assert 'href="/auth/login"' in body
    assert "Log in with Yahoo" in body


# ---------------------------------------------------------------------------
# TC16 — GET / authenticated: league list renders, no login CTA shown (023)
# ---------------------------------------------------------------------------

def test_home_authenticated_shows_league_list_not_cta(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    assert "Your Leagues" in body
    assert "Alpha League" in body
    assert "Beta League" in body
    # Login CTA must not appear when the user is authenticated
    assert "Log in with Yahoo" not in body


# ---------------------------------------------------------------------------
# TC17 — GET / unauthenticated: header nav has no auth-gated link (036a)
# ---------------------------------------------------------------------------

def test_home_unauthenticated_nav_has_no_auth_gated_links(ctx):
    _, client = ctx
    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    for href in ('href="/overview"', 'href="/waiver"', 'href="/projection"',
                 'href="/auth/logout"'):
        assert href not in body
    assert 'href="/auth/login"' in body
    assert "Log in with Yahoo" in body


# ---------------------------------------------------------------------------
# TC18 — GET / authenticated: full nav in roadmap order + league label (036a)
# ---------------------------------------------------------------------------

def test_home_authenticated_nav_has_feature_links_in_roadmap_order(ctx):
    conn, client = ctx
    _insert_session(conn, league_key="419.l.11111")

    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch(
            "web.routes.home.get_user_hockey_leagues",
            return_value=[LEAGUE_2025_A, LEAGUE_2025_B],
        ),
    ):
        response = client.get("/", cookies={"session_id": "sid-test"})

    assert response.status_code == 200
    body = response.text
    positions = [body.index(f'href="/{p}"') for p in ("overview", "waiver", "projection")]
    assert positions == sorted(positions)
    assert 'href="/auth/logout"' in body
    assert 'href="/auth/login"' not in body
    # selected_league_name is now threaded via shell_context on this branch
    assert "Alpha League" in body


# ---------------------------------------------------------------------------
# TC19 — logged-out home nav differs from authenticated home nav (036a AC4)
# ---------------------------------------------------------------------------

def test_home_nav_differs_between_logged_out_and_authenticated(ctx):
    conn, client = ctx

    logged_out_body = client.get("/").text

    _insert_session(conn, league_key="419.l.11111")
    with (
        patch("web.routes.home.make_session", return_value=MagicMock()),
        patch("web.routes.home.get_user_hockey_leagues", return_value=[LEAGUE_2025_A]),
    ):
        authenticated_body = client.get("/", cookies={"session_id": "sid-test"}).text

    assert 'href="/waiver"' not in logged_out_body
    assert "Log in with Yahoo" in logged_out_body
    assert 'href="/waiver"' in authenticated_body
