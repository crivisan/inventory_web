import sqlite3, hashlib
from core.database import get_connection

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password, role="user"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, hash_password(password), role))
    conn.commit()
    conn.close()

def verify_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, hash_password(password)))
    user = cur.fetchone()
    conn.close()
    return user
