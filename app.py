import os
import re
import cv2
from datetime import datetime
import base64
import uuid 
import io
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory,jsonify,send_file
import io
from reportlab.lib.pagesizes import A4

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet

from flask import send_file

from modules.integrated_monitoring import (
    start_integrated_monitoring,
    stop_integrated_monitoring,
    get_monitoring_data,
    update_browser_status
)

from utils.event_logger import (
    log_event,
    get_event_count,
    get_last_event_time,
    get_event_summary
)
from utils.integrity_score import calculate_integrity_score

from utils.db import get_db_connection, init_db


app = Flask(__name__)
app.secret_key = "online_exam_secret_key"

PHOTO_FOLDER = "uploads/candidate_photos"
os.makedirs(PHOTO_FOLDER, exist_ok=True)


def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)

def format_duration(total_seconds):
    total_seconds = int(total_seconds)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours} hr {minutes} min {seconds} sec"
    elif minutes > 0:
        return f"{minutes} min {seconds} sec"
    else:
        return f"{seconds} sec"


def calculate_session_duration(current_session):
    if not current_session or not current_session["start_time"]:
        return "Not started"

    start_time = datetime.strptime(
        current_session["start_time"],
        "%Y-%m-%d %H:%M:%S"
    )

    if current_session["end_time"]:
        end_time = datetime.strptime(
            current_session["end_time"],
            "%Y-%m-%d %H:%M:%S"
        )
    else:
        end_time = datetime.now()

    duration_seconds = (end_time - start_time).total_seconds()

    return format_duration(duration_seconds)

def capture_candidate_photo(candidate_id):
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        return None

    ret = False
    frame = None

    for _ in range(10):
        ret, frame = camera.read()

    camera.release()

    if not ret or frame is None:
        return None

    photo_name = f"{candidate_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    photo_path = os.path.join(PHOTO_FOLDER, photo_name)

    cv2.imwrite(photo_path, frame)

    return photo_path.replace("\\", "/")


