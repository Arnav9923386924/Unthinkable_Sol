import sqlite3
import json
from contextlib import contextmanager
from app.config import settings


def get_db_path() -> str:
    return settings.database_path


def init_db():
    """Create the meetings table if it doesn't exist, and migrate if needed."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                transcript TEXT NOT NULL,
                meeting_type TEXT DEFAULT 'general',
                summary TEXT DEFAULT '',
                decisions TEXT DEFAULT '[]',
                action_items TEXT DEFAULT '[]',
                audio_duration REAL DEFAULT 0.0,
                processing_time REAL DEFAULT 0.0,
                segments TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrate existing databases: add columns if missing
        try:
            conn.execute("ALTER TABLE meetings ADD COLUMN meeting_type TEXT DEFAULT 'general'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE meetings ADD COLUMN audio_duration REAL DEFAULT 0.0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE meetings ADD COLUMN processing_time REAL DEFAULT 0.0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE meetings ADD COLUMN segments TEXT DEFAULT '[]'")
        except Exception:
            pass
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
                 meeting_type: str, summary: str, decisions: list, action_items: list,
                 audio_duration: float = 0.0, processing_time: float = 0.0, segments: list = None):
    """Insert a new meeting record into the database."""
    if segments is None:
        segments = []
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO meetings (id, filename, transcript, meeting_type, summary, decisions, action_items, audio_duration, processing_time, segments)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (meeting_id, filename, transcript, meeting_type, summary,
             json.dumps(decisions), json.dumps(action_items), audio_duration, processing_time, json.dumps(segments))
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
        "meeting_type": row["meeting_type"] if "meeting_type" in row.keys() else "general",
        "summary": row["summary"],
        "decisions": json.loads(row["decisions"]),
        "action_items": json.loads(row["action_items"]),
        "created_at": row["created_at"],
        "audio_duration": row["audio_duration"] if "audio_duration" in row.keys() else 0.0,
        "processing_time": row["processing_time"] if "processing_time" in row.keys() else 0.0,
        "segments": json.loads(row["segments"]) if ("segments" in row.keys() and row["segments"]) else [],
    }
