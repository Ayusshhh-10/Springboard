import cv2
import time
import os
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
    "capture_browser_focus_screenshot": False,
    "browser_focus_proof_filename": None,
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

        absence_start_time = None
        multiple_face_start_time = None

        time.sleep(2)

        while not stop_monitoring_event.is_set():
            success, frame = camera.read()

            if not success or frame is None:
                print("Camera frame failed")
                monitoring_data["face_status"] = "Camera Frame Not Read"
                time.sleep(0.1)
                continue

            # Ensure violation directory exists
            os.makedirs(os.path.join("static", "violation_proofs"), exist_ok=True)

            # Check if screenshot is requested for Browser Focus Lost
            if monitoring_data.get("capture_browser_focus_screenshot"):
                filename = f"{candidate_id}_browser_focus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                filepath = os.path.join("static", "violation_proofs", filename)
                cv2.imwrite(filepath, frame)
                monitoring_data["browser_focus_proof_filename"] = f"violation_proofs/{filename}"
                monitoring_data["capture_browser_focus_screenshot"] = False

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(
                gray,
                1.1,
                4
            )

            print("Faces detected:", len(faces))

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 1. Multiple face detection handling
            if len(faces) >= 2:
                monitoring_data["multiple_face_status"] = "Yes"
                if multiple_face_start_time is None:
                    multiple_face_start_time = time.time()
                else:
                    elapsed = time.time() - multiple_face_start_time
                    if last_multiple_face_log_time is None:
                        if elapsed >= 3.0:
                            filename = f"{candidate_id}_multiple_faces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            filepath = os.path.join("static", "violation_proofs", filename)
                            cv2.imwrite(filepath, frame)
                            log_event(
                                candidate_id,
                                "Multiple Faces Detected",
                                "More than one face detected in camera.",
                                proof_image=f"violation_proofs/{filename}",
                                penalty=-10
                            )
                            last_multiple_face_log_time = time.time()
                            print("MULTIPLE FACE EVENT LOGGED")
                    else:
                        elapsed_since_log = time.time() - last_multiple_face_log_time
                        if elapsed_since_log >= 3.0:
                            filename = f"{candidate_id}_multiple_faces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            filepath = os.path.join("static", "violation_proofs", filename)
                            cv2.imwrite(filepath, frame)
                            log_event(
                                candidate_id,
                                "Multiple Faces Detected",
                                "More than one face detected in camera.",
                                proof_image=f"violation_proofs/{filename}",
                                penalty=-10
                            )
                            last_multiple_face_log_time = time.time()
                            print("MULTIPLE FACE EVENT LOGGED")
            else:
                monitoring_data["multiple_face_status"] = "No"
                multiple_face_start_time = None
                last_multiple_face_log_time = None

            # 2. Face missing (Not Detected) and single face handling
            if len(faces) > 0:
                monitoring_data["face_status"] = "Face Detected"
                monitoring_data["last_face_absence_time"] = "No face absence"
                absence_start_time = None
                last_absence_log_time = None

                # Draw rectangles for feedback on webcam window
                for (x, y, w, h) in faces:
                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x+w, y+h),
                        (0, 255, 0),
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
                monitoring_data["last_face_absence_time"] = current_time

                if absence_start_time is None:
                    absence_start_time = time.time()
                else:
                    elapsed = time.time() - absence_start_time
                    if last_absence_log_time is None:
                        if elapsed >= 3.0:
                            filename = f"{candidate_id}_face_missing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            filepath = os.path.join("static", "violation_proofs", filename)
                            cv2.imwrite(filepath, frame)
                            log_event(
                                candidate_id,
                                "Face Not Detected",
                                "Candidate face was not visible during integrated monitoring.",
                                proof_image=f"violation_proofs/{filename}",
                                penalty=-2
                            )
                            last_absence_log_time = time.time()
                            print("FACE ABSENCE EVENT LOGGED")
                    else:
                        elapsed_since_log = time.time() - last_absence_log_time
                        if elapsed_since_log >= 3.0:
                            filename = f"{candidate_id}_face_missing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            filepath = os.path.join("static", "violation_proofs", filename)
                            cv2.imwrite(filepath, frame)
                            log_event(
                                candidate_id,
                                "Face Not Detected",
                                "Candidate face was not visible during integrated monitoring.",
                                proof_image=f"violation_proofs/{filename}",
                                penalty=-2
                            )
                            last_absence_log_time = time.time()
                            print("FACE ABSENCE EVENT LOGGED")

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
    monitoring_data["capture_browser_focus_screenshot"] = False
    monitoring_data["browser_focus_proof_filename"] = None

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