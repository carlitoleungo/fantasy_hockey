"""
Shared test harness: an in-memory session DB with the real schema.

Route tests inject the connection with `app.dependency_overrides[db_dep]` so
the test body and the route handlers share one database.
"""

from __future__ import annotations

import sqlite3
import time

from db.connection import init_db


def make_db() -> sqlite3.Connection:
    """Open an in-memory SQLite DB with db/schema.sql applied (Row factory on)."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def insert_session(
    conn: sqlite3.Connection,
    session_id: str = "sid-test",
    league_key: str | None = None,
    *,
    access_token: str = "acc",
    refresh_token: str = "ref",
    expires_at: float | None = None,
) -> None:
    """Insert a user_sessions row whose token is valid for an hour by default."""
    now = time.time()
    conn.execute(
        "INSERT INTO user_sessions"
        " (session_id, access_token, refresh_token, expires_at, created_at, league_key)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            session_id,
            access_token,
            refresh_token,
            now + 3600 if expires_at is None else expires_at,
            now,
            league_key,
        ),
    )
    conn.commit()
