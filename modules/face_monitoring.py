import cv2
import os
import sqlite3
import time
from datetime import datetime
from utils.event_logger import log_event


DB_PATH = "database/exam_monitoring.db"
PHOTOS_FOLDER = "photos"
PROOFS_FOLDER = os.path.join("static", "violation_proofs")

os.makedirs(PHOTOS_FOLDER, exist_ok=True)
os.makedirs(PROOFS_FOLDER, exist_ok=True)


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def check_candidate_exists(candidate_id):
    connection = get_db_connection()

    candidate = connection.execute(
        "SELECT * FROM candidates WHERE candidate_id = ?",
        (candidate_id,)
    ).fetchone()

    connection.close()

    return candidate is not None


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


def start_face_monitoring():
    candidate_id = input("Enter Candidate ID for monitoring: ").strip()

    if not candidate_id:
        print("Candidate ID is required.")
        return

    if not check_candidate_exists(candidate_id):
        print("Candidate ID not found in database. Please use a registered Candidate ID.")
        return

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    profile_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_profileface.xml"
    )

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Error: Could not access the webcam.")
        return

    print("Face monitoring started successfully.")
    print("Press 'c' to capture image.")
    print("Press 'q' to quit.")

    absence_start_time = None
    last_absence_log_time = None
    multiple_face_start_time = None
    last_multiple_face_log_time = None

    while True:
        ret, frame = camera.read()

        if not ret or frame is None:
            print("Error: Could not read video frame.")
            break

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = detect_faces(gray_frame, face_cascade, profile_cascade)
        num_faces = len(faces)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Multiple Faces Detected
        if num_faces >= 2:
            absence_start_time = None
            last_absence_log_time = None

            if multiple_face_start_time is None:
                multiple_face_start_time = time.time()

            elapsed_mf = time.time() - multiple_face_start_time

            if last_multiple_face_log_time is None:
                if elapsed_mf >= 3.0:
                    filename = f"{candidate_id}_multiple_faces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    filepath = os.path.join(PROOFS_FOLDER, filename)
                    cv2.imwrite(filepath, frame)
                    log_event(
                        candidate_id,
                        "Multiple Faces Detected",
                        f"More than one face detected in camera ({num_faces} faces).",
                        proof_image=f"violation_proofs/{filename}",
                        penalty=-10
                    )
                    last_multiple_face_log_time = time.time()
                    print(f"[{current_time}] MULTIPLE FACE EVENT LOGGED ({num_faces} faces)")
            else:
                if time.time() - last_multiple_face_log_time >= 3.0:
                    filename = f"{candidate_id}_multiple_faces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    filepath = os.path.join(PROOFS_FOLDER, filename)
                    cv2.imwrite(filepath, frame)
                    log_event(
                        candidate_id,
                        "Multiple Faces Detected",
                        f"More than one face detected in camera ({num_faces} faces).",
                        proof_image=f"violation_proofs/{filename}",
                        penalty=-10
                    )
                    last_multiple_face_log_time = time.time()
                    print(f"[{current_time}] MULTIPLE FACE EVENT LOGGED ({num_faces} faces)")

        # 2. Exactly 1 Face Detected (Normal)
        elif num_faces == 1:
            absence_start_time = None
            last_absence_log_time = None
            multiple_face_start_time = None
            last_multiple_face_log_time = None

        # 3. No Face Detected (Absence)
        else:
            multiple_face_start_time = None
            last_multiple_face_log_time = None

            if absence_start_time is None:
                absence_start_time = time.time()

            elapsed_abs = time.time() - absence_start_time

            if last_absence_log_time is None:
                if elapsed_abs >= 3.0:
                    filename = f"{candidate_id}_face_missing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    filepath = os.path.join(PROOFS_FOLDER, filename)
                    cv2.imwrite(filepath, frame)
                    log_event(
                        candidate_id,
                        "Face Not Detected",
                        "Candidate face was not visible during integrated monitoring.",
                        proof_image=f"violation_proofs/{filename}",
                        penalty=-2
                    )
                    last_absence_log_time = time.time()
                    print(f"[{current_time}] FACE ABSENCE EVENT LOGGED")
            else:
                if time.time() - last_absence_log_time >= 3.0:
                    filename = f"{candidate_id}_face_missing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    filepath = os.path.join(PROOFS_FOLDER, filename)
                    cv2.imwrite(filepath, frame)
                    log_event(
                        candidate_id,
                        "Face Not Detected",
                        "Candidate face was not visible during integrated monitoring.",
                        proof_image=f"violation_proofs/{filename}",
                        penalty=-2
                    )
                    last_absence_log_time = time.time()
                    print(f"[{current_time}] FACE ABSENCE EVENT LOGGED")

        try:
            cv2.imshow("Continuous Face Presence Monitoring", frame)
            key = cv2.waitKey(10) & 0xFF
            if key == ord("c"):
                image_name = f"captured_face_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                image_path = os.path.join(PHOTOS_FOLDER, image_name)
                cv2.imwrite(image_path, frame)
                print(f"Image captured and saved successfully: {image_path}")
            elif key == ord("q") or key == 27:
                print("Face monitoring stopped.")
                break
        except Exception:
            break

    camera.release()
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass


if __name__ == "__main__":
    start_face_monitoring()
