"""
SQLite connection factory for the Fantasy Hockey web app.

Opens the database in WAL mode for concurrent reads and sets row_factory
so query results are accessible by column name.
"""

from __future__ import annotations

import os
import sqlite3

_DEFAULT_DB_PATH = "/data/app.db"


def get_db(path: str | None = None) -> sqlite3.Connection:
    """
    Open and return a SQLite connection in WAL mode.

    path defaults to the DB_PATH env var, falling back to /data/app.db.
    """
    resolved = path or os.environ.get("DB_PATH", _DEFAULT_DB_PATH)
    conn = sqlite3.connect(resolved, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn
