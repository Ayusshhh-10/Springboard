import os
import sqlite3

DB_PATH = "database/exam_monitoring.db"

def run_migration():
    print("Starting database migration for verification columns...")
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at: {os.path.abspath(DB_PATH)}")
        print("Skipping migration. Initialize DB first.")
        return

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    try:
        # Check current columns of exam_sessions
        columns_info = cursor.execute("PRAGMA table_info(exam_sessions)").fetchall()
        columns = [col['name'] for col in columns_info]
        print(f"Current columns in exam_sessions: {columns}")

        # Add columns if they do not exist
        if "identity_verified" not in columns:
            print("Adding column 'identity_verified' to exam_sessions...")
            cursor.execute("ALTER TABLE exam_sessions ADD COLUMN identity_verified INTEGER DEFAULT 0")
        else:
            print("Column 'identity_verified' already exists.")

        if "verification_time" not in columns:
            print("Adding column 'verification_time' to exam_sessions...")
            cursor.execute("ALTER TABLE exam_sessions ADD COLUMN verification_time TEXT")
        else:
            print("Column 'verification_time' already exists.")

        if "verification_attempts" not in columns:
            print("Adding column 'verification_attempts' to exam_sessions...")
            cursor.execute("ALTER TABLE exam_sessions ADD COLUMN verification_attempts INTEGER DEFAULT 0")
        else:
            print("Column 'verification_attempts' already exists.")

        connection.commit()
        print("Database migration completed successfully!")

    except Exception as e:
        connection.rollback()
        print(f"Error during database migration: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    run_migration()
