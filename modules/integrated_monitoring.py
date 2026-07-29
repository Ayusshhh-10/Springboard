import cv2
import time
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
    "last_face_absence_time": "No face absence yet",
    "multiple_face_status": "No",
    
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
    try:
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

        camera = cv2.VideoCapture(0)

        if not camera.isOpened():
            print("Camera NOT opened")
            monitoring_data["face_status"] = "Camera Not Opened"
            return

        ret, test_frame = camera.read()
        print("Initial frame:", ret)

        if not ret:
            print("Unable to read first frame")
            monitoring_data["face_status"] = "Camera Frame Not Read"
            camera.release()
            return
        


        last_absence_log_time = None
        last_multiple_face_log_time = None

        time.sleep(2)


        while not stop_monitoring_event.is_set():
            success, frame = camera.read()

            if not success or frame is None:
                print("Camera frame failed")
                monitoring_data["face_status"] = "Camera Frame Not Read"
                time.sleep(0.1)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(
                gray,
                1.1,
                4
            )

            print("Faces:", len(faces))
            print("Faces detected:", len(faces))

                    # Multiple face detection
            if len(faces) >= 2:

                monitoring_data["multiple_face_status"] = "Yes"

                current_seconds = time.time()

                if (
                    last_multiple_face_log_time is None
                    or current_seconds - last_multiple_face_log_time >= 2
                ):

                    log_event(
                    candidate_id,
                    "Multiple Faces Detected",
                    "More than one face detected in camera."
                    )

                    print("MULTIPLE FACE EVENT LOGGED")

                    last_multiple_face_log_time = current_seconds

            else:

                monitoring_data["multiple_face_status"] = "No"
                last_multiple_face_log_time = None

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if len(faces) > 0:

                monitoring_data["face_status"] = "Face Detected"

                monitoring_data["last_face_absence_time"] = "No face absence"

                last_absence_log_time = None

                largest_face = max(
                    faces,
                    key=lambda face: face[2] * face[3]
                )

                x, y, w, h = largest_face

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x+w, y+h),
                    (0,255,0),
                    2
                )
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

                current_seconds = time.time()

                if last_absence_log_time is None:

                    last_absence_log_time = current_seconds

                elif current_seconds - last_absence_log_time >= 2:

                    monitoring_data["last_face_absence_time"] = current_time

                    log_event(
                        candidate_id,
                        "Face Not Detected",
                        "Candidate face was not visible during integrated monitoring."
                    )

                    print("FACE ABSENCE EVENT LOGGED")

                    last_absence_log_time = current_seconds

                cv2.putText(
                    frame,
                    "Face Not Detected",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
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

    except Exception as e:
        print("FACE THREAD ERROR:", e)
        monitoring_data["face_status"] = f"Error: {e}"

    finally:
        if 'camera' in locals() and camera.isOpened():
            camera.release()

        cv2.destroyAllWindows()

        monitoring_data["is_running"] = False


def start_integrated_monitoring(candidate_id):
    """
    Starts face monitoring in a background thread.
    """
    global monitoring_thread

    # If already running, do nothing
    if monitoring_thread is not None and monitoring_thread.is_alive():
        print("Monitoring already running")
        return

    stop_monitoring_event.clear()

    monitoring_data["is_running"] = True
    monitoring_data["candidate_id"] = candidate_id
    monitoring_data["face_status"] = "Starting Camera"
    monitoring_data["browser_status"] = "Browser Active"
    monitoring_data["last_face_absence_time"] = "No face absence yet"
    monitoring_data["multiple_face_status"] = "No"

    # IMPORTANT: create a NEW thread every time
    monitoring_thread = threading.Thread(
        target=face_monitoring_loop,
        args=(candidate_id,),
        daemon=True
    )

    monitoring_thread.start()

    print("Monitoring thread started")
    print("Thread Alive:", monitoring_thread.is_alive())

def stop_integrated_monitoring():
    global monitoring_thread

    stop_monitoring_event.set()

    monitoring_thread = None

    monitoring_data["is_running"] = False