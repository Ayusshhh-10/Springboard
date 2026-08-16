import sqlite3
import pandas as pd
from datetime import datetime

# Centralized event weights (deduction values)
EVENT_WEIGHTS = {
    "Face Not Detected": 2,
    "Browser Focus Lost": 5,
    "Multiple Faces Detected": 10,
}

# Centralized risk thresholds
RISK_THRESHOLD_LOW = 80
RISK_THRESHOLD_MEDIUM = 50


def calculate_integrity_score(candidate_id):
    """
    Calculates the integrity score for the latest exam session.

    Uses Pandas to:
    - Load session events into a DataFrame
    - Apply weighted event deductions
    - Calculate the total deduction
    - Normalize the integrity score to 0-100 (integer)
    - Calculate face presence ratio based on active monitoring interval (3 seconds)
    - Assign a risk label based on centralized thresholds
    """

    connection = sqlite3.connect("database/exam_monitoring.db")

    try:
        # ---------------------------------------------------------
        # 1. Get the latest exam session
        # ---------------------------------------------------------
        session = connection.execute(
            """
            SELECT session_id, start_time, end_time
            FROM exam_sessions
            WHERE candidate_id = ?
            ORDER BY session_id DESC
            LIMIT 1
            """,
            (candidate_id,)
        ).fetchone()

        if not session:
            return {
                "score": 100,
                "remark": "No active session",
                "risk_label": "Low Risk",
                "face_absence": 0,
                "browser_focus": 0,
                "multiple_faces": 0,
                "total_events": 0,
                "total_deduction": 0,
                "face_presence_ratio": 100.0,
            }

        session_id, start_time, end_time = session

        # ---------------------------------------------------------
        # 2. Load events for this session into Pandas
        # ---------------------------------------------------------
        events_df = pd.read_sql_query(
            """
            SELECT event_type, timestamp, penalty
            FROM event_logs
            WHERE candidate_id = ?
              AND timestamp >= ?
            ORDER BY timestamp ASC
            """,
            connection,
            params=(candidate_id, start_time)
        )

        # ---------------------------------------------------------
        # 3. Handle empty event DataFrame
        # ---------------------------------------------------------
        if events_df.empty:
            return {
                "score": 100,
                "remark": "Excellent Integrity",
                "risk_label": "Low Risk",
                "face_absence": 0,
                "browser_focus": 0,
                "multiple_faces": 0,
                "total_events": 0,
                "total_deduction": 0,
                "face_presence_ratio": 100.0,
            }

        # ---------------------------------------------------------
        # 4. Apply centralized event weights
        # ---------------------------------------------------------
        events_df["weight"] = events_df["event_type"].map(EVENT_WEIGHTS).fillna(0)

        # ---------------------------------------------------------
        # 5. Calculate total deduction using Pandas
        # ---------------------------------------------------------
        total_deduction = int(events_df["weight"].sum())

        # ---------------------------------------------------------
        # 6. Count individual event types
        # ---------------------------------------------------------
        face_absence = int(
            (events_df["event_type"] == "Face Not Detected").sum()
        )

        browser_focus = int(
            (events_df["event_type"] == "Browser Focus Lost").sum()
        )

        multiple_faces = int(
            (events_df["event_type"] == "Multiple Faces Detected").sum()
        )

        total_events = face_absence + browser_focus + multiple_faces

        # ---------------------------------------------------------
        # 7. Calculate normalized integrity score (always between 0 and 100)
        # ---------------------------------------------------------
        raw_score = 100 - total_deduction
        score = int(max(0, min(100, raw_score)))

        # ---------------------------------------------------------
        # 8. Calculate exam duration
        # ---------------------------------------------------------
        start = pd.to_datetime(start_time)

        if end_time:
            end = pd.to_datetime(end_time)
        else:
            # If exam is still running, use the current timestamp
            end = pd.to_datetime(datetime.now())

        exam_duration = (end - start).total_seconds()

        # Prevent division by zero or negative duration
        if exam_duration <= 0:
            exam_duration = 1.0

        # ---------------------------------------------------------
        # 9. Calculate face absence duration (3 seconds per event)
        # ---------------------------------------------------------
        face_absence_duration = face_absence * 3.0

        # Do not allow absence duration to exceed exam duration
        face_absence_duration = min(
            face_absence_duration,
            exam_duration
        )

        # ---------------------------------------------------------
        # 10. Face Presence Ratio
        # ---------------------------------------------------------
        face_presence_ratio = (
            (exam_duration - face_absence_duration)
            / exam_duration
        ) * 100

        face_presence_ratio = max(
            0.0,
            min(100.0, face_presence_ratio)
        )

        face_presence_ratio = round(
            float(face_presence_ratio),
            2
        )

        # ---------------------------------------------------------
        # 11. Assign risk label based on centralized thresholds
        # ---------------------------------------------------------
        if score >= RISK_THRESHOLD_LOW:
            risk_label = "Low Risk"
        elif score >= RISK_THRESHOLD_MEDIUM:
            risk_label = "Medium Risk"
        else:
            risk_label = "High Risk"

        # ---------------------------------------------------------
        # 12. Existing remark system
        # ---------------------------------------------------------
        if score >= 90:
            remark = "Excellent Integrity"
        elif score >= 75:
            remark = "Good Integrity"
        elif score >= 50:
            remark = "Average Integrity"
        else:
            remark = "Poor Integrity (Manual Review Recommended)"

        # ---------------------------------------------------------
        # 13. Return complete scoring result
        # ---------------------------------------------------------
        return {
            "score": int(score),
            "remark": remark,
            "risk_label": risk_label,

            "face_absence": int(face_absence),
            "browser_focus": int(browser_focus),
            "multiple_faces": int(multiple_faces),
            "total_events": int(total_events),

            "total_deduction": float(total_deduction),

            "face_presence_ratio": float(face_presence_ratio),
        }

    finally:
        connection.close()


