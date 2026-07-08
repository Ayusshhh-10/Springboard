from flask import Flask, render_template, request, redirect, url_for, flash
from utils.db import get_db_connection, init_db


app = Flask(__name__)
app.secret_key = "online_exam_secret_key"


@app.route("/")
def home():
    return redirect(url_for("register"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        candidate_id = request.form["candidate_id"]
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        photo_path = ""

        try:
            connection = get_db_connection()
            connection.execute(
                """
                INSERT INTO candidates 
                (candidate_id, name, email, password, photo_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (candidate_id, name, email, password, photo_path),
            )
            connection.commit()
            connection.close()

            flash("Candidate registered successfully.")
            return redirect(url_for("register"))

        except Exception as error:
            flash(f"Registration failed: {error}")
            return redirect(url_for("register"))

    return render_template("registration.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)