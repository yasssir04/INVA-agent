from __future__ import annotations
import os
import sqlite3
from typing import Any, Dict, List, Optional
from ..config import settings
from .logger import get_logger

logger = get_logger(__name__)


def _connect() -> sqlite3.Connection:
    db_dir = os.path.dirname(settings.sqlite_db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(settings.sqlite_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not _has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    try:
        conn = _connect()
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    document_id TEXT,
                    file_name TEXT,
                    file_path TEXT,
                    storage_uri TEXT,
                    content_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                );
                """
            )
            _ensure_column(conn, "sessions", "status", "TEXT DEFAULT 'active'")
            _ensure_column(conn, "files", "document_id", "TEXT")
            _ensure_column(conn, "files", "storage_uri", "TEXT")
            _ensure_column(conn, "files", "content_type", "TEXT")
            _ensure_column(conn, "files", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except Exception:
        logger.exception("Failed initializing SQLite")


def record_session(session_id: str, status: str = "active") -> None:
    try:
        conn = _connect()
        with conn:
            conn.execute(
                "INSERT INTO sessions(session_id, status) VALUES (?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET status=excluded.status",
                (session_id, status),
            )
    except Exception:
        logger.exception("Failed recording session")


def update_session_status(session_id: str, status: str) -> None:
    try:
        conn = _connect()
        with conn:
            conn.execute("UPDATE sessions SET status=? WHERE session_id=?", (status, session_id))
    except Exception:
        logger.exception("Failed updating session status")


def record_file(
    session_id: str,
    file_name: str,
    file_path: str,
    document_id: str = "",
    storage_uri: str = "",
    content_type: str = "",
) -> None:
    try:
        conn = _connect()
        with conn:
            conn.execute(
                "INSERT INTO files(session_id, document_id, file_name, file_path, storage_uri, content_type) "
                "VALUES (?,?,?,?,?,?)",
                (session_id, document_id, file_name, file_path, storage_uri, content_type),
            )
    except Exception:
        logger.exception("Failed recording file")


def list_session_files(session_id: str) -> List[Dict[str, Any]]:
    try:
        conn = _connect()
        rows = conn.execute(
            "SELECT session_id, document_id, file_name, file_path, storage_uri, content_type, created_at "
            "FROM files WHERE session_id=? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    except Exception:
        logger.exception("Failed listing session files")
        return []


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        conn = _connect()
        row = conn.execute(
            "SELECT session_id, status, created_at FROM sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None
    except Exception:
        logger.exception("Failed reading session")
        return None


def delete_session_records(session_id: str) -> None:
    try:
        conn = _connect()
        with conn:
            conn.execute("DELETE FROM files WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
    except Exception:
        logger.exception("Failed deleting session records")
