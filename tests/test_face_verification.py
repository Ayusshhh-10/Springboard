import unittest
import os
import sys
import sqlite3

# Ensure Springboard directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import (
    FACE_MATCH_TOLERANCE,
    MAX_VERIFICATION_ATTEMPTS,
    VERIFICATION_REQUIRED_FRAMES,
    VERIFICATION_TOTAL_FRAMES
)


class TestFaceVerification(unittest.TestCase):

    def test_configuration_values(self):
        self.assertIsInstance(FACE_MATCH_TOLERANCE, float)
        self.assertGreater(FACE_MATCH_TOLERANCE, 0.0)
        self.assertLess(FACE_MATCH_TOLERANCE, 1.0)

        self.assertIsInstance(MAX_VERIFICATION_ATTEMPTS, int)
        self.assertEqual(MAX_VERIFICATION_ATTEMPTS, 3)

        self.assertIsInstance(VERIFICATION_REQUIRED_FRAMES, int)
        self.assertIsInstance(VERIFICATION_TOTAL_FRAMES, int)

        self.assertLessEqual(
            VERIFICATION_REQUIRED_FRAMES,
            VERIFICATION_TOTAL_FRAMES
        )

    def test_database_schema(self):
        db_path = "database/exam_monitoring.db"

        self.assertTrue(
            os.path.exists(db_path),
            "Database should exist"
        )

        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        columns_info = cursor.execute(
            "PRAGMA table_info(exam_sessions)"
        ).fetchall()

        columns = [col["name"] for col in columns_info]

        self.assertIn("identity_verified", columns)
        self.assertIn("verification_time", columns)
        self.assertIn("verification_attempts", columns)

        connection.close()

    def test_face_recognition_dependency(self):
        import face_recognition
        import dlib

        self.assertIsNotNone(face_recognition)
        self.assertIsNotNone(dlib)


if __name__ == "__main__":
    unittest.main()