@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/upload_photo", methods=["POST"])
def upload_photo():

    import base64
    import os
    from datetime import datetime

    data = request.json

    image = data.get("image")
    candidate_id = data.get("candidate_id", "temp")

    if not image:
        return {"success": False}

    image_data = image.split(",")[1]

    image_bytes = base64.b64decode(image_data)

    upload_folder = os.path.join("uploads", "candidate_photos")

    os.makedirs(upload_folder, exist_ok=True)

    filename = f"{candidate_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    filepath = os.path.join(upload_folder, filename)

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    return {
        "success": True,
        "photo_path": filepath
    }


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        candidate_id = "C" + uuid.uuid4().hex[:6].upper()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        photo_path = request.form.get("photo_path")

    

        print("========== REGISTER ==========")
        print("Candidate ID :", candidate_id)
        print("Name :", name)
        print("Email :", email)
        print("Password :", password)
        print("Captured Image :", photo_path)

        if  not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
        
                flash("Passwords do not match.", "error")
        
                return redirect(url_for("register"))

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return redirect(url_for("register"))

        connection = get_db_connection()

        existing_email = connection.execute(
            "SELECT * FROM candidates WHERE email = ?",
            (email,)
        ).fetchone()
        print("existing_email =", existing_email)

        if existing_email:
            connection.close()
            flash("This email is already registered.", "error")
            return redirect(url_for("register"))

        existing_candidate = connection.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?",
            (candidate_id,)
        ).fetchone()
        print("existing_candidate =", existing_candidate)

        if existing_candidate:
            connection.close()
            flash("This Candidate ID is already registered.", "error")
            return redirect(url_for("register"))
        
        if not photo_path:

            connection.close()

            flash("Please capture your photo before registering.", "error")

            return redirect(url_for("register"))
        print("Reached after photo validation")

        print("About to execute INSERT")
        
        connection.execute(
            """
            INSERT INTO candidates 
            (candidate_id, name, email, password, photo_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (candidate_id, name, email, password, photo_path)
        )
        

        print("========== INSERT ==========")
        print("Candidate ID:", candidate_id)
        print("Name:", name)
        print("Email:", email)
        print("Photo Path:", photo_path)

        connection.commit()

        count = connection.execute(
            "SELECT COUNT(*) FROM candidates"
        ).fetchone()[0]

        print("TOTAL CANDIDATES IN DB:", count)

        all_candidates = connection.execute(
            "SELECT candidate_id, name, email FROM candidates"
        ).fetchall()

        print(all_candidates)
        print("Data committed to database successfully.")
        connection.close()

        print("REDIRECTING TO LOGIN NOW")

        flash("Registration completed successfully. Please login.", "success")
        return redirect(url_for("login"))

        
    return render_template("registration.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.")
            return redirect(url_for("login"))

        if not is_valid_email(email):
            flash("Please enter a valid email address.")
            return redirect(url_for("login"))

        connection = get_db_connection()

        candidate = connection.execute(
            """
            SELECT * FROM candidates
            WHERE email = ? AND password = ?
            """,
            (email, password)
        ).fetchone()
       

        connection.close()

        if candidate:
            session["candidate_id"] = candidate["candidate_id"]
            session["candidate_name"] = candidate["name"]
            session["candidate_email"] = candidate["email"]
            session["candidate_photo"] = candidate["photo_path"]

            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password. Please try again.")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # Temporary credentials
        if username == "admin" and password == "admin123":

            session["admin"] = username

            return redirect(url_for("admin_dashboard"))

        flash("Invalid Username or Password")

    return render_template("admin_login.html")


@app.route("/dashboard")
def dashboard():
    if "candidate_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    connection = get_db_connection()

    current_session = connection.execute(
        """
        SELECT * FROM exam_sessions
        WHERE candidate_id = ?
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()

    connection.close()

    session_duration = calculate_session_duration(current_session)

    return render_template(
        "dashboard.html",
        candidate_name=session["candidate_name"],
        candidate_email=session["candidate_email"],
        candidate_photo=session["candidate_photo"],
        current_session=current_session
    )




@app.route("/exam")
def exam():

    if "candidate_id" not in session:

        return redirect(url_for("login"))

    connection = get_db_connection()

    current_session = connection.execute(

        """
        SELECT *
        FROM exam_sessions
        WHERE candidate_id=?
        ORDER BY session_id DESC
        LIMIT 1
        """,

        (session["candidate_id"],)

    ).fetchone()

    connection.close()

    return render_template(

        "exam.html",

        current_session=current_session,

        candidate_name=session["candidate_name"],

        candidate_email=session["candidate_email"],

        candidate_id=session["candidate_id"]

    )
        
@app.route("/log-browser-event", methods=["POST"])
def log_browser_event():
    """
    Receives browser focus events from JavaScript
    and stores them in the unified event_logs table.
    """
    if "candidate_id" not in session:
        return jsonify({
            "success": False,
            "message": "Candidate not logged in"
        }), 401

    data = request.get_json()

    event_type = data.get("event_type")
    remarks = data.get("remarks", "")

    allowed_events = [
        "Browser Focus Lost",
        "Browser Focus Regained"
    ]

    if event_type not in allowed_events:
        return jsonify({
            "success": False,
            "message": "Invalid browser event"
        }), 400

    candidate_id = session["candidate_id"]
    proof_image = None
    penalty = 0

    if event_type == "Browser Focus Lost":
        penalty = -5
        from modules.integrated_monitoring import get_monitoring_data
        monitoring_data = get_monitoring_data()
        if monitoring_data.get("is_running"):
            monitoring_data["capture_browser_focus_screenshot"] = True
            monitoring_data["browser_focus_proof_filename"] = None
            import time
            start_wait = time.time()
            while time.time() - start_wait < 1.5:
                if monitoring_data.get("browser_focus_proof_filename"):
                    proof_image = monitoring_data["browser_focus_proof_filename"]
                    break
                time.sleep(0.05)
            monitoring_data["browser_focus_proof_filename"] = None

    log_event(
        candidate_id,
        event_type,
        remarks,
        proof_image=proof_image,
        penalty=penalty
    )

    update_browser_status(event_type)

    return jsonify({
        "success": True,
        "browser_status": "Browser Inactive" if event_type == "Browser Focus Lost" else "Browser Active"
    })

@app.route("/monitoring-status")
def monitoring_status():
    """
    Sends real-time monitoring data to the dashboard.
    This includes face status, browser status, event counts,
    current date/time, and session timer.
    """
    if "candidate_id" not in session:
        return jsonify({
            "success": False,
            "message": "Candidate not logged in"
        }), 401

    candidate_id = session["candidate_id"]

    connection = get_db_connection()

    current_session = connection.execute(
        """
        SELECT * FROM exam_sessions
        WHERE candidate_id = ?
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (candidate_id,)
    ).fetchone()

    connection.close()

    monitoring_data = get_monitoring_data()

    integrity = calculate_integrity_score(candidate_id)
    face_absence_count = integrity["face_absence"]
    browser_focus_loss_count = integrity["browser_focus"]
    multiple_face_count = integrity["multiple_faces"]

    last_focus_loss_time = get_last_event_time(
        candidate_id,
        "Browser Focus Lost"
    )

    if last_focus_loss_time == "No event found":
        last_focus_loss_time = "No focus loss yet"

    return jsonify({
        "success": True,
        "candidate_name": session["candidate_name"],
        "candidate_id": candidate_id,
        "face_status": monitoring_data["face_status"],
        "browser_status": monitoring_data["browser_status"],
        "face_absence_count": face_absence_count,
        "browser_focus_loss_count": browser_focus_loss_count,
        "last_focus_loss_time": last_focus_loss_time,
        "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_timer": calculate_session_duration(current_session),
        "multiple_face_count": multiple_face_count,
        "multiple_face_status": monitoring_data["multiple_face_status"],
        "integrity_score": integrity["score"]
    })

@app.route("/start-exam", methods=["POST"])
def start_exam():
    if "candidate_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    candidate_id = session["candidate_id"]
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    connection = get_db_connection()

    active_session = connection.execute(
        """
        SELECT * FROM exam_sessions
        WHERE candidate_id = ? AND status IN ('Started', 'Paused', 'Resumed')
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (candidate_id,)
    ).fetchone()

    if active_session:
        connection.close()
        flash("An exam session is already active.")
        return redirect(url_for("exam"))

    connection.execute(
        """
        INSERT INTO exam_sessions
        (candidate_id, start_time, end_time, status)
        VALUES (?, ?, ?, ?)
        """,
        (candidate_id, start_time, "", "Started")
    )

    connection.commit()
    connection.close()

    print("CALLING START_INTEGRATED_MONITORING")
    start_integrated_monitoring(candidate_id)

    return redirect(url_for("exam"))

@app.route("/pause-exam", methods=["POST"])
def pause_exam():
    if "candidate_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    connection = get_db_connection()

    active_session = connection.execute(
        """
        SELECT * FROM exam_sessions
        WHERE candidate_id = ? AND status IN ('Started', 'Resumed')
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()

    if not active_session:
        connection.close()
        flash("No active exam session found to pause.")
        return redirect(url_for("dashboard"))

    connection.execute(
        "UPDATE exam_sessions SET status = ? WHERE session_id = ?",
        ("Paused", active_session["session_id"])
    )

    connection.commit()
    connection.close()

    flash("Exam session paused.")
    return redirect(url_for("dashboard"))


@app.route("/resume-exam", methods=["POST"])
def resume_exam():
    if "candidate_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    connection = get_db_connection()

    paused_session = connection.execute(
        """
        SELECT * FROM exam_sessions
        WHERE candidate_id = ? AND status = 'Paused'
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()

    if not paused_session:
        connection.close()
        flash("No paused exam session found to resume.")
        return redirect(url_for("dashboard"))

    connection.execute(
        "UPDATE exam_sessions SET status = ? WHERE session_id = ?",
        ("Resumed", paused_session["session_id"])
    )

    connection.commit()
    connection.close()

    flash("Exam session resumed.")
    return redirect(url_for("dashboard"))


@app.route("/end-exam", methods=["POST"])
def end_exam():

    if "candidate_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    connection = get_db_connection()

    active_session = connection.execute(
        """
        SELECT *
        FROM exam_sessions
        WHERE candidate_id = ?
        AND status IN ('Started','Paused','Resumed')
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()

    if not active_session:
        connection.close()
        flash("No active exam session found to end.")
        return redirect(url_for("dashboard"))


    result = calculate_integrity_score(
        session["candidate_id"]
    )

    connection.execute(
        """
        UPDATE exam_sessions
        SET
            end_time=?,
            status=?,
            integrity_score=?
        WHERE session_id=?
        """,
        (
            end_time,
            "Ended",
            result["score"],
            active_session["session_id"]
        )
    )

    # Find latest proof image in this session
    proof_row = connection.execute(
        """
        SELECT proof_image
        FROM event_logs
        WHERE candidate_id = ?
          AND timestamp >= ?
          AND proof_image IS NOT NULL
          AND proof_image != ''
        ORDER BY event_id DESC
        LIMIT 1
        """,
        (session["candidate_id"], active_session["start_time"])
    ).fetchone()
    proof_image = proof_row["proof_image"] if proof_row else None

    # Insert into the student_integrity_scores table
    connection.execute(
        """
        INSERT INTO student_integrity_scores
        (candidate_id, name, session_id, integrity_score, total_suspicious_events, proof_image)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session["candidate_id"],
            session["candidate_name"],
            active_session["session_id"],
            result["score"],
            result["total_events"],
            proof_image
        )
    )

    connection.commit()
    connection.close()

    stop_integrated_monitoring()

    return redirect(url_for("exam_report"))

@app.route("/exam-report")
def exam_report():

    if "candidate_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    report = connection.execute(
        """
        SELECT *
        FROM exam_sessions
        WHERE candidate_id=?
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()

    connection.close()

    result = calculate_integrity_score(
        session["candidate_id"]
    )
    events = get_event_summary(
        session["candidate_id"]
    )

    return render_template(
    "exam_report.html",
    report=report,
    integrity=result,
    events=events,
    candidate_name=session["candidate_name"],
    candidate_email=session["candidate_email"],
    duration=calculate_session_duration(report)
)

@app.route("/download-report")
def download_report():

    if "candidate_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    report = connection.execute(
        """
        SELECT *
        FROM exam_sessions
        WHERE candidate_id=?
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()

    connection.close()

    integrity = calculate_integrity_score(
        session["candidate_id"]
    )

    events = get_event_summary(
        session["candidate_id"]
    )

    duration = calculate_session_duration(report)

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(

    Paragraph(
        "<b><font size=18 color='#753B59'>ONLINE EXAMINATION MONITORING SYSTEM</font></b>",
        styles["Title"]
    )

    )

    elements.append(

        Paragraph(
            "<b>Integrity Report</b>",
            styles["Heading2"]
        )

    )

    elements.append(Spacer(1, 0.30 * inch))

    elements.append(

    Paragraph(
        "<b>Candidate Details</b>",
        styles["Heading2"]
    )

    )

    candidate_table = Table(

        [

            ["Candidate ID", report["candidate_id"]],

            ["Candidate Name", session["candidate_name"]],

            ["Email", session["candidate_email"]]

        ],

        colWidths=[2.2*inch,4*inch]

    )

    candidate_table.setStyle(

        TableStyle([

            ("GRID",(0,0),(-1,-1),1,colors.grey),

            ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#753B59")),

            ("TEXTCOLOR",(0,0),(0,-1),colors.white),

            ("FONTNAME",(0,0),(-1,-1),"Helvetica"),

            ("BOTTOMPADDING",(0,0),(-1,-1),8)

        ])

        )

    elements.append(candidate_table)

    elements.append(Spacer(1,0.30*inch))

    elements.append(

        Paragraph(
            "<b>Session Details</b>",
            styles["Heading2"]
        )

    )

    session_table = Table(

        [

            ["Session ID", str(report["session_id"])],

            ["Start Time", report["start_time"]],

            ["End Time", report["end_time"]],

            ["Duration", duration]

        ],

        colWidths=[2.2*inch,4*inch]

    )

    session_table.setStyle(

        TableStyle([

            ("GRID",(0,0),(-1,-1),1,colors.grey),

            ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#753B59")),

            ("TEXTCOLOR",(0,0),(0,-1),colors.white),

            ("BOTTOMPADDING",(0,0),(-1,-1),8)

        ])

    )

    elements.append(session_table)

    elements.append(Spacer(1,0.30*inch))

    elements.append(

    Paragraph(
        "<b>Integrity Score</b>",
        styles["Heading2"]
    )

    )

    score_table = Table(

        [

            ["Final Score", f"{integrity['score']} / 100"],

            ["Remark", integrity["remark"]]

        ],

        colWidths=[2.2*inch,4*inch]

    )

    score_table.setStyle(

        TableStyle([

            ("GRID",(0,0),(-1,-1),1,colors.grey),

            ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#753B59")),

            ("TEXTCOLOR",(0,0),(0,-1),colors.white),

            ("BOTTOMPADDING",(0,0),(-1,-1),8)

        ])

    )

    elements.append(score_table)

    elements.append(Spacer(1,0.30*inch))

    elements.append(

    Paragraph(
        "<b>Monitoring Statistics</b>",
        styles["Heading2"]
    )

    )

    monitoring_table = Table(

        [

            ["Face Not Detected", str(integrity["face_absence"])],

            ["Browser Focus Lost", str(integrity["browser_focus"])],

            ["Multiple Faces Detected", str(integrity["multiple_faces"])],

            ["Total Suspicious Events", str(integrity["total_events"])]

        ],

        colWidths=[3.5*inch,2.5*inch]

    )

    monitoring_table.setStyle(

        TableStyle([

            ("GRID",(0,0),(-1,-1),1,colors.grey),

            ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#753B59")),

            ("TEXTCOLOR",(0,0),(0,-1),colors.white),

            ("BOTTOMPADDING",(0,0),(-1,-1),8),

            ("ALIGN",(1,0),(1,-1),"CENTER")

        ])

    )

    elements.append(monitoring_table)

    elements.append(Spacer(1,0.30*inch))

    elements.append(

    Paragraph(
        "<b>Event Summary</b>",
        styles["Heading2"]
    )

    )

    event_data = [

        ["Event Type", "Timestamp", "Penalty"]

    ]

    for event in events:

        event_data.append([

            event["event_type"],

            event["timestamp"],

            f"-{event['deduction']}"

            ])

        event_table = Table(

            event_data,

            colWidths=[2.6*inch,2.8*inch,0.8*inch]

        )

        event_table.setStyle(

            TableStyle([

                ("GRID",(0,0),(-1,-1),1,colors.grey),

                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#753B59")),

                ("TEXTCOLOR",(0,0),(-1,0),colors.white),

                ("ALIGN",(2,1),(2,-1),"CENTER"),

                ("BOTTOMPADDING",(0,0),(-1,-1),8)

            ])

        )

        elements.append(event_table)

        elements.append(Spacer(1,0.25*inch))

    document.build(elements)

    buffer.seek(0)

    return send_file(

        buffer,

        as_attachment=True,

        download_name="Integrity_Report.pdf",

        mimetype="application/pdf"

    )

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for("login"))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)

