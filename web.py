from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import secrets
import time
import os
import requests

app = Flask(__name__)
app.secret_key = "supersecretkey"

# =========================
# DISCORD CONFIG
# =========================
CLIENT_ID = "1495598588406005911"
CLIENT_SECRET = "TON_CLIENT_SECRET"
REDIRECT_URI = "https://watchy3-0.onrender.com/callback"
DISCORD_API = "https://discord.com/api"

BOT_TOKEN = os.getenv("TOKEN")  # token bot

ADMIN_IDS = [1018561026427474121]

# ⚠️ remplace par les vrais serveurs où ton bot est
BOT_GUILDS = []

# =========================
# DB
# =========================
def init_db():
    conn = sqlite3.connect("codes.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS codes (
        code TEXT PRIMARY KEY,
        guild_id INTEGER,
        role_id INTEGER,
        max_uses INTEGER,
        uses INTEGER DEFAULT 0,
        expires_at INTEGER,
        bound_user INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()

def db():
    return sqlite3.connect("codes.db")

def generate_code():
    return secrets.token_hex(4).upper()

# =========================
# LOGIN DISCORD
# =========================
@app.route("/login")
def login():
    return redirect(
        f"https://discord.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
    )

# =========================
# CALLBACK
# =========================
@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
    return redirect("/login")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(DISCORD_API + "/oauth2/token", data=data, headers=headers)
    token_json = r.json()

    access_token = token_json.get("access_token")

    if not access_token:
        return f"❌ Token error: {token_json}"

    # USER
    user = requests.get(
        DISCORD_API + "/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    if "id" not in user:
        return f"❌ User error: {user}"

    # GUILDS
    guilds = requests.get(
        DISCORD_API + "/users/@me/guilds",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    session["user"] = user
    session["guilds"] = guilds

    if int(user["id"]) not in ADMIN_IDS:
        return "❌ Pas admin"

    return redirect("/dashboard")

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:
        return redirect("/login")

    conn = db()
    cursor = conn.cursor()

    user_guilds = session.get("guilds", [])

    # 🔥 filtrer serveurs où bot est présent + admin
    filtered_guilds = [
        g for g in user_guilds
        if int(g["permissions"]) & 0x20  # admin
    ]

    # =========================
    # CREATE CODE
    # =========================
    if request.method == "POST":

        guild_id = int(request.form.get("guild"))
        role_id = int(request.form.get("role"))
        days = int(request.form.get("days") or 0)
        max_uses = int(request.form.get("max_uses") or 1)
        user_id = request.form.get("user")

        code = generate_code()

        expires_at = None
        if days > 0:
            expires_at = int(time.time()) + (days * 86400)

        cursor.execute("""
        INSERT INTO codes
        (code, guild_id, role_id, max_uses, uses, expires_at, bound_user)
        VALUES (?, ?, ?, ?, 0, ?, ?)
        """, (
            code,
            guild_id,
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
    total_codes = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(uses) FROM codes")
    total_uses = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT code, guild_id, role_id, uses
        FROM codes
        ORDER BY ROWID DESC
        LIMIT 20
    """)
    codes = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        guilds=filtered_guilds,
        total_codes=total_codes,
        total_uses=total_uses,
        codes=codes
    )

# =========================
# API ROLES
# =========================
@app.route("/api/roles/<guild_id>")
def get_roles(guild_id):

    headers = {
        "Authorization": f"Bot {BOT_TOKEN}"
    }

    r = requests.get(
        f"https://discord.com/api/guilds/{guild_id}/roles",
        headers=headers
    )

    return jsonify(r.json())

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
