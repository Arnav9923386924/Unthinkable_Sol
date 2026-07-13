import sqlite3
import json
from contextlib import contextmanager
from app.config import settings


def get_db_path() -> str:
    return settings.database_path


def init_db():
    """Create the meetings table if it doesn't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                transcript TEXT NOT NULL,
                summary TEXT DEFAULT '',
                decisions TEXT DEFAULT '[]',
                action_items TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


@contextmanager
def get_connection():
    """Context manager for SQLite connections."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save_meeting(meeting_id: str, filename: str, transcript: str,
                 summary: str, decisions: list, action_items: list):
    """Insert a new meeting record into the database."""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO meetings (id, filename, transcript, summary, decisions, action_items)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (meeting_id, filename, transcript, summary,
             json.dumps(decisions), json.dumps(action_items))
        )
        conn.commit()


def get_meeting(meeting_id: str) -> dict | None:
    """Retrieve a single meeting by ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)


def get_all_meetings() -> list[dict]:
    """Retrieve all meetings, most recent first."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM meetings ORDER BY created_at DESC").fetchall()
        return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a SQLite row to a dictionary, parsing JSON fields."""
    return {
        "id": row["id"],
        "filename": row["filename"],
        "transcript": row["transcript"],
        "summary": row["summary"],
        "decisions": json.loads(row["decisions"]),
        "action_items": json.loads(row["action_items"]),
        "created_at": row["created_at"],
    }
