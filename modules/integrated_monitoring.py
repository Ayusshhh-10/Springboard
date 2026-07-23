import cv2
import threading
from datetime import datetime
from utils.event_logger import log_event


monitoring_thread = None
stop_monitoring_event = threading.Event()

monitoring_data = {
    "is_running": False,
    "candidate_id": None,
    "face_status": "Not Started",
    "browser_status": "Browser Active",
    "last_face_absence_time": "No face absence yet"
}


def update_browser_status(event_type):
    """
    Updates browser status for the real-time monitoring dashboard.
    """
    if event_type == "Browser Focus Lost":
        monitoring_data["browser_status"] = "Browser Inactive"
    elif event_type == "Browser Focus Regained":
        monitoring_data["browser_status"] = "Browser Active"


def get_monitoring_data():
    """
    Returns latest face and browser monitoring status.
    """
    return monitoring_data


def face_monitoring_loop(candidate_id):
    """
    Runs face monitoring in background without stopping browser monitoring.
    """
    monitoring_data["is_running"] = True
    monitoring_data["candidate_id"] = candidate_id
    monitoring_data["face_status"] = "Starting Camera"

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    if face_cascade.empty():
        monitoring_data["face_status"] = "Face Model Not Loaded"
        log_event(
            candidate_id,
            "Face Model Error",
            "Haar Cascade face model could not be loaded."
        )
        return

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not camera.isOpened():
        monitoring_data["face_status"] = "Camera Not Opened"
        log_event(
            candidate_id,
            "Camera Error",
            "Webcam could not be opened during integrated monitoring."
        )
        return

    face_absence_logged = False

    while not stop_monitoring_event.is_set():
        success, frame = camera.read()

        if not success:
            monitoring_data["face_status"] = "Camera Frame Not Read"
            continue

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_frame = cv2.equalizeHist(gray_frame)

        faces = face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.05,
            minNeighbors=3,
            minSize=(40, 40)
        )

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if len(faces) > 0:
            monitoring_data["face_status"] = "Face Detected"
            face_absence_logged = False

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            cv2.putText(
                frame,
                "Face Detected",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

        else:
            monitoring_data["face_status"] = "Face Not Detected"

            if not face_absence_logged:
                monitoring_data["last_face_absence_time"] = current_time

                log_event(
                    candidate_id,
                    "Face Not Detected",
                    "Candidate face was not visible during integrated monitoring."
                )

                face_absence_logged = True

            cv2.putText(
                frame,
                "Face Not Detected",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )

        cv2.putText(
            frame,
            f"Time: {current_time}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.imshow("Integrated Face Monitoring", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:
            break

    camera.release()
    cv2.destroyAllWindows()

    monitoring_data["is_running"] = False
    monitoring_data["face_status"] = "Monitoring Stopped"


def start_integrated_monitoring(candidate_id):
    """
    Starts face monitoring in a background thread.
    """
    global monitoring_thread

    if monitoring_data["is_running"]:
        return

    stop_monitoring_event.clear()

    monitoring_thread = threading.Thread(
        target=face_monitoring_loop,
        args=(candidate_id,),
        daemon=True
    )

    monitoring_thread.start()


def stop_integrated_monitoring():
    """
    Stops face monitoring safely.
    """
    stop_monitoring_event.set()
    monitoring_data["is_running"] = False
    monitoring_data["face_status"] = "Monitoring Stopped"