import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from tools.paths import DB_NAME

# Путь к сессии делаем ЛОКАЛЬНЫМ (создастся в папке проекта)
SESSION_FILE = "session.txt"

def init_auth_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, nickname TEXT UNIQUE, phone TEXT UNIQUE, password TEXT)''')
    conn.commit()

    # Добавляем колонку аватарки, если её ещё нет (для тех, у кого база уже существует)
    cursor.execute("PRAGMA table_info(users)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'avatar' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
        conn.commit()

    conn.close()

def is_user_exists(nickname, phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE nickname = ? OR phone = ?", (nickname, phone))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def register_user(nickname, phone, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (nickname, phone, password) VALUES (?, ?, ?)", (nickname, phone, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError: return False
    finally: conn.close()

def set_user_avatar(nickname, avatar_path):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar = ? WHERE nickname = ?", (avatar_path, nickname))
    conn.commit()
    conn.close()

def get_user_avatar(nickname):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT avatar FROM users WHERE nickname = ?", (nickname,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def logout_user():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

def login_user(nickname, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, phone FROM users WHERE nickname = ? AND password = ?", (nickname, hashed_pw))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # ЗАПИСЫВАЕМ СЕССИЮ В ЛОКАЛЬНЫЙ ФАЙЛ
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            f.write(f"{user[0]},{user[1]}")
        return True
    return False

def get_current_user():
    if not os.path.exists(SESSION_FILE): return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = f.read().split(",")
            return data # Вернет [nickname, phone]
    except: return None

def check_session_timeout(minutes=0):
    # Если файл сессии есть — считаем, что залогинены
    return not os.path.exists(SESSION_FILE)