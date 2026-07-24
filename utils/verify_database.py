import sqlite3

DB_PATH = "database/exam_monitoring.db"


def verify_database():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    print("\n========== Candidate Details ==========")

    candidates = cursor.execute(
        """
        SELECT candidate_id, name, email, photo_path
        FROM candidates
        ORDER BY candidate_id
        """
    ).fetchall()

    if candidates:
        for candidate in candidates:
            print(candidate)
    else:
        print("No candidate records found.")

    print("\n========== Exam Sessions ==========")

    sessions = cursor.execute(
        """
        SELECT session_id, candidate_id, start_time, end_time, status
        FROM exam_sessions
        ORDER BY session_id DESC
        LIMIT 10
        """
    ).fetchall()

    if sessions:
        for session in sessions:
            print(session)
    else:
        print("No exam session records found.")

    print("\n========== Event Counts ==========")

    event_counts = cursor.execute(
        """
        SELECT candidate_id, event_type, COUNT(*)
        FROM event_logs
        GROUP BY candidate_id, event_type
        ORDER BY candidate_id, event_type
        """
    ).fetchall()

    if event_counts:
        for row in event_counts:
            print(f"Candidate ID: {row[0]} | Event Type: {row[1]} | Count: {row[2]}")
    else:
        print("No event logs found.")

    print("\n========== Latest Event Logs ==========")

    events = cursor.execute(
        """
        SELECT event_id, candidate_id, event_type, timestamp, remarks
        FROM event_logs
        ORDER BY event_id DESC
        LIMIT 15
        """
    ).fetchall()

    if events:
        for event in events:
            print(event)
    else:
        print("No event logs found.")

    connection.close()


if __name__ == "__main__":
    verify_database()