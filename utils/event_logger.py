import sqlite3
from datetime import datetime

DB_PATH = "database/exam_monitoring.db"


def log_event(candidate_id, event_type, remarks, proof_image=None, penalty=0):
    """
    Stores all monitoring events in the common event_logs table.
    """
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("Saving proof image:", proof_image)

    cursor.execute(
        """
        INSERT INTO event_logs
        (candidate_id, event_type, timestamp, remarks, proof_image, penalty)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            candidate_id,
            event_type,
            timestamp,
            remarks,
            proof_image,
            penalty
        )
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
def get_event_summary(candidate_id):
    """
    Returns all suspicious events for the latest exam session.
    """

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
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
        return []

    start_time = session["start_time"]

    events = cursor.execute(
        """
        SELECT
            event_type,
            timestamp,
            proof_image,
            penalty
        FROM event_logs
        WHERE candidate_id = ?
        AND timestamp >= ?
        ORDER BY timestamp ASC
        """,
        (candidate_id, start_time)
    ).fetchall()

    from utils.integrity_score import EVENT_WEIGHTS

    summary = []
    running_score = 100

    for event in events:
        penalty_val = event["penalty"] if event["penalty"] is not None else 0
        if penalty_val != 0:
            deduction = abs(penalty_val)
        else:
            deduction = EVENT_WEIGHTS.get(event["event_type"], 0)
        
        running_score = max(0, running_score - deduction)

        summary.append({
            "event_type": event["event_type"],
            "timestamp": event["timestamp"],
            "proof_image": event["proof_image"],
            "penalty": penalty_val,
            "deduction": deduction,
            "running_score": running_score
        })

    connection.close()

    return summary