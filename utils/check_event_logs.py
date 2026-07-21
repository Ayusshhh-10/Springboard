import sqlite3

DB_PATH = "database/exam_monitoring.db"


def check_face_absence_events():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    print("\nFace Not Detected Count Candidate-wise:")
    count_rows = cursor.execute(
        """
        SELECT candidate_id, COUNT(*) 
        FROM event_logs 
        WHERE event_type = ?
        GROUP BY candidate_id
        """,
        ("Face Not Detected",)
    ).fetchall()

    if count_rows:
        for candidate_id, count in count_rows:
            print(f"Candidate {candidate_id} left the video {count} time(s).")
    else:
        print("No Face Not Detected events found.")

    print("\nLatest Face Absence Event Details:")
    event_rows = cursor.execute(
        """
        SELECT event_id, candidate_id, event_type, timestamp, remarks
        FROM event_logs
        WHERE event_type = ?
        ORDER BY event_id DESC
        LIMIT 10
        """,
        ("Face Not Detected",)
    ).fetchall()

    for row in event_rows:
        print(row)

    connection.close()


if __name__ == "__main__":
    check_face_absence_events()