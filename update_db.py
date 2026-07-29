import sqlite3

connection = sqlite3.connect("database/exam_monitoring.db")
cursor = connection.cursor()

try:
    cursor.execute("""
        ALTER TABLE exam_sessions
        ADD COLUMN integrity_score INTEGER DEFAULT 100
    """)
    print("✅ integrity_score column added.")
except Exception as e:
    print(e)

connection.commit()
connection.close()