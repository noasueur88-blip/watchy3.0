import sqlite3

def get_db():
    return sqlite3.connect("data.db")

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS codes (
        code TEXT,
        guild_id TEXT,
        role_id TEXT,
        used_by TEXT,
        max_uses INTEGER,
        uses INTEGER DEFAULT 0,
        premium INTEGER DEFAULT 0,
        expires_at INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()