def calculate_integrity_score_for_session(session_id):
    """
    Calculates the integrity score for a specific exam session by session_id.
    Uses the exact same Pandas scoring, weighting, and risk classification rules.
    """
    connection = sqlite3.connect("database/exam_monitoring.db")
    try:
        session = connection.execute(
            """
            SELECT session_id, candidate_id, start_time, end_time
            FROM exam_sessions
            WHERE session_id = ?
            """,
            (session_id,)
        ).fetchone()

        if not session:
            return {
                "score": 100,
                "remark": "No session found",
                "risk_label": "Low Risk",
                "face_absence": 0,
                "browser_focus": 0,
                "multiple_faces": 0,
                "total_events": 0,
                "total_deduction": 0,
                "face_presence_ratio": 100.0,
            }

        session_id, candidate_id, start_time, end_time = session

        # Load events for this session into Pandas
        events_df = pd.read_sql_query(
            """
            SELECT event_type, timestamp, penalty
            FROM event_logs
            WHERE candidate_id = ?
              AND timestamp >= ?
              AND (timestamp <= ? OR ? IS NULL OR ? = '')
            ORDER BY timestamp ASC
            """,
            connection,
            params=(candidate_id, start_time, end_time, end_time, end_time)
        )

        if events_df.empty:
            return {
                "score": 100,
                "remark": "Excellent Integrity",
                "risk_label": "Low Risk",
                "face_absence": 0,
                "browser_focus": 0,
                "multiple_faces": 0,
                "total_events": 0,
                "total_deduction": 0,
                "face_presence_ratio": 100.0,
            }

        events_df["weight"] = events_df["event_type"].map(EVENT_WEIGHTS).fillna(0)
        total_deduction = int(events_df["weight"].sum())

        face_absence = int((events_df["event_type"] == "Face Not Detected").sum())
        browser_focus = int((events_df["event_type"] == "Browser Focus Lost").sum())
        multiple_faces = int((events_df["event_type"] == "Multiple Faces Detected").sum())
        total_events = face_absence + browser_focus + multiple_faces

        raw_score = 100 - total_deduction
        score = int(max(0, min(100, raw_score)))

        start = pd.to_datetime(start_time)
        if end_time:
            end = pd.to_datetime(end_time)
        else:
            end = pd.to_datetime(datetime.now())

        exam_duration = (end - start).total_seconds()
        if exam_duration <= 0:
            exam_duration = 1.0

        face_absence_duration = face_absence * 3.0
        face_absence_duration = min(face_absence_duration, exam_duration)

        face_presence_ratio = ((exam_duration - face_absence_duration) / exam_duration) * 100
        face_presence_ratio = max(0.0, min(100.0, face_presence_ratio))
        face_presence_ratio = round(float(face_presence_ratio), 2)

        if score >= RISK_THRESHOLD_LOW:
            risk_label = "Low Risk"
        elif score >= RISK_THRESHOLD_MEDIUM:
            risk_label = "Medium Risk"
        else:
            risk_label = "High Risk"

        if score >= 90:
            remark = "Excellent Integrity"
        elif score >= 75:
            remark = "Good Integrity"
        elif score >= 50:
            remark = "Average Integrity"
        else:
            remark = "Poor Integrity (Manual Review Recommended)"

        return {
            "score": int(score),
            "remark": remark,
            "risk_label": risk_label,
            "face_absence": int(face_absence),
            "browser_focus": int(browser_focus),
            "multiple_faces": int(multiple_faces),
            "total_events": int(total_events),
            "total_deduction": float(total_deduction),
            "face_presence_ratio": float(face_presence_ratio),
        }
    finally:
        connection.close()
