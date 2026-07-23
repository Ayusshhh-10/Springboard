import sqlite3
from datetime import datetime

DB_PATH = "database/exam_monitoring.db"


def log_event(candidate_id, event_type, remarks):
    """
    Stores all monitoring events in the common event_logs table.
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO event_logs
        (candidate_id, event_type, timestamp, remarks)
        VALUES (?, ?, ?, ?)
        """,
        (candidate_id, event_type, timestamp, remarks)
    )

    connection.commit()
    connection.close()


def get_event_count(candidate_id, event_type):
    """
    Returns count of a particular event for one candidate.
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    row = cursor.execute(
        """
        SELECT COUNT(*)
        FROM event_logs
        WHERE candidate_id = ?
        AND event_type = ?
        """,
        (candidate_id, event_type)
    ).fetchone()

    connection.close()

    return row[0] if row else 0


def get_last_event_time(candidate_id, event_type):
    """
    Returns latest timestamp of a particular event.
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    row = cursor.execute(
        """
        SELECT timestamp
        FROM event_logs
        WHERE candidate_id = ?
        AND event_type = ?
        ORDER BY event_id DESC
        LIMIT 1
        """,
        (candidate_id, event_type)
    ).fetchone()

    connection.close()

    return row[0] if row else "No event found"