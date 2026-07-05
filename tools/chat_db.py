import sqlite3
from datetime import datetime
from tools.paths import DB_NAME

def init_chat_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS friend_requests 
                      (id INTEGER PRIMARY KEY, from_user TEXT, to_user TEXT, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS friends 
                      (user1 TEXT, user2 TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages 
                      (id INTEGER PRIMARY KEY, sender TEXT, receiver TEXT, 
                       content BLOB, timestamp TEXT, is_image INTEGER DEFAULT 0, is_read INTEGER DEFAULT 0)''')
    
    cursor.execute("PRAGMA table_info(messages)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'is_read' not in cols:
        cursor.execute("ALTER TABLE messages ADD COLUMN is_read INTEGER DEFAULT 0")
    
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

def send_friend_request(from_nick, to_phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT nickname FROM users WHERE phone = ?", (to_phone,))
    res = cursor.fetchone()
    if not res: return False, "Номер не найден!"
    to_nick = res[0]
    cursor.execute("INSERT INTO friend_requests (from_user, to_user, status) VALUES (?, ?, 'pending')", (from_nick, to_nick))
    conn.commit()
    conn.close()
    return True, f"Заявка для {to_nick} отправлена!"

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
    cursor.execute("UPDATE friend_requests SET status = 'accepted' WHERE from_user = ? AND to_user = ?", (friend_nick, my_nick))
    cursor.execute("INSERT INTO friends (user1, user2) VALUES (?, ?)", (my_nick, friend_nick))
    conn.commit()
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
    if is_image == 0:
        content = content.encode('utf-8')
    cursor.execute("INSERT INTO messages (sender, receiver, content, timestamp, is_image, is_read) VALUES (?, ?, ?, ?, ?, 0)",
                   (sender, receiver, content, datetime.now().strftime("%H:%M"), is_image))
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