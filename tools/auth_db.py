import sqlite3
import hashlib
import os
import time  # <--- Добавили импорт time для работы с таймштампами
from datetime import datetime, timedelta
from tools.paths import DB_NAME

SESSION_FILE = "session.txt"

def init_auth_db():
    import sqlite3
    from tools.paths import DB_NAME
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Создаем таблицу, если её не было
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (nickname TEXT PRIMARY KEY, password TEXT, phone TEXT, avatar TEXT)''')
    
    # Проверяем, есть ли колонка created_at, и если нет — добавляем её
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'created_at' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
        conn.commit()
    # Проверяем, есть ли колонка last_seen, и если нет — добавляем её
    if 'last_seen' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_seen REAL")
        conn.commit()
        
    conn.close()

# --- Новые функции для работы со статусом ---

def update_user_activity(nickname):
    """Обновляет таймштамп последней активности пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_seen = ? WHERE nickname = ?", (time.time(), nickname))
    conn.commit()
    conn.close()

def get_user_last_seen(nickname):
    """Возвращает таймштамп последней активности пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT last_seen FROM users WHERE nickname = ?", (nickname,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# --- Конец новых функций ---

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
        cursor.execute("INSERT INTO users (nickname, phone, password, last_seen) VALUES (?, ?, ?, ?)", 
                       (nickname, phone, hashed_pw, time.time()))
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
    # При выходе ставим метку last_seen для текущего пользователя, затем удаляем сессию
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = f.read().split(",")
                if data:
                    nickname = data[0]
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET last_seen = ? WHERE nickname = ?", (time.time(), nickname))
                    conn.commit()
                    conn.close()
        except Exception:
            pass
        try:
            os.remove(SESSION_FILE)
        except Exception:
            pass

def login_user(nickname, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, phone FROM users WHERE nickname = ? AND password = ?", (nickname, hashed_pw))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            f.write(f"{user[0]},{user[1]}")
        # Обновляем активность при успешном входе
        update_user_activity(user[0])
        return True
    return False

def get_current_user():
    if not os.path.exists(SESSION_FILE): return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = f.read().split(",")
            return data
    except: return None

def get_nickname_by_phone(phone):
    """Возвращает nickname по номеру телефона или None"""
    if not phone: return None
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT nickname FROM users WHERE phone = ?", (phone,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def check_session_timeout(minutes=0):
    return not os.path.exists(SESSION_FILE)