@app.route("/admin-dashboard")
@app.route("/admin-dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    total_candidates = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM candidates
        """
    ).fetchone()["total"]

    active_sessions = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM exam_sessions
        WHERE end_time IS NULL
        """
    ).fetchone()["total"]

    completed_sessions = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM exam_sessions
        WHERE end_time IS NOT NULL
        """
    ).fetchone()["total"]

    average_score = connection.execute(
        """
        SELECT ROUND(AVG(integrity_score),2) AS avg_score
        FROM exam_sessions
        """
    ).fetchone()["avg_score"]

    total_events = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM event_logs
        """
    ).fetchone()["total"]

        # Face Not Detected Events
    face_events = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM event_logs
        WHERE event_type='Face Not Detected'
        """
    ).fetchone()["total"]

    # Browser Focus Lost Events
    browser_events = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM event_logs
        WHERE event_type='Browser Focus Lost'
        """
    ).fetchone()["total"]

    # Multiple Faces Events
    multiple_face_events = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM event_logs
        WHERE event_type='Multiple Faces Detected'
        """
    ).fetchone()["total"]

    # Highest Integrity Score
    highest_score = connection.execute(
        """
        SELECT MAX(integrity_score) AS score
        FROM exam_sessions
        """
    ).fetchone()["score"]

    # Lowest Integrity Score
    lowest_score = connection.execute(
        """
        SELECT MIN(integrity_score) AS score
        FROM exam_sessions
        """
    ).fetchone()["score"]

    connection.close()

    print("Total Candidates:", total_candidates)
    print("Active Sessions:", active_sessions)
    print("Completed Sessions:", completed_sessions)
    print("Average Score:", average_score)
    print("Total Events:", total_events)
    print("Face Events :", face_events)
    print("Browser Events :", browser_events)
    print("Multiple Face Events :", multiple_face_events)
    print("Highest Score :", highest_score)
    print("Lowest Score :", lowest_score)

    return render_template(

    "admin_dashboard.html",

    total_candidates=total_candidates,

    active_sessions=active_sessions,

    completed_sessions=completed_sessions,

    average_score=average_score,

    total_events=total_events,

    face_events=face_events,

    browser_events=browser_events,

    multiple_face_events=multiple_face_events,

    highest_score=highest_score,

    lowest_score=lowest_score

)

@app.route("/event-logs")
def event_logs():

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    candidate_id = request.args.get("candidate_id", "")
    event_type = request.args.get("event_type", "")
    event_date = request.args.get("event_date", "")

    connection = get_db_connection()

    query = """
        SELECT
            event_logs.*,
            candidates.name AS candidate_name
        FROM event_logs
        JOIN candidates
        ON event_logs.candidate_id = candidates.candidate_id
        WHERE 1=1
    """

    parameters = []

    if candidate_id:

        query += " AND event_logs.candidate_id=?"

        parameters.append(candidate_id)

    if event_type:

        query += " AND event_logs.event_type=?"

        parameters.append(event_type)

    if event_date:

        query += " AND DATE(event_logs.timestamp)=?"

        parameters.append(event_date)

    query += " ORDER BY timestamp DESC"

    events = connection.execute(

        query,

        parameters

    ).fetchall()

    connection.close()

    return render_template(

        "event_logs.html",

        events=events

    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True, use_reloader=False)