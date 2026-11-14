import sqlite3

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            credits INTEGER DEFAULT 5
        )
    """)
    conn.commit()
    conn.close()

def get_credits(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute("INSERT INTO users (user_id, credits) VALUES (?, 5)", (user_id,))
        conn.commit()
        credits = 5
    else:
        credits = row[0]
    conn.close()
    return credits

def use_credit(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = credits - 1 WHERE user_id = ? AND credits > 0", (user_id,))
    conn.commit()
    conn.close()

def add_credits(user_id, amount):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
