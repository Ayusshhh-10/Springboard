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

import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify, send_file, Response

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
    get_event_summary,
    get_event_summary_for_session
)
from utils.integrity_score import (
    calculate_integrity_score,
    calculate_integrity_score_for_session,
    EVENT_WEIGHTS,
    RISK_THRESHOLD_LOW,
    RISK_THRESHOLD_MEDIUM
)

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

    "current_datetime": datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    ),

    "session_timer": calculate_session_duration(
        current_session
    ),

    "multiple_face_count": multiple_face_count,
    "multiple_face_status": monitoring_data[
        "multiple_face_status"
    ],

    # Existing score
    "integrity_score": integrity["score"],

    # New Pandas scoring information
    "risk_label": integrity["risk_label"],
    "face_presence_ratio": integrity[
        "face_presence_ratio"
    ],
    "total_deduction": integrity[
        "total_deduction"
    ]
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
@app.route("/exam-report/<int:session_id>")
def exam_report(session_id=None):
    if "admin" not in session and "candidate_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    if session_id:
        report = connection.execute(
            """
            SELECT exam_sessions.*, candidates.name AS candidate_name, candidates.email AS candidate_email, candidates.photo_path
            FROM exam_sessions
            JOIN candidates ON exam_sessions.candidate_id = candidates.candidate_id
            WHERE exam_sessions.session_id = ?
            """,
            (session_id,)
        ).fetchone()
    else:
        candidate_id = session.get("candidate_id")
        report = connection.execute(
            """
            SELECT exam_sessions.*, candidates.name AS candidate_name, candidates.email AS candidate_email, candidates.photo_path
            FROM exam_sessions
            JOIN candidates ON exam_sessions.candidate_id = candidates.candidate_id
            WHERE exam_sessions.candidate_id = ?
            ORDER BY exam_sessions.session_id DESC
            LIMIT 1
            """,
            (candidate_id,)
        ).fetchone()

    connection.close()

    if not report:
        flash("Exam report not found.")
        return redirect(url_for("admin_dashboard") if "admin" in session else url_for("dashboard"))

    if session_id:
        result = calculate_integrity_score_for_session(session_id)
        events = get_event_summary_for_session(report["candidate_id"], report["start_time"], report["end_time"])
    else:
        result = calculate_integrity_score(session["candidate_id"])
        events = get_event_summary(session["candidate_id"])

    candidate_name = report["candidate_name"] if "candidate_name" in report.keys() else session.get("candidate_name", "Candidate")
    candidate_email = report["candidate_email"] if "candidate_email" in report.keys() else session.get("candidate_email", "")

    return render_template(
        "exam_report.html",
        report=report,
        integrity=result,
        events=events,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        duration=calculate_session_duration(report)
    )

