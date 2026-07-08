import sqlite3


DATABASE_PATH = "database/exam_monitoring.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()

    with open("database/schema.sql", "r") as file:
        connection.executescript(file.read())

    connection.commit()
    connection.close()