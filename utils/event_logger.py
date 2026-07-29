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
    Returns count of events only for the CURRENT exam session.
    """

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Get latest exam start time
    session = cursor.execute(
        """
        SELECT start_time
        FROM exam_sessions
        WHERE candidate_id = ?
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (candidate_id,)
    ).fetchone()

    if not session:
        connection.close()
        return 0

    start_time = session[0]

    row = cursor.execute(
        """
        SELECT COUNT(*)
        FROM event_logs
        WHERE candidate_id = ?
        AND event_type = ?
        AND timestamp >= ?
        """,
        (candidate_id, event_type, start_time)
    ).fetchone()

    connection.close()

    return row[0] if row else 0

def get_last_event_time(candidate_id, event_type):
    """
    Returns latest event time only for current exam session.
    """

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    session = cursor.execute(
        """
        SELECT start_time
        FROM exam_sessions
        WHERE candidate_id = ?
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (candidate_id,)
    ).fetchone()

    if not session:
        connection.close()
        return "No event found"

    start_time = session[0]

    row = cursor.execute(
        """
        SELECT timestamp
        FROM event_logs
        WHERE candidate_id = ?
        AND event_type = ?
        AND timestamp >= ?
        ORDER BY event_id DESC
        LIMIT 1
        """,
        (candidate_id, event_type, start_time)
    ).fetchone()

    connection.close()

    return row[0] if row else "No event found"