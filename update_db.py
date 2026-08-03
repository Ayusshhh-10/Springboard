import sqlite3

DB_PATH = "database/exam_monitoring.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

try:
    cursor.execute("""
        ALTER TABLE event_logs
        ADD COLUMN proof_image TEXT
    """)
    print("✅ proof_image column added.")
except sqlite3.OperationalError:
    print("ℹ️ proof_image column already exists.")

connection.commit()
connection.close()