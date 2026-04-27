"""Database layer for clipboard history storage using SQLite."""

import contextlib
import hashlib
import os
import sqlite3
from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path


class ClipboardDB:
    """Repository for clipboard history database operations."""

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

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript(self.SCHEMA)

    @contextlib.contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a configured database connection that automatically closes."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            with conn:
                yield conn
        finally:
            if conn:
                conn.close()

    @staticmethod
    def _hash(content: str) -> str:
        """Generate a SHA-256 hash for content deduplication."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def add_entry(self, content: str) -> bool:
        """
        Add a new clipboard entry to the database.

        Returns True if the entry was added, False if it was a duplicate
        of the most recent entry. If the entry exists but is not the most
        recent, it will be moved to the top of the history.
        """
        content = content.strip()
        if not content:
            return False

        content_hash = self._hash(content)

        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT content_hash FROM clipboard_history ORDER BY id DESC LIMIT 1"
            )
            last = cursor.fetchone()
            if last and last["content_hash"] == content_hash:
                return False

            conn.execute("DELETE FROM clipboard_history WHERE content_hash = ?", (content_hash,))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO clipboard_history 
                (content, content_hash, char_count, word_count, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (content, content_hash, len(content), len(content.split()), now),
            )
            conn.commit()
            return True

    def get_entries(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """Get the most recent clipboard entries."""
        with self.get_connection() as conn:
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

    def get_latest_id(self) -> int:
        """Get the ID of the most recent entry. Returns 0 if empty."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT MAX(id) FROM clipboard_history")
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else 0

    def search_entries(self, query: str, limit: int = 50) -> list[dict]:
        """Search clipboard history for entries containing the query string."""
        with self.get_connection() as conn:
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

    def get_stats(self) -> dict:
        """Get statistics about clipboard history."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            stats = {}

            cursor = conn.execute("SELECT COUNT(*) as count FROM clipboard_history")
            stats["total_entries"] = cursor.fetchone()["count"]

            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM clipboard_history WHERE date(created_at) = ?",
                (today,),
            )
            stats["today_entries"] = cursor.fetchone()["count"]

            cursor = conn.execute(
                "SELECT AVG(char_count) as avg_chars,"
                " AVG(word_count) as avg_words FROM clipboard_history"
            )
            row = cursor.fetchone()
            stats["avg_chars"] = round(row["avg_chars"] or 0, 1)
            stats["avg_words"] = round(row["avg_words"] or 0, 1)

            cursor = conn.execute("SELECT MAX(char_count) as max_chars FROM clipboard_history")
            stats["longest_entry"] = cursor.fetchone()["max_chars"] or 0

            cursor = conn.execute("SELECT MIN(char_count) as min_chars FROM clipboard_history")
            stats["shortest_entry"] = cursor.fetchone()["min_chars"] or 0

            cursor = conn.execute("SELECT SUM(char_count) as total_chars FROM clipboard_history")
            stats["total_chars"] = cursor.fetchone()["total_chars"] or 0

            cursor = conn.execute(
                "SELECT MIN(created_at) as first, MAX(created_at) as last FROM clipboard_history"
            )
            row = cursor.fetchone()
            stats["first_entry"] = row["first"]
            stats["last_entry"] = row["last"]

            if self.db_path.exists():
                size_bytes = self.db_path.stat().st_size
                if size_bytes < 1024:
                    stats["db_size"] = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    stats["db_size"] = f"{size_bytes / 1024:.1f} KB"
                else:
                    stats["db_size"] = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                stats["db_size"] = "N/A"

            return stats

    def delete_entry(self, entry_id: int) -> bool:
        """Delete a single clipboard entry by its ID. Returns True if deleted."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM clipboard_history WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_all(self) -> int:
        """Delete all clipboard history entries. Returns the number of deleted rows."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM clipboard_history")
            count = cursor.fetchone()["count"]
            conn.execute("DELETE FROM clipboard_history")
            conn.commit()
            return count

    def get_count(self) -> int:
        """Get the total number of entries in the database."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM clipboard_history")
            return cursor.fetchone()["count"]

    def enforce_max_entries(self, max_entries: int) -> int:
        """Delete the oldest entries to keep the database within the max entry limit."""
        with self.get_connection() as conn:
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

    def prune_older_than(self, days: int) -> int:
        """Delete entries older than the specified number of days."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
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


class PidManager:
    """Manages the PID file for daemon execution."""

    def __init__(self, pid_path: Path):
        self.pid_path = pid_path

    def write_pid(self) -> None:
        """Write the current process ID to the PID file."""
        self.pid_path.parent.mkdir(parents=True, exist_ok=True)
        self.pid_path.write_text(str(os.getpid()))

    def read_pid(self) -> int | None:
        """Read the daemon PID from the PID file. Returns None if not found or invalid."""
        if not self.pid_path.exists():
            return None
        try:
            pid = int(self.pid_path.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            self.remove_pid()
            return None

    def remove_pid(self) -> None:
        """Remove the PID file."""
        if self.pid_path.exists():
            self.pid_path.unlink()


# Default singleton instances for legacy CLI mapping
DATA_DIR = Path.home() / ".yankit"
db = ClipboardDB(DATA_DIR / "history.db")
pid_manager = PidManager(DATA_DIR / "yankit.pid")
