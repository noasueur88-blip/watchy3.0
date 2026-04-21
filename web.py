from flask import Flask, render_template, request, redirect, session
import sqlite3
import secrets
import time
import os
import requests

# =========================
# APP INIT (FIX IMPORTANT)
# =========================
app = Flask(__name__)
app.secret_key = "supersecretkey"

# =========================
# DISCORD OAUTH
# =========================
CLIENT_ID = "1495598588406005911"
CLIENT_SECRET = "lVpvT0iMAap-ZVUOhObChvs-CNywnIvb"  # ⚠️ ne jamais leak en public
REDIRECT_URI = "https://watchy3-0.onrender.com/callback"
DISCORD_API = "https://discord.com/api"

# =========================
# ADMIN SYSTEM
# =========================
ADMIN_IDS = []  # tu peux ajouter tes IDs Discord ici

# =========================
# PASSWORD FALLBACK (optionnel)
# =========================
PASSWORD = "admin123"

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
# DISCORD LOGIN ROUTES
# =========================
@app.route("/login/discord")
def login_discord():
    return redirect(
        f"https://discord.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
    )


@app.route("/callback")
def callback():
    code = request.args.get("code")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(DISCORD_API + "/oauth2/token", data=data, headers=headers)
    token = r.json().get("access_token")

    user = requests.get(
        DISCORD_API + "/users/@me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    session["user_id"] = user["id"]

    # ADMIN CHECK
    if int(user["id"]) not in ADMIN_IDS:
        return "❌ Pas admin"

    return redirect("/")

# =========================
# DASHBOARD
# =========================
@app.route("/", methods=["GET", "POST"])
def index():

    # 🔐 LOGIN CHECK
    if "user_id" not in session:
        return redirect("/login/discord")

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

        expires_at = None
        if days > 0:
            expires_at = int(time.time()) + (days * 86400)

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
    # STATS
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
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
