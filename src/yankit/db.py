"""Database layer for clipboard history storage using SQLite."""

import hashlib
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Default database location
DATA_DIR = Path.home() / ".yankit"
DB_PATH = DATA_DIR / "history.db"
PID_FILE = DATA_DIR / "yankit.pid"

SCHEMA = """
CREATE TABLE IF NOT EXISTS clipboard_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_content_hash ON clipboard_history(content_hash);
CREATE INDEX IF NOT EXISTS idx_created_at ON clipboard_history(created_at);
"""


def _hash(content: str) -> str:
    """Generate a SHA-256 hash for content deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the data directory and schema if needed."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def add_entry(content: str) -> bool:
    """
    Add a new clipboard entry to the database.

    Returns True if the entry was added, False if it was a duplicate
    of the most recent entry.
    """
    content = content.strip()
    if not content:
        return False

    content_hash = _hash(content)

    conn = get_connection()
    try:
        # Check if the last entry has the same hash (avoid consecutive duplicates)
        cursor = conn.execute("SELECT content_hash FROM clipboard_history ORDER BY id DESC LIMIT 1")
        last = cursor.fetchone()
        if last and last["content_hash"] == content_hash:
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            INSERT INTO clipboard_history (content, content_hash, char_count, word_count, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (content, content_hash, len(content), len(content.split()), now),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_entries(limit: int = 20, offset: int = 0) -> list[dict]:
    """Get the most recent clipboard entries."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, content, char_count, word_count, created_at
            FROM clipboard_history
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_today_entries() -> list[dict]:
    """Get all clipboard entries from today."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, content, char_count, word_count, created_at
            FROM clipboard_history
            WHERE date(created_at) = ?
            ORDER BY id DESC
            """,
            (today,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def search_entries(query: str, limit: int = 50) -> list[dict]:
    """Search clipboard history for entries containing the query string."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, content, char_count, word_count, created_at
            FROM clipboard_history
            WHERE content LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_entry_by_id(entry_id: int) -> dict | None:
    """Get a single clipboard entry by its ID."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, content, char_count, word_count, created_at
            FROM clipboard_history
            WHERE id = ?
            """,
            (entry_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_stats() -> dict:
    """Get statistics about clipboard history."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        stats = {}

        # Total entries
        cursor = conn.execute("SELECT COUNT(*) as count FROM clipboard_history")
        stats["total_entries"] = cursor.fetchone()["count"]

        # Today's entries
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM clipboard_history WHERE date(created_at) = ?",
            (today,),
        )
        stats["today_entries"] = cursor.fetchone()["count"]

        # Average character count
        cursor = conn.execute(
            "SELECT AVG(char_count) as avg_chars,"
            " AVG(word_count) as avg_words FROM clipboard_history"
        )
        row = cursor.fetchone()
        stats["avg_chars"] = round(row["avg_chars"] or 0, 1)
        stats["avg_words"] = round(row["avg_words"] or 0, 1)

        # Longest entry
        cursor = conn.execute("SELECT MAX(char_count) as max_chars FROM clipboard_history")
        stats["longest_entry"] = cursor.fetchone()["max_chars"] or 0

        # Shortest entry
        cursor = conn.execute("SELECT MIN(char_count) as min_chars FROM clipboard_history")
        stats["shortest_entry"] = cursor.fetchone()["min_chars"] or 0

        # Total characters copied
        cursor = conn.execute("SELECT SUM(char_count) as total_chars FROM clipboard_history")
        stats["total_chars"] = cursor.fetchone()["total_chars"] or 0

        # First and last entry dates
        cursor = conn.execute(
            "SELECT MIN(created_at) as first, MAX(created_at) as last FROM clipboard_history"
        )
        row = cursor.fetchone()
        stats["first_entry"] = row["first"]
        stats["last_entry"] = row["last"]

        # Database file size
        if DB_PATH.exists():
            size_bytes = DB_PATH.stat().st_size
            if size_bytes < 1024:
                stats["db_size"] = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                stats["db_size"] = f"{size_bytes / 1024:.1f} KB"
            else:
                stats["db_size"] = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            stats["db_size"] = "N/A"

        return stats
    finally:
        conn.close()


def delete_all() -> int:
    """Delete all clipboard history entries. Returns the number of deleted rows."""
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) as count FROM clipboard_history")
        count = cursor.fetchone()["count"]
        conn.execute("DELETE FROM clipboard_history")
        conn.commit()
        return count
    finally:
        conn.close()


def enforce_max_entries(max_entries: int) -> int:
    """
    Delete the oldest entries to keep the database within the max entry limit.

    Returns the number of deleted rows.
    """
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) as count FROM clipboard_history")
        count = cursor.fetchone()["count"]

        if count <= max_entries:
            return 0

        to_delete = count - max_entries
        conn.execute(
            """
            DELETE FROM clipboard_history
            WHERE id IN (
                SELECT id FROM clipboard_history
                ORDER BY id ASC
                LIMIT ?
            )
            """,
            (to_delete,),
        )
        conn.commit()
        return to_delete
    finally:
        conn.close()


def prune_older_than(days: int) -> int:
    """
    Delete entries older than the specified number of days.

    Returns the number of deleted rows.
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM clipboard_history WHERE created_at < ?",
            (cutoff,),
        )
        count = cursor.fetchone()["count"]

        conn.execute(
            "DELETE FROM clipboard_history WHERE created_at < ?",
            (cutoff,),
        )
        conn.commit()
        return count
    finally:
        conn.close()


# --- PID file management for daemon mode ---


def write_pid() -> None:
    """Write the current process ID to the PID file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def read_pid() -> int | None:
    """Read the daemon PID from the PID file. Returns None if not found."""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process is actually running
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        # PID file exists but process is not running — stale PID
        remove_pid()
        return None


def remove_pid() -> None:
    """Remove the PID file."""
    if PID_FILE.exists():
        PID_FILE.unlink()
