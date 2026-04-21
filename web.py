from flask import Flask, render_template, request
import sqlite3
import secrets
import time
import os

app = Flask(__name__)

PASSWORD = "admin123"  # change ça

# =========================
# DB INIT (IMPORTANT FIX)
# =========================
def init_db():
    conn = sqlite3.connect("codes.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS codes (
        code TEXT PRIMARY KEY,
        role_id INTEGER,
        max_uses INTEGER,
        uses INTEGER DEFAULT 0,
        expires_at INTEGER,
        bound_user INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        role_id INTEGER PRIMARY KEY,
        role_name TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# UTILS
# =========================
def generate_code():
    return secrets.token_hex(4).upper()

def db():
    return sqlite3.connect("codes.db")

# =========================
# ROUTE
# =========================
@app.route("/", methods=["GET", "POST"])
def index():

    conn = db()
    cursor = conn.cursor()

    if request.method == "POST":

        if request.form.get("password") != PASSWORD:
            return "❌ Mot de passe incorrect"

        role_id = int(request.form.get("role"))
        days = int(request.form.get("days"))
        code_type = request.form.get("type")
        user_id = request.form.get("user")

        code = generate_code()

        # =========================
        # TYPE CODE
        # =========================
        if code_type == "unique":
            max_uses = 1
        else:
            max_uses = -1  # VIP / lifetime

        # =========================
        # EXPIRATION
        # =========================
        expires_at = None
        if days > 0:
            expires_at = int(time.time()) + (days * 86400)

        cursor.execute(
            "INSERT INTO codes VALUES (?, ?, ?, 0, ?, ?)",
            (
                code,
                role_id,
                max_uses,
                expires_at,
                user_id if user_id else None
            )
        )

        conn.commit()
        conn.close()

        return f"✅ Code créé : {code}"

    # =========================
    # LOAD ROLES
    # =========================
    cursor.execute("SELECT role_id, role_name FROM roles")
    roles = cursor.fetchall()

    conn.close()

    return render_template("index.html", roles=roles)

# =========================
# RUN (Render FIX)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
