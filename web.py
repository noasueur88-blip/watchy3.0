from flask import Flask, render_template, request, redirect
import sqlite3
import secrets
import time

app = Flask(__name__)

PASSWORD = "admin123"  # change ça

def generate_code():
    return secrets.token_hex(4).upper()

def db():
    return sqlite3.connect("codes.db")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        if request.form.get("password") != PASSWORD:
            return "Mot de passe incorrect"

        role_id = int(request.form.get("role"))
        days = int(request.form.get("days"))
        code_type = request.form.get("type")
        user_id = request.form.get("user")

        code = generate_code()

        # type
        if code_type == "unique":
            max_uses = 1
        else:
            max_uses = -1

        # expiration
        expires_at = None
        if days > 0:
            expires_at = int(time.time()) + (days * 86400)

        conn = db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO codes VALUES (?, ?, ?, 0, ?, ?)",
            (code, role_id, max_uses, expires_at, user_id if user_id else None)
        )

        conn.commit()
        conn.close()

        return f"Code créé: {code}"

    conn = db()
    cursor = conn.cursor()

    cursor.execute("SELECT role_id, role_name FROM roles")
    roles = cursor.fetchall()

    conn.close()

    return render_template("index.html", roles=roles)

app.run(port=5000)
