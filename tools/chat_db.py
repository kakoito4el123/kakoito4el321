import sqlite3
from datetime import datetime
from tools.paths import DB_NAME
from tools.auth_db import get_nickname_by_phone

def init_chat_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS friend_requests 
                      (id INTEGER PRIMARY KEY, from_user TEXT, to_user TEXT, status TEXT)''')
    # friends: хранить пары (user1,user2) без дубликатов. Добавляем UNIQUE
    cursor.execute('''CREATE TABLE IF NOT EXISTS friends 
                      (user1 TEXT, user2 TEXT, UNIQUE(user1,user2))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages 
                      (id INTEGER PRIMARY KEY, sender TEXT, receiver TEXT, 
                       content BLOB, timestamp TEXT, is_image INTEGER DEFAULT 0, is_read INTEGER DEFAULT 0)''')
    
    cursor.execute("PRAGMA table_info(messages)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'is_read' not in cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN is_read INTEGER DEFAULT 0")
    # Убедимся, что timestamp хранится в удобном формате; существующие записи оставляем
    
    conn.commit()
    conn.close()

def delete_message(msg_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

def edit_message(msg_id, new_text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET content = ? WHERE id = ?", (new_text.encode('utf-8'), msg_id))
    conn.commit()
    conn.close()

def mark_as_read(my_nick, friend_nick):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET is_read = 1 WHERE sender = ? AND receiver = ?", (friend_nick, my_nick))
    conn.commit()
    conn.close()

def get_unread_count(my_nick, friend_nick):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE sender = ? AND receiver = ? AND is_read = 0", (friend_nick, my_nick))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def send_friend_request(my_id, target_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Проверяем, не являются ли уже друзьями
    # Разрешаем передавать в target_id либо ник, либо номер телефона
    resolved_target = target_id
    # Попробуем разрешить телефон в ник
    try:
        maybe = get_nickname_by_phone(target_id)
        if maybe:
            resolved_target = maybe
    except Exception:
        resolved_target = target_id

    # Проверим, что такой пользователь существует
    cursor.execute("SELECT 1 FROM users WHERE nickname = ?", (resolved_target,))
    if not cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "Пользователь не найден"}

    cursor.execute("SELECT 1 FROM friends WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)", (my_id, resolved_target, resolved_target, my_id))
    if cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "Вы уже друзья!"}

    # Проверяем, не отправлена ли уже заявка
    cursor.execute("SELECT status FROM friend_requests WHERE from_user=? AND to_user=?", (my_id, resolved_target))
    row = cursor.fetchone()
    if row:
        conn.close()
        return {"status": "error", "message": "Заявка уже отправлена"}

    cursor.execute("INSERT INTO friend_requests (from_user, to_user, status) VALUES (?, ?, 'pending')", (my_id, resolved_target))
    conn.commit()
    conn.close()
    return {"status": "success"}

def delete_friend(my_nick, friend_nick):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM friends WHERE (user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?)", (my_nick, friend_nick, friend_nick, my_nick))
        # Optionally also mark requests between them as rejected
        cursor.execute("UPDATE friend_requests SET status = 'rejected' WHERE (from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?)", (my_nick, friend_nick, friend_nick, my_nick))
        conn.commit()
    finally:
        conn.close()

def get_incoming_requests(my_nick):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT from_user FROM friend_requests WHERE to_user = ? AND status = 'pending'", (my_nick,))
    reqs = [r[0] for r in cursor.fetchall()]
    conn.close()
    return reqs

def accept_friend_request(my_nick, friend_nick):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Пометить все заявки между пользователями как accepted
    cursor.execute("UPDATE friend_requests SET status = 'accepted' WHERE (from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?)", (friend_nick, my_nick, my_nick, friend_nick))
    # Вставляем пару друзей в canonical форме (min,max) чтобы избежать дубликатов зеркал
    a, b = (my_nick, friend_nick)
    try:
        cursor.execute("INSERT OR IGNORE INTO friends (user1, user2) VALUES (?, ?)", (a, b))
    except Exception:
        # Пробуем вставить в обратном порядке, если уникальность отличается
        try:
            cursor.execute("INSERT OR IGNORE INTO friends (user1, user2) VALUES (?, ?)", (b, a))
        except:
            pass
    conn.commit()
    conn.close()

def reject_friend_request(my_nick, friend_nick):
    """Помечает заявку как отклонённую (rejected)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE friend_requests SET status = 'rejected' WHERE from_user = ? AND to_user = ?", (friend_nick, my_nick))
        cursor.execute("UPDATE friend_requests SET status = 'rejected' WHERE from_user = ? AND to_user = ?", (my_nick, friend_nick))
        conn.commit()
    finally:
        conn.close()

def get_friends_list(my_nick):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user2 FROM friends WHERE user1 = ?", (my_nick,))
    f1 = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT user1 FROM friends WHERE user2 = ?", (my_nick,))
    f2 = [r[0] for r in cursor.fetchall()]
    conn.close()
    return list(set(f1 + f2))

def save_message(sender, receiver, content, is_image=0):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Для текста сохраняем как UTF-8 байты; для стабильности записываем полный ISO timestamp
    if is_image == 0 and isinstance(content, str):
        content = content.encode('utf-8')
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO messages (sender, receiver, content, timestamp, is_image, is_read) VALUES (?, ?, ?, ?, ?, 0)",
                   (sender, receiver, content, ts, is_image))
    conn.commit()
    conn.close()

def get_chat_history(user1, user2):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""SELECT sender, content, timestamp, is_image, id FROM messages 
                      WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) 
                      ORDER BY id ASC""", (user1, user2, user2, user1))
    history = cursor.fetchall()
    conn.close()
    return history