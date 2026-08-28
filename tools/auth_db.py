import hashlib
import os
import sqlite3
import time
from datetime import datetime
import uuid as uuid_lib
from tools.paths import DB_NAME
from tools.supabase_client import get_supabase_client, is_supabase_configured, load_json_store, save_json_store
from tools.cache import cache_invalidate

SESSION_FILE = "session.txt"


def _response_data(response):
    return getattr(response, "data", None) or []


def init_auth_db():
    if is_supabase_configured():
        load_json_store("users", default=[])
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (nickname TEXT PRIMARY KEY, password TEXT, phone TEXT, avatar TEXT)''')

    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'created_at' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
        conn.commit()
    if 'last_seen' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_seen REAL")
        conn.commit()

    conn.close()


def update_user_activity(nickname):
    """Обновляет таймштамп последней активности пользователя"""
    if is_supabase_configured():
        try:
            users = load_json_store("users", default=[])
            updated = []
            for row in users:
                if row.get("nickname") == nickname:
                    row = dict(row)
                    row["last_seen"] = time.time()
                updated.append(row)
            if not any(r.get("nickname") == nickname for r in users):
                updated.append({"nickname": nickname, "last_seen": time.time()})
            save_json_store("users", updated)
        except Exception as exc:
            print(f"[Supabase Auth] update_user_activity: {exc}")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_seen = ? WHERE nickname = ?", (time.time(), nickname))
    conn.commit()
    conn.close()


def get_user_last_seen(nickname):
    """Возвращает таймштамп последней активности пользователя"""
    if is_supabase_configured():
        try:
            cache_invalidate("store:users")
            users = load_json_store("users", default=[])
            for row in users:
                if row.get("nickname") == nickname:
                    return row.get("last_seen")
            return None
        except Exception as exc:
            print(f"[Supabase Auth] get_user_last_seen: {exc}")
            return None
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT last_seen FROM users WHERE nickname = ?", (nickname,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def is_user_exists(nickname, phone):
    if is_supabase_configured():
        try:
            users = load_json_store("users", default=[])
            return any((row.get("nickname") == nickname or row.get("phone") == phone) for row in users)
        except Exception as exc:
            print(f"[Supabase Auth] is_user_exists: {exc}")
            return False
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE nickname = ? OR phone = ?", (nickname, phone))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def register_user(nickname, phone, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    user_uuid = str(uuid_lib.uuid4())
    if is_supabase_configured():
        try:
            users = load_json_store("users", default=[])
            if any(row.get("nickname") == nickname or row.get("phone") == phone for row in users):
                return False
            users.append({
                "nickname": nickname,
                "phone": phone,
                "password": hashed_pw,
                "avatar": "👤",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_seen": time.time(),
                "uuid": user_uuid,
            })
            save_json_store("users", users)
            return True
        except Exception as exc:
            print(f"[Supabase Auth] register_user: {exc}")
            return False
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (nickname, phone, password, last_seen) VALUES (?, ?, ?, ?)",
                       (nickname, phone, hashed_pw, time.time()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_or_create_user_uuid(nickname):
    """Возвращает UUID пользователя. Если его ещё нет (старый аккаунт) — создаёт и сохраняет."""
    if is_supabase_configured():
        try:
            users = load_json_store("users", default=[])
            found_uuid = None
            updated = []
            for row in users:
                row = dict(row)
                if row.get("nickname") == nickname:
                    if not row.get("uuid"):
                        row["uuid"] = str(uuid_lib.uuid4())
                    found_uuid = row["uuid"]
                updated.append(row)
            if found_uuid:
                save_json_store("users", updated)
            return found_uuid
        except Exception as exc:
            print(f"[Supabase Auth] get_or_create_user_uuid: {exc}")
            return None
    return None


def set_user_avatar(nickname, avatar_path):
    if is_supabase_configured():
        try:
            users = load_json_store("users", default=[])
            updated = []
            for row in users:
                if row.get("nickname") == nickname:
                    row = dict(row)
                    row["avatar"] = avatar_path
                updated.append(row)
            save_json_store("users", updated)
        except Exception as exc:
            print(f"[Supabase Auth] set_user_avatar: {exc}")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar = ? WHERE nickname = ?", (avatar_path, nickname))
    conn.commit()
    conn.close()


def get_user_avatar(nickname):
    if is_supabase_configured():
        try:
            users = load_json_store("users", default=[])
            for row in users:
                if row.get("nickname") == nickname:
                    return row.get("avatar")
            return None
        except Exception as exc:
            print(f"[Supabase Auth] get_user_avatar: {exc}")
            return None
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT avatar FROM users WHERE nickname = ?", (nickname,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def logout_user():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = f.read().split(",")
                if data:
                    nickname = data[0]
                    if is_supabase_configured():
                        try:
                            update_user_activity(nickname)
                        except Exception as exc:
                            print(f"[Supabase Auth] logout_user: {exc}")
                    else:
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
    if is_supabase_configured():
        try:
            users = load_json_store("users", default=[])
            for row in users:
                if row.get("nickname") == nickname and row.get("password") == hashed_pw:
                    user_uuid = get_or_create_user_uuid(nickname)
                    with open(SESSION_FILE, "w", encoding="utf-8") as f:
                        f.write(f"{row.get('nickname')},{row.get('phone', '')},{user_uuid or ''}")
                    update_user_activity(row.get("nickname"))
                    return True
        except Exception as exc:
            print(f"[Supabase Auth] login_user: {exc}")
            return False
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, phone FROM users WHERE nickname = ? AND password = ?", (nickname, hashed_pw))
    user = cursor.fetchone()
    conn.close()

    if user:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            f.write(f"{user[0]},{user[1]},")
        update_user_activity(user[0])
        return True
    return False


def verify_user_credentials(nickname, phone, password):
    """Проверяет ник, телефон и пароль без изменения текущей сессии."""
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    if is_supabase_configured():
        users = load_json_store("users", default=[])
        return any(
            row.get("nickname") == nickname
            and row.get("phone") == phone
            and row.get("password") == hashed_pw
            for row in users
        )
    conn = sqlite3.connect(DB_NAME)
    row = conn.execute(
        "SELECT 1 FROM users WHERE nickname = ? AND phone = ? AND password = ?",
        (nickname, phone, hashed_pw),
    ).fetchone()
    conn.close()
    return row is not None

def get_current_user():
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = f.read().split(",")
            return data
    except Exception:
        return None


def get_nickname_by_phone(phone):
    """Возвращает nickname по номеру телефона или None"""
    if not phone:
        return None
    if is_supabase_configured():
        try:
            users = load_json_store("users", default=[])
            for row in users:
                if row.get("phone") == phone:
                    return row.get("nickname")
            return None
        except Exception as exc:
            print(f"[Supabase Auth] get_nickname_by_phone: {exc}")
            return None
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT nickname FROM users WHERE phone = ?", (phone,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def check_session_timeout(minutes=0):
    return not os.path.exists(SESSION_FILE)