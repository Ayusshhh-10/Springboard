import os
import sys

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)

from utils.db import get_db_connection, init_db


def run_migration():

    print("Initializing database tables...")
    init_db()

    print("Running data backfill/migration for ended exam sessions...")

    connection = get_db_connection()
    cursor = connection.cursor()

    # ---------------------------------------------------------
    # Check whether student_integrity_scores table exists
    # ---------------------------------------------------------

    table_exists = cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'student_integrity_scores'
        """
    ).fetchone()

    if not table_exists:
        print("[ERROR] student_integrity_scores table does not exist.")
        print("[ERROR] Please check database/schema.sql and utils/db.py")
        connection.close()
        return

    print("[SUCCESS] student_integrity_scores table exists.")

    # ---------------------------------------------------------
    # Get all ended exam sessions
    # ---------------------------------------------------------

    sessions = cursor.execute(
        """
        SELECT session_id, candidate_id, start_time, end_time
        FROM exam_sessions
        WHERE status = 'Ended'
        """
    ).fetchall()

    print(f"Found {len(sessions)} ended exam sessions.")

    # ---------------------------------------------------------
    # Process every ended session
    # ---------------------------------------------------------

    for session in sessions:

        session_id, candidate_id, start_time, end_time = session

        # Check if already migrated
        existing = cursor.execute(
            """
            SELECT 1
            FROM student_integrity_scores
            WHERE session_id = ?
            """,
            (session_id,)
        ).fetchone()

        if existing:
            print(
                f"Session #{session_id} for Candidate "
                f"{candidate_id} already backfilled. Skipping."
            )
            continue

        # -----------------------------------------------------
        # Get candidate name
        # -----------------------------------------------------

        candidate_row = cursor.execute(
            """
            SELECT name
            FROM candidates
            WHERE candidate_id = ?
            """,
            (candidate_id,)
        ).fetchone()

        name = candidate_row[0] if candidate_row else "Unknown Candidate"

        # -----------------------------------------------------
        # Count suspicious events for this session
        # -----------------------------------------------------

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

        for event_type, count in event_counts:

            if event_type in counts:
                counts[event_type] = count

        # -----------------------------------------------------
        # Calculate integrity score
        # -----------------------------------------------------

        score = 100

        score -= counts["Face Not Detected"] * 5
        score -= counts["Browser Focus Lost"] * 10
        score -= counts["Multiple Faces Detected"] * 15

        if score < 0:
            score = 0

        total_events = sum(counts.values())

        # -----------------------------------------------------
        # Find latest proof image
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Insert integrity score
        # -----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO student_integrity_scores
            (
                candidate_id,
                name,
                session_id,
                integrity_score,
                total_suspicious_events,
                proof_image
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                name,
                session_id,
                score,
                total_events,
                proof_image
            )
        )

        print(
            f"Backfilled Session #{session_id} | "
            f"Candidate: {name} ({candidate_id}) | "
            f"Score: {score} | "
            f"Events: {total_events} | "
            f"Proof: {proof_image}"
        )

    # ---------------------------------------------------------
    # Commit changes
    # ---------------------------------------------------------

    connection.commit()
    connection.close()

    print()
    print("[SUCCESS] Migration complete!")


if __name__ == "__main__":
    run_migration()