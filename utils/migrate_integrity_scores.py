import os
import sys
import sqlite3

# Ensure current folder is in system path to resolve imports correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.db import get_db_connection, init_db

def run_migration():
    print("Initializing database tables...")
    init_db()

    print("Running data backfill/migration for ended exam sessions...")
    connection = get_db_connection()
    cursor = connection.cursor()

    # Get all ended sessions
    sessions = cursor.execute(
        """
        SELECT session_id, candidate_id, start_time, end_time
        FROM exam_sessions
        WHERE status = 'Ended'
        """
    ).fetchall()

    print(f"Found {len(sessions)} ended exam sessions.")

    for session in sessions:
        session_id, candidate_id, start_time, end_time = session

        # Check if record already exists in student_integrity_scores
        existing = cursor.execute(
            "SELECT 1 FROM student_integrity_scores WHERE session_id = ?",
            (session_id,)
        ).fetchone()

        if existing:
            print(f"Session #{session_id} for Candidate {candidate_id} already backfilled. Skipping.")
            continue

        # Fetch candidate name
        candidate_row = cursor.execute(
            "SELECT name FROM candidates WHERE candidate_id = ?",
            (candidate_id,)
        ).fetchone()
        name = candidate_row[0] if candidate_row else "Unknown Candidate"

        # Count events for this session
        event_counts = cursor.execute(
            """
            SELECT event_type, COUNT(*)
            FROM event_logs
            WHERE candidate_id = ?
              AND timestamp >= ?
              AND timestamp <= ?
            GROUP BY event_type
            """,
            (candidate_id, start_time, end_time)
        ).fetchall()

        counts = {
            "Face Not Detected": 0,
            "Browser Focus Lost": 0,
            "Multiple Faces Detected": 0
        }
        for row in event_counts:
            event_type, count = row[0], row[1]
            if event_type in counts:
                counts[event_type] = count

        # Calculate score
        score = 100
        score -= counts["Face Not Detected"] * 5
        score -= counts["Browser Focus Lost"] * 10
        score -= counts["Multiple Faces Detected"] * 15
        if score < 0:
            score = 0

        total_events = sum(counts.values())

        # Find latest proof image in this session
        proof_row = cursor.execute(
            """
            SELECT proof_image
            FROM event_logs
            WHERE candidate_id = ?
              AND timestamp >= ?
              AND timestamp <= ?
              AND proof_image IS NOT NULL
              AND proof_image != ''
            ORDER BY event_id DESC
            LIMIT 1
            """,
            (candidate_id, start_time, end_time)
        ).fetchone()

        proof_image = proof_row[0] if proof_row else None

        # Insert record
        cursor.execute(
            """
            INSERT INTO student_integrity_scores
            (candidate_id, name, session_id, integrity_score, total_suspicious_events, proof_image)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (candidate_id, name, session_id, score, total_events, proof_image)
        )
        print(f"Backfilled Session #{session_id} | Candidate: {name} ({candidate_id}) | Score: {score} | Events: {total_events} | Proof: {proof_image}")

    connection.commit()
    connection.close()
    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