@app.route("/download-report")
@app.route("/download-report/<int:session_id>")
def download_report(session_id=None):
    if "admin" not in session and "candidate_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    if session_id:
        report = connection.execute(
            """
            SELECT exam_sessions.*, candidates.name AS candidate_name, candidates.email AS candidate_email, candidates.photo_path
            FROM exam_sessions
            JOIN candidates ON exam_sessions.candidate_id = candidates.candidate_id
            WHERE exam_sessions.session_id = ?
            """,
            (session_id,)
        ).fetchone()
    else:
        candidate_id = session.get("candidate_id")
        report = connection.execute(
            """
            SELECT exam_sessions.*, candidates.name AS candidate_name, candidates.email AS candidate_email, candidates.photo_path
            FROM exam_sessions
            JOIN candidates ON exam_sessions.candidate_id = candidates.candidate_id
            WHERE exam_sessions.candidate_id = ?
            ORDER BY exam_sessions.session_id DESC
            LIMIT 1
            """,
            (candidate_id,)
        ).fetchone()

    connection.close()

    if not report:
        flash("Exam report not found.")
        return redirect(url_for("admin_dashboard") if "admin" in session else url_for("dashboard"))

    if session_id:
        integrity = calculate_integrity_score_for_session(session_id)
        events = get_event_summary_for_session(report["candidate_id"], report["start_time"], report["end_time"])
    else:
        integrity = calculate_integrity_score(session["candidate_id"])
        events = get_event_summary(session["candidate_id"])

    candidate_id = report["candidate_id"]
    candidate_name = report["candidate_name"] if "candidate_name" in report.keys() else session.get("candidate_name", "Candidate")
    candidate_email = report["candidate_email"] if "candidate_email" in report.keys() else session.get("candidate_email", "")
    duration = calculate_session_duration(report)

    from reportlab.lib.styles import ParagraphStyle

    buffer = io.BytesIO()

    # Create document with custom margins (40 pt)
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom styles & colors
    primary_color = colors.HexColor("#0f172a")   # Slate-900
    text_color = colors.HexColor("#334155")      # Slate-700
    border_color = colors.HexColor("#e2e8f0")    # Slate-200
    bg_light = colors.HexColor("#f8fafc")        # Slate-50

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        alignment=0, # Left aligned
        spaceAfter=5
    )

    h2_style = ParagraphStyle(
        'DocHeading2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )

    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569")
    )

    value_style = ParagraphStyle(
        'ValueStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a")
    )

    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    cell_header_style = ParagraphStyle(
        'CellHeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    elements = []

    # Title & Subtitle Header
    elements.append(Paragraph("ONLINE EXAMINATION MONITORING SYSTEM", title_style))
    elements.append(Paragraph("<b>Integrity Report</b>", ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#64748b"), spaceAfter=10)))
    
    # Accent divider line under header
    line_table = Table([[""]], colWidths=[515])
    line_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1.5, primary_color),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0)
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 15))

    # Candidate details nested table
    cand_data = [
        [Paragraph("<b>Candidate Details</b>", ParagraphStyle('HCard', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.white)), ""],
        [Paragraph("Candidate ID", label_style), Paragraph(candidate_id, value_style)],
        [Paragraph("Name", label_style), Paragraph(candidate_name, value_style)],
        [Paragraph("Email", label_style), Paragraph(candidate_email, value_style)]
    ]
    cand_table = Table(cand_data, colWidths=[80, 170])
    cand_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, border_color)
    ]))

    # Session details nested table
    sess_data = [
        [Paragraph("<b>Session Details</b>", ParagraphStyle('HCard2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.white)), ""],
        [Paragraph("Session ID", label_style), Paragraph(f"#{report['session_id']}", value_style)],
        [Paragraph("Start Time", label_style), Paragraph(report["start_time"], value_style)],
        [Paragraph("End Time", label_style), Paragraph(report["end_time"] if report["end_time"] else "N/A", value_style)],
        [Paragraph("Duration", label_style), Paragraph(duration, value_style)]
    ]
    sess_table = Table(sess_data, colWidths=[70, 180])
    sess_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, border_color)
    ]))

    # Combine Candidate and Session details side-by-side
    details_layout = Table([[cand_table, "", sess_table]], colWidths=[250, 15, 250])
    details_layout.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(details_layout)
    elements.append(Spacer(1, 10))

    # Integrity Score dynamic color coding block
    score_val = integrity["score"]
    remark_val = integrity["remark"]
    
    if score_val >= 90:
        score_bg = colors.HexColor("#f0fdf4")         # Emerald-50
        score_border = colors.HexColor("#16a34a")     # Emerald-500
        score_text_color = colors.HexColor("#15803d") # Emerald-700
    elif score_val >= 75:
        score_bg = colors.HexColor("#fef9c3")         # Yellow-50
        score_border = colors.HexColor("#eab308")     # Yellow-500
        score_text_color = colors.HexColor("#a16207") # Yellow-700
    elif score_val >= 50:
        score_bg = colors.HexColor("#ffedd5")         # Orange-50
        score_border = colors.HexColor("#f97316")     # Orange-500
        score_text_color = colors.HexColor("#c2410c") # Orange-700
    else:
        score_bg = colors.HexColor("#fee2e2")         # Red-50
        score_border = colors.HexColor("#ef4444")     # Red-500
        score_text_color = colors.HexColor("#b91c1c") # Red-700

    score_num_style = ParagraphStyle(
        'ScoreNum',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=30,
        leading=34,
        textColor=score_text_color,
        alignment=1
    )
    score_lbl_style = ParagraphStyle(
        'ScoreLbl',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )

    score_box_data = [
        [
            Paragraph(f"{score_val}", score_num_style),
            Paragraph("<b>Security Integrity Status</b>", ParagraphStyle('SI_Title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=primary_color))
        ],
        [
            Paragraph("INTEGRITY SCORE", score_lbl_style),
            Paragraph(f"<b>Assessment Remark:</b> <font color='{score_border.hexval()}'><b>{remark_val}</b></font> &nbsp;|&nbsp; <b>Risk Label:</b> {integrity['risk_label']} &nbsp;|&nbsp; <b>Face Presence Ratio:</b> {integrity['face_presence_ratio']}%<br/>The score is calculated based on system infraction logs. A score below 75 points requires a manual overview of candidate video proof snapshots.", ParagraphStyle('SI_Desc', parent=styles['Normal'], fontSize=9, leading=13, textColor=text_color))
        ]
    ]
    score_box_table = Table(score_box_data, colWidths=[110, 405])
    score_box_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (0, 1)),
        ('BACKGROUND', (0, 0), (-1, -1), score_bg),
        ('BOX', (0, 0), (-1, -1), 1.5, score_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(Paragraph("<b>Integrity Score Card</b>", h2_style))
    elements.append(score_box_table)
    elements.append(Spacer(1, 10))

    # Monitoring Statistics
    stat_box_style_lbl = ParagraphStyle(
        'StatLbl',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b"),
        alignment=1
    )
    stat_box_style_val = ParagraphStyle(
        'StatVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=13,
        textColor=primary_color,
        alignment=1
    )
    
    stats_data = [
        [
            Paragraph("FACE ABSENCES", stat_box_style_lbl),
            Paragraph("FOCUS LOSSES", stat_box_style_lbl),
            Paragraph("MULTIPLE FACES", stat_box_style_lbl),
            Paragraph("TOTAL EVENTS", stat_box_style_lbl),
            Paragraph("FACE PRESENCE", stat_box_style_lbl),
            Paragraph("RISK LEVEL", stat_box_style_lbl)
        ],
        [
            Paragraph(f"{integrity['face_absence']} times", stat_box_style_val),
            Paragraph(f"{integrity['browser_focus']} times", stat_box_style_val),
            Paragraph(f"{integrity['multiple_faces']} times", stat_box_style_val),
            Paragraph(f"<b>{integrity['total_events']}</b>", ParagraphStyle('StatValTot', parent=stat_box_style_val, textColor=score_border)),
            Paragraph(f"{integrity['face_presence_ratio']}%", stat_box_style_val),
            Paragraph(f"<b>{integrity['risk_label']}</b>", ParagraphStyle('RiskVal', parent=stat_box_style_val, textColor=score_text_color))
        ]
    ]
    stats_table = Table(stats_data, colWidths=[85, 86, 86, 86, 86, 86])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    
    elements.append(Paragraph("<b>Monitoring Infraction Summary</b>", h2_style))
    elements.append(stats_table)
    elements.append(Spacer(1, 10))

    # Detailed Event Log
    elements.append(Paragraph("<b>Detailed Event Log</b>", h2_style))
    
    if len(events) > 0:
        event_data = [
            [
                Paragraph("<b>Event Type</b>", cell_header_style),
                Paragraph("<b>Timestamp</b>", cell_header_style),
                Paragraph("<b>Deduction</b>", cell_header_style),
                Paragraph("<b>Deduction Score</b>", cell_header_style),
                Paragraph("<b>Proof Image</b>", cell_header_style)
            ]
        ]
        
        for event in events:
            ev_type = event["event_type"]
            if "Lost" in ev_type or "Not Detected" in ev_type or "Absence" in ev_type:
                badge_color = "#ef4444"
            elif "Regained" in ev_type:
                badge_color = "#10b981"
            else:
                badge_color = "#f59e0b"
                
            type_para = Paragraph(f"<font color='{badge_color}'><b>{ev_type}</b></font>", cell_style)
            time_para = Paragraph(event["timestamp"], cell_style)
            
            penalty_val = event["penalty"]
            deduction_val = event.get("deduction", abs(penalty_val))
            if penalty_val and penalty_val < 0:
                penalty_str = f"<font color='#ef4444'><b>-{deduction_val}</b></font>"
            elif deduction_val > 0:
                penalty_str = f"<font color='#ef4444'><b>-{deduction_val}</b></font>"
            else:
                penalty_str = "<font color='#64748b'>0</font>"
            penalty_para = Paragraph(penalty_str, ParagraphStyle('PenStyle', parent=cell_style, alignment=1))
            
            # Deduction Score / Running Score column
            running_score_val = event.get("running_score", 100)
            running_score_str = f"<b>{running_score_val}</b>"
            running_score_para = Paragraph(running_score_str, ParagraphStyle('ScoreStyle', parent=cell_style, alignment=1))
            
            # Proof image thumbnail
            proof_element = Paragraph("<font color='#94a3b8'><i>No Image</i></font>", cell_style)
            if event["proof_image"]:
                img_full_path = os.path.join("static", event["proof_image"])
                if os.path.exists(img_full_path):
                    try:
                        img_flowable = Image(img_full_path, width=80, height=60)
                        proof_element = img_flowable
                    except Exception as e:
                        print(f"Error rendering image in PDF: {e}")
                        proof_element = Paragraph("<font color='#ef4444'>Image Error</font>", cell_style)
            
            event_data.append([type_para, time_para, penalty_para, running_score_para, proof_element])
            
        event_table = Table(event_data, colWidths=[135, 120, 55, 85, 120])
        
        table_style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('ALIGN', (2, 0), (3, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, border_color),
            ('BOX', (0, 0), (-1, -1), 1, border_color)
        ]
        
        for i in range(1, len(event_data)):
            if i % 2 == 0:
                table_style_commands.append(('BACKGROUND', (0, i), (-1, i), bg_light))
            else:
                table_style_commands.append(('BACKGROUND', (0, i), (-1, i), colors.white))
                
        event_table.setStyle(TableStyle(table_style_commands))
        elements.append(event_table)
    else:
        no_events_style = ParagraphStyle(
            'NoEventsStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0f766e"),
            alignment=1
        )
        no_events_data = [
            [Paragraph("<b>No suspicious events were recorded during this examination session.</b>", no_events_style)]
        ]
        no_events_table = Table(no_events_data, colWidths=[515])
        no_events_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ccfbf1")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#99f6e4")),
            ('TOPPADDING', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        elements.append(no_events_table)

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
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    # 1. Total Candidates count
    total_candidates = connection.execute(
        "SELECT COUNT(*) AS total FROM candidates"
    ).fetchone()["total"]

    # 2. Query all sessions joined with candidates
    raw_sessions = connection.execute(
        """
        SELECT
            exam_sessions.session_id,
            exam_sessions.candidate_id,
            exam_sessions.start_time,
            exam_sessions.end_time,
            exam_sessions.status,
            exam_sessions.integrity_score AS db_score,
            candidates.name AS candidate_name,
            candidates.email AS candidate_email,
            candidates.photo_path
        FROM exam_sessions
        JOIN candidates ON exam_sessions.candidate_id = candidates.candidate_id
        ORDER BY exam_sessions.session_id DESC
        """
    ).fetchall()

    sessions_list = []
    for s in raw_sessions:
        session_id = s["session_id"]
        integrity = calculate_integrity_score_for_session(session_id)
        duration_str = calculate_session_duration(s)
        start_time_str = s["start_time"] or ""
        end_time_str = s["end_time"] or ""
        exam_date = start_time_str.split(" ")[0] if start_time_str else ""
        exam_time = start_time_str.split(" ")[1] if " " in start_time_str else ""

        # Normalize status
        if s["status"] in ("Ended", "Completed") or s["end_time"]:
            status_label = "Completed"
            status_code = "completed"
        elif s["status"] == "Paused":
            status_label = "Paused"
            status_code = "paused"
        else:
            status_label = "Active"
            status_code = "active"

        # Check proof
        proof_row = connection.execute(
            """
            SELECT proof_image
            FROM event_logs
            WHERE candidate_id = ? AND timestamp >= ? AND proof_image IS NOT NULL AND proof_image != ''
            ORDER BY event_id DESC
            LIMIT 1
            """,
            (s["candidate_id"], start_time_str)
        ).fetchone()

        sessions_list.append({
            "session_id": session_id,
            "candidate_id": s["candidate_id"],
            "candidate_name": s["candidate_name"],
            "candidate_email": s["candidate_email"],
            "candidate_photo": s["photo_path"] or "uploads/candidate_photos/default.jpg",
            "start_time": start_time_str,
            "end_time": end_time_str,
            "exam_date": exam_date,
            "exam_time": exam_time,
            "duration": duration_str,
            "status": status_label,
            "status_code": status_code,
            "integrity_score": integrity["score"],
            "risk_label": integrity["risk_label"],
            "remark": integrity["remark"],
            "face_presence_ratio": integrity["face_presence_ratio"],
            "face_absence_count": integrity["face_absence"],
            "browser_focus_loss_count": integrity["browser_focus"],
            "multiple_face_count": integrity["multiple_faces"],
            "total_suspicious_events": integrity["total_events"],
            "has_proof": bool(proof_row and proof_row["proof_image"]),
            "sample_proof": proof_row["proof_image"] if proof_row else None
        })

    # Summary Statistics
    total_sessions = len(sessions_list)
    active_sessions = sum(1 for s in sessions_list if s["status_code"] == "active")
    completed_sessions = sum(1 for s in sessions_list if s["status_code"] == "completed")

    scores_list = [s["integrity_score"] for s in sessions_list] if sessions_list else [100]
    average_score = round(sum(scores_list) / len(scores_list), 2) if sessions_list else 100.0
    highest_score = max(scores_list) if scores_list else 100
    lowest_score = min(scores_list) if scores_list else 100

    low_risk_count = sum(1 for s in sessions_list if s["risk_label"] == "Low Risk")
    medium_risk_count = sum(1 for s in sessions_list if s["risk_label"] == "Medium Risk")
    high_risk_count = sum(1 for s in sessions_list if s["risk_label"] == "High Risk")

    total_events = connection.execute("SELECT COUNT(*) AS total FROM event_logs").fetchone()["total"]
    face_events = connection.execute("SELECT COUNT(*) AS total FROM event_logs WHERE event_type='Face Not Detected'").fetchone()["total"]
    browser_events = connection.execute("SELECT COUNT(*) AS total FROM event_logs WHERE event_type='Browser Focus Lost'").fetchone()["total"]
    multiple_face_events = connection.execute("SELECT COUNT(*) AS total FROM event_logs WHERE event_type='Multiple Faces Detected'").fetchone()["total"]

    # Needs Attention List (High Risk and Medium Risk students only, excluding Low Risk)
    needs_attention_sessions = [
        s for s in sessions_list
        if s["risk_label"] in ("High Risk", "Medium Risk")
    ]
    needs_attention_sessions.sort(key=lambda s: (s["integrity_score"], -s["total_suspicious_events"]))

    connection.close()

    return render_template(
        "admin_dashboard.html",
        total_candidates=total_candidates,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        completed_sessions=completed_sessions,
        average_score=average_score,
        highest_score=highest_score,
        lowest_score=lowest_score,
        total_events=total_events,
        face_events=face_events,
        browser_events=browser_events,
        multiple_face_events=multiple_face_events,
        low_risk_count=low_risk_count,
        medium_risk_count=medium_risk_count,
        high_risk_count=high_risk_count,
        sessions=sessions_list,
        needs_attention=needs_attention_sessions
    )


@app.route("/admin/session/<int:session_id>/details")
def admin_session_details(session_id):
    if "admin" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    connection = get_db_connection()
    session_row = connection.execute(
        """
        SELECT
            exam_sessions.*,
            candidates.name AS candidate_name,
            candidates.email AS candidate_email,
            candidates.photo_path
        FROM exam_sessions
        JOIN candidates ON exam_sessions.candidate_id = candidates.candidate_id
        WHERE exam_sessions.session_id = ?
        """,
        (session_id,)
    ).fetchone()

    if not session_row:
        connection.close()
        return jsonify({"success": False, "message": "Session not found"}), 404

    integrity = calculate_integrity_score_for_session(session_id)
    events_summary = get_event_summary_for_session(
        session_row["candidate_id"],
        session_row["start_time"],
        session_row["end_time"]
    )
    duration_str = calculate_session_duration(session_row)

    proofs = [ev["proof_image"] for ev in events_summary if ev.get("proof_image")]

    connection.close()

    return jsonify({
        "success": True,
        "session_id": session_id,
        "candidate_id": session_row["candidate_id"],
        "candidate_name": session_row["candidate_name"],
        "candidate_email": session_row["candidate_email"],
        "candidate_photo": session_row["photo_path"] or "uploads/candidate_photos/default.jpg",
        "start_time": session_row["start_time"],
        "end_time": session_row["end_time"] or "In Progress",
        "duration": duration_str,
        "status": session_row["status"],
        "integrity_score": integrity["score"],
        "risk_label": integrity["risk_label"],
        "remark": integrity["remark"],
        "face_presence_ratio": integrity["face_presence_ratio"],
        "face_absence_count": integrity["face_absence"],
        "browser_focus_loss_count": integrity["browser_focus"],
        "multiple_face_count": integrity["multiple_faces"],
        "total_suspicious_events": integrity["total_events"],
        "total_deduction": integrity["total_deduction"],
        "events": events_summary,
        "proofs": proofs
    })


@app.route("/admin/export-sessions-csv", methods=["GET", "POST"])
@app.route("/download-report-csv", methods=["GET", "POST"])
@app.route("/download-report-csv/<int:session_id>")
def export_sessions_csv(session_id=None):
    if "admin" not in session and "candidate_id" not in session:
        return redirect(url_for("login"))

    selected_ids = []
    if session_id:
        selected_ids = [session_id]
    elif request.method == "POST":
        ids_str = request.form.get("session_ids") or (request.json.get("session_ids", "") if request.is_json else "")
        if ids_str:
            selected_ids = [int(x.strip()) for x in str(ids_str).split(",") if x.strip().isdigit()]
    elif request.method == "GET":
        ids_str = request.args.get("session_ids", "")
        if ids_str:
            selected_ids = [int(x.strip()) for x in str(ids_str).split(",") if x.strip().isdigit()]

    connection = get_db_connection()

    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        query = f"""
            SELECT
                exam_sessions.session_id,
                exam_sessions.candidate_id,
                exam_sessions.start_time,
                exam_sessions.end_time,
                exam_sessions.status,
                candidates.name AS candidate_name
            FROM exam_sessions
            JOIN candidates ON exam_sessions.candidate_id = candidates.candidate_id
            WHERE exam_sessions.session_id IN ({placeholders})
            ORDER BY exam_sessions.session_id DESC
        """
        raw_sessions = connection.execute(query, selected_ids).fetchall()
    else:
        query = """
            SELECT
                exam_sessions.session_id,
                exam_sessions.candidate_id,
                exam_sessions.start_time,
                exam_sessions.end_time,
                exam_sessions.status,
                candidates.name AS candidate_name
            FROM exam_sessions
            JOIN candidates ON exam_sessions.candidate_id = candidates.candidate_id
            ORDER BY exam_sessions.session_id DESC
        """
        raw_sessions = connection.execute(query).fetchall()

    connection.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Candidate Name",
        "Candidate ID",
        "Session ID",
        "Date",
        "Start Time",
        "End Time",
        "Session Duration",
        "Integrity Score",
        "Risk Label",
        "Face Presence Ratio (%)",
        "Face Absence Events",
        "Browser Focus Loss Events",
        "Multiple Face Events",
        "Total Suspicious Events"
    ])

    for s in raw_sessions:
        sid = s["session_id"]
        integrity = calculate_integrity_score_for_session(sid)
        duration_str = calculate_session_duration(s)
        start_time_str = s["start_time"] or ""
        end_time_str = s["end_time"] or ""
        exam_date = start_time_str.split(" ")[0] if start_time_str else ""

        writer.writerow([
            s["candidate_name"],
            s["candidate_id"],
            sid,
            exam_date,
            start_time_str,
            end_time_str,
            duration_str,
            integrity["score"],
            integrity["risk_label"],
            f"{integrity['face_presence_ratio']}%",
            integrity["face_absence"],
            integrity["browser_focus"],
            integrity["multiple_faces"],
            integrity["total_events"]
        ])

    csv_data = output.getvalue()
    filename = f"integrity_exam_sessions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
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