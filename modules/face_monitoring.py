import cv2
import os
import sqlite3
import time
from datetime import datetime


DB_PATH = "database/exam_monitoring.db"
PHOTOS_FOLDER = "photos"

os.makedirs(PHOTOS_FOLDER, exist_ok=True)


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_event_log_table():
    connection = get_db_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS event_logs (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            remarks TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
        )
        """
    )

    connection.commit()
    connection.close()


def check_candidate_exists(candidate_id):
    connection = get_db_connection()

    candidate = connection.execute(
        "SELECT * FROM candidates WHERE candidate_id = ?",
        (candidate_id,)
    ).fetchone()

    connection.close()

    return candidate is not None


def log_event(candidate_id, event_type, remarks):
    connection = get_db_connection()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    connection.execute(
        """
        INSERT INTO event_logs
        (candidate_id, event_type, timestamp, remarks)
        VALUES (?, ?, ?, ?)
        """,
        (candidate_id, event_type, timestamp, remarks)
    )

    connection.commit()
    connection.close()

    print(f"Event logged: {event_type} at {timestamp}")


def start_face_monitoring():
    create_event_log_table()

    candidate_id = input("Enter Candidate ID for monitoring: ").strip()

    if not candidate_id:
        print("Candidate ID is required.")
        return

    if not check_candidate_exists(candidate_id):
        print("Candidate ID not found in database. Please use a registered Candidate ID.")
        return

    face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("Error: Could not access the webcam.")
        return

    print("Face monitoring started successfully.")
    print("Press 'c' to capture image.")
    print("Press 'q' to quit.")

    absence_start_time = None
    absence_event_logged = False
    absence_duration = 0

    while True:
        ret, frame = camera.read()

        if not ret:
            print("Error: Could not read video frame.")
            break

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if len(faces) > 0:
            status_text = "Face Detected"
            status_color = (0, 255, 0)

            for (x, y, w, h) in faces:
                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    status_color,
                    2
                )

            absence_start_time = None
            absence_event_logged = False
            absence_duration = 0

        else:
            status_text = "Face Not Detected"
            status_color = (0, 0, 255)

            if absence_start_time is None:
                absence_start_time = time.time()

            absence_duration = int(time.time() - absence_start_time)

            if not absence_event_logged:
                log_event(
                    candidate_id,
                    "Face Not Detected",
                    "Candidate face was not visible in the webcam feed."
                )
                absence_event_logged = True

        cv2.putText(
            frame,
            f"Status: {status_text}",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2
        )

        cv2.putText(
            frame,
            f"Current Time: {current_time}",
            (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Face Absence Duration: {absence_duration} sec",
            (30, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            status_color,
            2
        )

        cv2.putText(
            frame,
            "Press 'c' to capture | Press 'q' to quit",
            (30, 460),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        cv2.imshow("Continuous Face Presence Monitoring", frame)

        key = cv2.waitKey(10) & 0xFF

        if key == ord("c"):
            image_name = f"captured_face_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            image_path = os.path.join(PHOTOS_FOLDER, image_name)

            cv2.imwrite(image_path, frame)

            print(f"Image captured and saved successfully: {image_path}")

        elif key == ord("q"):
            print("Face monitoring stopped.")
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    start_face_monitoring()