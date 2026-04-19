"""
SQLite connection factory for the Fantasy Hockey web app.

Opens the database in WAL mode for concurrent reads and sets row_factory
so query results are accessible by column name.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Generator

_DEFAULT_DB_PATH = "./app.db"
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def db_dep() -> Generator:
    """FastAPI dependency: open a DB connection and close it after the response."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def get_db(path: str | None = None) -> sqlite3.Connection:
    """
    Open and return a SQLite connection in WAL mode.

    path defaults to the DB_PATH env var, falling back to ./app.db (repo root).
    Set DB_PATH=/data/app.db in production (Fly.io volume mount).
    """
    resolved = path or os.environ.get("DB_PATH", _DEFAULT_DB_PATH)
    Path(resolved).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Apply schema.sql to conn. Safe to call on every startup (CREATE TABLE IF NOT EXISTS)."""
    conn.executescript(_SCHEMA_PATH.read_text())
    conn.commit()
