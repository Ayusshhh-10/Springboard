import os
import sqlite3

DATABASE_PATH = "database/exam_monitoring.db"

def get_db_connection():
    print("USING DATABASE:", os.path.abspath(DATABASE_PATH))
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()

    with open("database/schema.sql", "r") as file:
        connection.executescript(file.read())

    connection.commit()
    connection.close()


def get_admin_dashboard_stats():
    connection = get_db_connection()
    cursor = connection.cursor()

    total_candidates = cursor.execute(
        "SELECT COUNT(*) FROM candidates"
    ).fetchone()[0]

    active_sessions = cursor.execute(
        """
        SELECT COUNT(*)
        FROM exam_sessions
        WHERE status='Active'
        """
    ).fetchone()[0]

    completed_sessions = cursor.execute(
        """
        SELECT COUNT(*)
        FROM exam_sessions
        WHERE status='Ended'
        """
    ).fetchone()[0]

    average_integrity = cursor.execute(
        """
        SELECT AVG(integrity_score)
        FROM exam_sessions
        WHERE integrity_score IS NOT NULL
        """
    ).fetchone()[0]

    total_events = cursor.execute(
        "SELECT COUNT(*) FROM event_logs"
    ).fetchone()[0]

    connection.close()

    return {
        "total_candidates": total_candidates,
        "active_sessions": active_sessions,
        "completed_sessions": completed_sessions,
        "average_integrity": round(average_integrity or 0, 2),
        "total_events": total_events
    }



def get_filtered_events(candidate_id="", event_type="", event_date=""):

    connection = get_db_connection()
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    query = """
        SELECT *
        FROM event_logs
        WHERE 1=1
    """

    params = []

    if candidate_id:
        query += " AND candidate_id = ?"
        params.append(candidate_id)

    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)

    if event_date:
        query += " AND DATE(timestamp) = ?"
        params.append(event_date)

    query += " ORDER BY timestamp DESC"

    events = cursor.execute(query, params).fetchall()

    connection.close()

    return events


def get_integrity_analytics():

    connection = get_db_connection()
    cursor = connection.cursor()

    face_absence = cursor.execute("""
        SELECT COUNT(*)
        FROM event_logs
        WHERE event_type='Face Not Detected'
    """).fetchone()[0]

    browser_focus = cursor.execute("""
        SELECT COUNT(*)
        FROM event_logs
        WHERE event_type='Browser Focus Lost'
    """).fetchone()[0]

    highest_score = cursor.execute("""
        SELECT MAX(integrity_score)
        FROM exam_sessions
    """).fetchone()[0]

    lowest_score = cursor.execute("""
        SELECT MIN(integrity_score)
        FROM exam_sessions
    """).fetchone()[0]

    average_score = cursor.execute("""
        SELECT AVG(integrity_score)
        FROM exam_sessions
    """).fetchone()[0]

    connection.close()

    return {
        "face_absence": face_absence,
        "browser_focus": browser_focus,
        "highest_score": highest_score or 0,
        "lowest_score": lowest_score or 0,
        "average_score": round(average_score or 0, 2)
    }