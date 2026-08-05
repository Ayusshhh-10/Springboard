import sqlite3

def calculate_integrity_score(candidate_id):
    """
    Calculates integrity score and counts using database events for the latest exam session.
    """
    connection = sqlite3.connect("database/exam_monitoring.db")
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
        return {
            "score": 100,
            "remark": "No active session",
            "face_absence": 0,
            "browser_focus": 0,
            "multiple_faces": 0,
            "total_events": 0
        }

    start_time = session[0]

    # Query all events for the current session
    events = cursor.execute(
        """
        SELECT event_type, penalty
        FROM event_logs
        WHERE candidate_id = ?
          AND timestamp >= ?
        """,
        (candidate_id, start_time)
    ).fetchall()

    connection.close()

    face_absence = 0
    browser_focus = 0
    multiple_faces = 0
    total_penalty = 0

    for event_type, penalty in events:
        if event_type == "Face Not Detected":
            face_absence += 1
            total_penalty += penalty if penalty else -2
        elif event_type == "Browser Focus Lost":
            browser_focus += 1
            total_penalty += penalty if penalty else -5
        elif event_type == "Multiple Faces Detected":
            multiple_faces += 1
            total_penalty += penalty if penalty else -10

    score = 100 + total_penalty
    if score < 0:
        score = 0

    total_events = face_absence + browser_focus + multiple_faces

    if score >= 90:
        remark = "Excellent Integrity"
    elif score >= 75:
        remark = "Good Integrity"
    elif score >= 50:
        remark = "Average Integrity"
    else:
        remark = "Poor Integrity (Manual Review Recommended)"

    return {
        "score": score,
        "remark": remark,
        "face_absence": face_absence,
        "browser_focus": browser_focus,
        "multiple_faces": multiple_faces,
        "total_events": total_events
    }