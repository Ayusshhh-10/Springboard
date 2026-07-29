from utils.event_logger import get_event_count


def calculate_integrity_score(candidate_id):
    """
    Calculates integrity score for the latest exam session.
    """

    score = 100

    face_absence = get_event_count(
        candidate_id,
        "Face Not Detected"
    )

    browser_focus = get_event_count(
        candidate_id,
        "Browser Focus Lost"
    )

    multiple_faces = get_event_count(
        candidate_id,
        "Multiple Faces Detected"
    )

    score -= face_absence * 2
    score -= browser_focus * 5
    score -= multiple_faces * 10

    if score < 0:
        score = 0

    return {
        "score": score,
        "face_absence": face_absence,
        "browser_focus": browser_focus,
        "multiple_faces": multiple_faces
    }