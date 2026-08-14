import sqlite3
from datetime import datetime, timedelta
import os
import sys

# Ensure we can import from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.integrity_score import calculate_integrity_score

DB_PATH = "database/exam_monitoring.db"

def run_tests():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    print("=" * 70)
    print("STARTING INTEGRITY SCORING MODULE VALIDATION")
    print("=" * 70)

    # 1. Clean up any previous test remnants
    cleanup_test_data(cursor)
    connection.commit()

    # 2. Define test cases
    test_cases = [
        {
            "name": "TEST_perfect",
            "description": "Perfect integrity (No suspicious events)",
            "duration_minutes": 10,
            "events": [],
            "expected_score": 100,
            "expected_presence": 100.0,
            "expected_risk": "Low Risk",
            "expected_deduction": 0.0
        },
        {
            "name": "TEST_minor",
            "description": "Minor infractions (5 Face Not Detected)",
            "duration_minutes": 5,
            "events": [
                ("Face Not Detected", 1.0),
                ("Face Not Detected", 2.0),
                ("Face Not Detected", 3.0),
                ("Face Not Detected", 4.0),
                ("Face Not Detected", 4.5),
            ],
            "expected_score": 90, # 100 - (5 * 2)
            "expected_presence": 95.0, # (300 - 15) / 300 * 100
            "expected_risk": "Low Risk",
            "expected_deduction": 10.0
        },
        {
            "name": "TEST_frequent",
            "description": "Frequent infractions (Mixed suspicious events)",
            "duration_minutes": 10,
            "events": [
                ("Face Not Detected", 1.0),
                ("Face Not Detected", 1.5),
                ("Face Not Detected", 2.0),
                ("Face Not Detected", 2.5),
                ("Face Not Detected", 3.0),
                ("Face Not Detected", 3.5),
                ("Face Not Detected", 4.0),
                ("Face Not Detected", 4.5),
                ("Face Not Detected", 5.0),
                ("Face Not Detected", 5.5), # 10 face not detected = 20 points
                ("Browser Focus Lost", 6.0),
                ("Browser Focus Lost", 7.0),
                ("Browser Focus Lost", 8.0),
                ("Browser Focus Lost", 8.5), # 4 browser focus lost = 20 points
                ("Multiple Faces Detected", 9.0),
                ("Multiple Faces Detected", 9.5), # 2 multiple faces = 20 points
            ],
            "expected_score": 40, # 100 - 60
            "expected_presence": 95.0, # (600 - 30) / 600 * 100
            "expected_risk": "High Risk",
            "expected_deduction": 60.0
        },
        {
            "name": "TEST_extreme",
            "description": "Extreme infractions (Negative score bound check)",
            "duration_minutes": 5,
            "events": [
                ("Face Not Detected", 0.5)] * 25 + \
                [("Browser Focus Lost", 1.0)] * 10 + \
                [("Multiple Faces Detected", 2.0)] * 5,
            # Deductions: 25*2 + 10*5 + 5*10 = 150 points. Score must be capped at 0.
            "expected_score": 0,
            "expected_presence": 75.0, # (300 - 75) / 300 * 100
            "expected_risk": "High Risk",
            "expected_deduction": 150.0
        },
        {
            "name": "TEST_short",
            "description": "Extremely short session (Absence duration capped)",
            "duration_minutes": 0.1667, # 10 seconds
            "events": [
                ("Face Not Detected", 0.01),
                ("Face Not Detected", 0.02),
                ("Face Not Detected", 0.03),
                ("Face Not Detected", 0.04),
                ("Face Not Detected", 0.05), # 5 events = 15 seconds absence, capped at 10s duration
            ],
            "expected_score": 90, # 100 - 10
            "expected_presence": 0.0, # (10 - 10) / 10 * 100
            "expected_risk": "Low Risk",
            "expected_deduction": 10.0
        }
    ]

    all_passed = True

    for tc in test_cases:
        candidate_id = tc["name"]
        description = tc["description"]
        duration_minutes = tc["duration_minutes"]
        events = tc["events"]

        # Insert test candidate
        cursor.execute(
            "INSERT OR IGNORE INTO candidates (candidate_id, name, email, password) VALUES (?, ?, ?, ?)",
            (candidate_id, f"Test {candidate_id}", f"{candidate_id}@test.com", "password")
        )

        # Set timestamps
        start_time = datetime.now() - timedelta(minutes=duration_minutes)
        end_time = datetime.now()
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        # Insert test exam session
        cursor.execute(
            "INSERT INTO exam_sessions (candidate_id, start_time, end_time, status) VALUES (?, ?, ?, ?)",
            (candidate_id, start_str, end_str, "Ended")
        )
        connection.commit()

        # Insert events
        for ev_type, offset_minutes in events:
            ev_time = start_time + timedelta(minutes=offset_minutes)
            ev_time_str = ev_time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO event_logs (candidate_id, event_type, timestamp, remarks) VALUES (?, ?, ?, ?)",
                (candidate_id, ev_type, ev_time_str, f"Mocked infraction of type {ev_type}")
            )
        connection.commit()

        # Call module function
        result = calculate_integrity_score(candidate_id)

        # Verify results
        score_ok = result["score"] == tc["expected_score"]
        deduction_ok = result["total_deduction"] == tc["expected_deduction"]
        presence_ok = abs(result["face_presence_ratio"] - tc["expected_presence"]) < 0.01
        risk_ok = result["risk_label"] == tc["expected_risk"]

        print(f"\nTest Case: {candidate_id} - {description}")
        print("-" * 50)
        print(f"  Score:             {result['score']} (Expected: {tc['expected_score']}) -> {'PASS' if score_ok else 'FAIL'}")
        print(f"  Total Deduction:   {result['total_deduction']} (Expected: {tc['expected_deduction']}) -> {'PASS' if deduction_ok else 'FAIL'}")
        print(f"  Presence Ratio:    {result['face_presence_ratio']}% (Expected: {tc['expected_presence']}%) -> {'PASS' if presence_ok else 'FAIL'}")
        print(f"  Risk Label:        {result['risk_label']} (Expected: {tc['expected_risk']}) -> {'PASS' if risk_ok else 'FAIL'}")

        if not (score_ok and deduction_ok and presence_ok and risk_ok):
            all_passed = False

    # Cleanup
    print("\nCleaning up validation data...")
    cleanup_test_data(cursor)
    connection.commit()
    connection.close()

    print("=" * 70)
    if all_passed:
        print("ALL VALIDATION TESTS PASSED SUCCESSFULLY!")
    else:
        print("SOME VALIDATION TESTS FAILED. PLEASE CHECK LOGS.")
    print("=" * 70)


def cleanup_test_data(cursor):
    cursor.execute("DELETE FROM event_logs WHERE candidate_id LIKE 'TEST_%'")
    cursor.execute("DELETE FROM exam_sessions WHERE candidate_id LIKE 'TEST_%'")
    cursor.execute("DELETE FROM student_integrity_scores WHERE candidate_id LIKE 'TEST_%'")
    cursor.execute("DELETE FROM candidates WHERE candidate_id LIKE 'TEST_%'")


if __name__ == "__main__":
    run_tests()
