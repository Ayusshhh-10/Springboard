import re
from flask import Flask, render_template, request, redirect, url_for, flash, session
from utils.db import get_db_connection, init_db


app = Flask(__name__)
app.secret_key = "online_exam_secret_key"


def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)


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
        photo_path = ""

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

        flash("Candidate registered successfully. Please login now.")
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
    if "candidate_email" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        candidate_name=session["candidate_name"],
        candidate_email=session["candidate_email"]
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)