import os
import re
import cv2
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session

from utils.db import get_db_connection, init_db


app = Flask(__name__)
app.secret_key = "online_exam_secret_key"

PHOTO_FOLDER = "uploads/candidate_photos"
os.makedirs(PHOTO_FOLDER, exist_ok=True)


def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)


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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        candidate_id = request.form.get("candidate_id", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not candidate_id or not name or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        if not is_valid_email(email):
            flash("Please enter a valid email address.")
            return redirect(url_for("register"))

        connection = get_db_connection()

        existing_email = connection.execute(
            "SELECT * FROM candidates WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_email:
            connection.close()
            flash("This email is already registered. Please use another email.")
            return redirect(url_for("register"))

        existing_candidate = connection.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?",
            (candidate_id,)
        ).fetchone()

        if existing_candidate:
            connection.close()
            flash("This Candidate ID is already registered. Please use another ID.")
            return redirect(url_for("register"))

        photo_path = capture_candidate_photo(candidate_id)

        if not photo_path:
            connection.close()
            flash("Photo capture failed. Please check your webcam and try again.")
            return redirect(url_for("register"))

        connection.execute(
            """
            INSERT INTO candidates 
            (candidate_id, name, email, password, photo_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (candidate_id, name, email, password, photo_path)
        )

        connection.commit()
        connection.close()

        flash("Candidate registered successfully with photo. Please login now.")
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

            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password. Please try again.")
            return redirect(url_for("login"))

    return render_template("login.html")


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

    return render_template(
        "dashboard.html",
        candidate_name=session["candidate_name"],
        candidate_email=session["candidate_email"],
        current_session=current_session
    )


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
        return redirect(url_for("dashboard"))

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

    flash("Exam session started successfully.")
    return redirect(url_for("dashboard"))


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
        SELECT * FROM exam_sessions
        WHERE candidate_id = ? AND status IN ('Started', 'Paused', 'Resumed')
        ORDER BY session_id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()

    if not active_session:
        connection.close()
        flash("No active exam session found to end.")
        return redirect(url_for("dashboard"))

    connection.execute(
        """
        UPDATE exam_sessions
        SET end_time = ?, status = ?
        WHERE session_id = ?
        """,
        (end_time, "Ended", active_session["session_id"])
    )

    connection.commit()
    connection.close()

    flash("Exam session ended successfully.")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)