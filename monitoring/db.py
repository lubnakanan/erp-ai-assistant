"""
Lightweight SQLite logging for ERP Assistant.

Every question/answer pair gets logged (timestamp, module filter,
response time, source count). Feedback (👍/👎) can be attached to a
logged interaction afterwards. The Monitoring tab in the Streamlit app
reads from this same database to build its charts.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.db"


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            module_filter TEXT,
            response_time_sec REAL,
            num_sources INTEGER,
            feedback TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def log_interaction(question: str, answer: str, module_filter: str | None, response_time_sec: float, num_sources: int) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO interactions
           (timestamp, question, answer, module_filter, response_time_sec, num_sources, feedback)
           VALUES (?, ?, ?, ?, ?, ?, NULL)""",
        (
            datetime.now(timezone.utc).isoformat(),
            question,
            answer,
            module_filter or "All modules",
            response_time_sec,
            num_sources,
        ),
    )
    conn.commit()
    log_id = cur.lastrowid
    conn.close()
    return log_id


def update_feedback(log_id: int, feedback: str) -> None:
    """feedback is 'up' or 'down'."""
    conn = _get_conn()
    conn.execute("UPDATE interactions SET feedback = ? WHERE id = ?", (feedback, log_id))
    conn.commit()
    conn.close()


def get_all_logs() -> list[dict]:
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM interactions ORDER BY timestamp ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print(f"Initialized DB at {DB_PATH}")
    print(f"Current row count: {len(get_all_logs())}")
