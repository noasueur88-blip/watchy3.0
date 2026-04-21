from flask import Flask, render_template, request
import sqlite3
import secrets
import time
import os

app = Flask(__name__)

PASSWORD = "admin123"  # change ça

# =========================
# DB INIT
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
# DASHBOARD
# =========================
@app.route("/", methods=["GET", "POST"])
def index():

    conn = db()
    cursor = conn.cursor()

    # =========================
    # CREATE CODE
    # =========================
    if request.method == "POST":

        password = request.form.get("password")

        if password != PASSWORD:
            return "❌ Mot de passe incorrect"

        try:
            role_id = int(request.form.get("role"))
        except:
            return "❌ rôle invalide"

        try:
            days = int(request.form.get("days") or 0)
        except:
            days = 0

        try:
            max_uses = int(request.form.get("max_uses") or 1)
        except:
            max_uses = 1

        user_id = request.form.get("user")

        code = generate_code()

        # =========================
        # EXPIRATION
        # =========================
        expires_at = None
        if days > 0:
            expires_at = int(time.time()) + (days * 86400)

        # =========================
        # INSERT SAFE
        # =========================
        cursor.execute("""
        INSERT INTO codes
        (code, role_id, max_uses, uses, expires_at, bound_user)
        VALUES (?, ?, ?, 0, ?, ?)
        """, (
            code,
            role_id,
            max_uses,
            expires_at,
            int(user_id) if user_id else None
        ))

        conn.commit()

    # =========================
    # STATS SAFE
    # =========================
    cursor.execute("SELECT COUNT(*) FROM codes")
    total_codes = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(uses) FROM codes")
    total_uses = cursor.fetchone()[0] or 0

    # =========================
    # ROLES
    # =========================
    cursor.execute("SELECT role_id, role_name FROM roles")
    roles = cursor.fetchall()

    # =========================
    # CODES LIST
    # =========================
    cursor.execute("""
        SELECT code, role_id, max_uses, uses, expires_at
        FROM codes
        ORDER BY ROWID DESC
        LIMIT 20
    """)
    codes = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        roles=roles,
        total_codes=total_codes,
        total_uses=total_uses,
        codes=codes
    )

# =========================
# RUN (RENDER READY)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
