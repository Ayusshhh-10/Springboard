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
    "multiple_face_status": "No"
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


def filter_overlapping_boxes(boxes, overlap_thresh=0.35):
    """
    Suppresses redundant/overlapping bounding boxes for the same face.
    """
    if len(boxes) == 0:
        return []

    rects = [[b[0], b[1], b[0] + b[2], b[1] + b[3], b[2] * b[3]] for b in boxes]
    rects.sort(key=lambda x: x[4], reverse=True)

    picked = []
    while len(rects) > 0:
        current = rects.pop(0)
        picked.append(current)

        filtered = []
        for r in rects:
            xx1 = max(current[0], r[0])
            yy1 = max(current[1], r[1])
            xx2 = min(current[2], r[2])
            yy2 = min(current[3], r[3])

            w = max(0, xx2 - xx1)
            h = max(0, yy2 - yy1)
            inter_area = w * h
            min_area = min(current[4], r[4])

            if min_area > 0 and (inter_area / min_area) > overlap_thresh:
                continue
            filtered.append(r)
        rects = filtered

    return [(p[0], p[1], p[2] - p[0], p[3] - p[1]) for p in picked]


def detect_faces(gray_frame, face_cascade, profile_cascade):
    """
    Detects both frontal and profile/angled faces with sensitive parameters.
    """
    frontal_faces = face_cascade.detectMultiScale(
        gray_frame,
        scaleFactor=1.08,
        minNeighbors=4,
        minSize=(35, 35)
    )

    profile_faces = profile_cascade.detectMultiScale(
        gray_frame,
        scaleFactor=1.08,
        minNeighbors=4,
        minSize=(35, 35)
    )

    flipped_gray = cv2.flip(gray_frame, 1)
    profile_faces_flipped = profile_cascade.detectMultiScale(
        flipped_gray,
        scaleFactor=1.08,
        minNeighbors=4,
        minSize=(35, 35)
    )

    w_frame = gray_frame.shape[1]
    unflipped = []
    for (x, y, w, h) in profile_faces_flipped:
        unflipped.append((w_frame - x - w, y, w, h))

    all_raw = list(frontal_faces) + list(profile_faces) + unflipped
    return filter_overlapping_boxes(all_raw, overlap_thresh=0.3)


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
        profile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_profileface.xml"
        )

        if face_cascade.empty():
            monitoring_data["face_status"] = "Face Model Not Loaded"
            log_event(
                candidate_id,
                "Face Model Error",
                "Haar Cascade face model could not be loaded."
            )
            return

        camera = None
        for i in range(10):
            camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not camera.isOpened():
                camera = cv2.VideoCapture(0)
            if camera.isOpened():
                break
            print(f"Webcam locked. Retrying camera connection ({i+1}/10)...")
            time.sleep(1.0)

        if not camera or not camera.isOpened():
            print("Camera NOT opened after retries")
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

        time.sleep(1)

        while not stop_monitoring_event.is_set():
            success, frame = camera.read()

            if not success or frame is None:
                print("Camera frame failed")
                monitoring_data["face_status"] = "Camera Frame Not Read"
                time.sleep(0.1)
                continue

            # Ensure violation directory exists
            os.makedirs(os.path.join("static", "violation_proofs"), exist_ok=True)


            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect multiple faces accurately across angles and distances
            faces = detect_faces(gray, face_cascade, profile_cascade)
            num_faces = len(faces)

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 1. Multiple face detection handling (>= 2 faces)
            if num_faces >= 2:
                monitoring_data["face_status"] = "Multiple Faces Detected"
                monitoring_data["multiple_face_status"] = "Yes"
                monitoring_data["last_face_absence_time"] = "No face absence"

                # Reset absence timer
                absence_start_time = None
                last_absence_log_time = None

                if multiple_face_start_time is None:
                    multiple_face_start_time = time.time()

                elapsed_mf = time.time() - multiple_face_start_time

                if last_multiple_face_log_time is None:
                    if elapsed_mf >= 3.0:
                        filename = f"{candidate_id}_multiple_faces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        filepath = os.path.join("static", "violation_proofs", filename)
                        cv2.imwrite(filepath, frame)
                        log_event(
                            candidate_id,
                            "Multiple Faces Detected",
                            f"More than one face detected in camera ({num_faces} faces).",
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
                            f"More than one face detected in camera ({num_faces} faces).",
                            proof_image=f"violation_proofs/{filename}",
                            penalty=-10
                        )
                        last_multiple_face_log_time = time.time()
                        print("MULTIPLE FACE EVENT LOGGED")

            # 2. Single face detection (Normal state: exactly 1 face)
            elif num_faces == 1:
                monitoring_data["face_status"] = "Face Detected"
                monitoring_data["multiple_face_status"] = "No"
                monitoring_data["last_face_absence_time"] = "No face absence"

                # Reset both violation timers
                absence_start_time = None
                last_absence_log_time = None
                multiple_face_start_time = None
                last_multiple_face_log_time = None

            # 3. Face absence handling (0 faces)
            else:
                monitoring_data["face_status"] = "Face Not Detected"
                monitoring_data["multiple_face_status"] = "No"
                monitoring_data["last_face_absence_time"] = current_time

                # Reset multiple face timer
                multiple_face_start_time = None
                last_multiple_face_log_time = None

                if absence_start_time is None:
                    absence_start_time = time.time()

                elapsed_abs = time.time() - absence_start_time

                if last_absence_log_time is None:
                    if elapsed_abs >= 3.0:
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

            try:
                cv2.imshow("Integrated Face Monitoring", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    break
            except Exception:
                pass

        camera.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        monitoring_data["is_running"] = False
        monitoring_data["face_status"] = "Monitoring Stopped"

    except Exception as e:
        print("FACE THREAD ERROR:", e)
        monitoring_data["face_status"] = f"Error: {e}"

    finally:
        if 'camera' in locals() and camera.isOpened():
            camera.release()

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

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
