import sqlite3
from datetime import datetime

from tools.auth_db import get_nickname_by_phone
from tools.paths import DB_NAME
from tools.supabase_client import get_supabase_client, is_supabase_configured, load_json_store, save_json_store
import base64
from tools.cache import cache_get, cache_set, cache_invalidate
def _response_data(response):
    return getattr(response, "data", None) or []


def _chat_cache_key(user1, user2):
    return f"chat_{min(user1, user2)}_{max(user1, user2)}"


def _invalidate_message_chat(row):
    if row and row.get("sender") and row.get("receiver"):
        cache_invalidate(_chat_cache_key(row.get("sender"), row.get("receiver")))


def init_chat_db():
    if is_supabase_configured():
        load_json_store("friends", default=[])
        load_json_store("friend_requests", default=[])
        load_json_store("messages", default=[])
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS friend_requests
                      (id INTEGER PRIMARY KEY, from_user TEXT, to_user TEXT, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS friends
                      (user1 TEXT, user2 TEXT, UNIQUE(user1,user2))''')
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
    if is_supabase_configured():
        try:
            messages = load_json_store("messages", default=[])
            removed = next((m for m in messages if m.get("id") == msg_id), None)
            filtered = [m for m in messages if m.get("id") != msg_id]
            save_json_store("messages", filtered)
            _invalidate_message_chat(removed)
        except Exception as exc:
            print(f"[Supabase Chat] delete_message: {exc}")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT sender, receiver FROM messages WHERE id = ?", (msg_id,))
    row = cursor.fetchone()
    cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
    if row:
        cache_invalidate(_chat_cache_key(row[0], row[1]))

def edit_message(msg_id, new_text):
    if is_supabase_configured():
        try:
            messages = load_json_store("messages", default=[])
            updated = []
            edited = None
            for m in messages:
                row = dict(m)
                if row.get("id") == msg_id:
                    row["content"] = new_text
                    edited = row
                updated.append(row)
            save_json_store("messages", updated)
            _invalidate_message_chat(edited)
        except Exception as exc:
            print(f"[Supabase Chat] edit_message: {exc}")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT sender, receiver FROM messages WHERE id = ?", (msg_id,))
    row = cursor.fetchone()
    cursor.execute("UPDATE messages SET content = ? WHERE id = ?", (new_text.encode('utf-8'), msg_id))
    conn.commit()
    conn.close()
    if row:
        cache_invalidate(_chat_cache_key(row[0], row[1]))


def mark_as_read(my_nick, friend_nick):
    cache_key = _chat_cache_key(my_nick, friend_nick)
    if is_supabase_configured():
        try:
            messages = load_json_store("messages", default=[])
            updated = []
            changed = False
            for m in messages:
                row = dict(m)
                if row.get("sender") == friend_nick and row.get("receiver") == my_nick and row.get("is_read") != 1:
                    row["is_read"] = 1
                    changed = True
                updated.append(row)
            if changed:
                save_json_store("messages", updated)
            cached = cache_get(cache_key)
            if cached is not None:
                refreshed = []
                for row in cached:
                    if len(row) >= 6 and row[0] == friend_nick:
                        refreshed.append((row[0], row[1], row[2], row[3], row[4], 1))
                    elif len(row) == 5 and row[0] == friend_nick:
                        refreshed.append((row[0], row[1], row[2], row[3], row[4], 1))
                    else:
                        refreshed.append(row)
                cache_set(cache_key, refreshed)
        except Exception as exc:
            print(f"[Supabase Chat] mark_as_read: {exc}")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET is_read = 1 WHERE sender = ? AND receiver = ?", (friend_nick, my_nick))
    conn.commit()
    conn.close()
    cache_invalidate(cache_key)


def get_unread_count(my_nick, friend_nick):
    if is_supabase_configured():
        try:
            messages = load_json_store("messages", default=[])
            return sum(1 for m in messages if m.get("sender") == friend_nick and m.get("receiver") == my_nick and m.get("is_read") == 0)
        except Exception as exc:
            print(f"[Supabase Chat] get_unread_count: {exc}")
            return 0
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE sender = ? AND receiver = ? AND is_read = 0", (friend_nick, my_nick))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def send_friend_request(my_id, target_id):
    if is_supabase_configured():
        try:
            resolved_target = target_id
            maybe = get_nickname_by_phone(target_id)
            if maybe:
                resolved_target = maybe
            requests = load_json_store("friend_requests", default=[])
            if any(r.get("from_user") == my_id and r.get("to_user") == resolved_target for r in requests):
                return {"status": "error", "message": "Заявка уже отправлена"}
            requests.append({"from_user": my_id, "to_user": resolved_target, "status": "pending"})
            save_json_store("friend_requests", requests)
            return {"status": "success"}
        except Exception as exc:
            print(f"[Supabase Chat] send_friend_request: {exc}")
            return {"status": "error", "message": str(exc)}
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    resolved_target = target_id
    try:
        maybe = get_nickname_by_phone(target_id)
        if maybe:
            resolved_target = maybe
    except Exception:
        resolved_target = target_id

    cursor.execute("SELECT 1 FROM users WHERE nickname = ?", (resolved_target,))
    if not cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "Пользователь не найден"}

    cursor.execute("SELECT 1 FROM friends WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)", (my_id, resolved_target, resolved_target, my_id))
    if cursor.fetchone():
        conn.close()
        return {"status": "error", "message": "Вы уже друзья!"}

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
    if is_supabase_configured():
        try:
            friends = load_json_store("friends", default=[])
            filtered = [row for row in friends if not ((row.get("user1") == my_nick and row.get("user2") == friend_nick) or (row.get("user1") == friend_nick and row.get("user2") == my_nick))]
            save_json_store("friends", filtered)
            requests = load_json_store("friend_requests", default=[])
            updated = []
            for row in requests:
                r = dict(row)
                if (r.get("from_user") == my_nick and r.get("to_user") == friend_nick) or (r.get("from_user") == friend_nick and r.get("to_user") == my_nick):
                    r["status"] = "rejected"
                updated.append(r)
            save_json_store("friend_requests", updated)
            cache_invalidate(f"friends:{my_nick}")
            cache_invalidate(f"friends:{friend_nick}")
        except Exception as exc:
            print(f"[Supabase Chat] delete_friend: {exc}")
            cache_invalidate(f"friends:{my_nick}")
            cache_invalidate(f"friends:{friend_nick}")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM friends WHERE (user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?)", (my_nick, friend_nick, friend_nick, my_nick))
        cursor.execute("UPDATE friend_requests SET status = 'rejected' WHERE (from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?)", (my_nick, friend_nick, friend_nick, my_nick))
        conn.commit()
    finally:
        conn.close()


def get_incoming_requests(my_nick):
    if is_supabase_configured():
        try:
            requests = load_json_store("friend_requests", default=[])
            return [row.get("from_user") for row in requests if row.get("to_user") == my_nick and row.get("status") == "pending"]
        except Exception as exc:
            print(f"[Supabase Chat] get_incoming_requests: {exc}")
            return []
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT from_user FROM friend_requests WHERE to_user = ? AND status = 'pending'", (my_nick,))
    reqs = [r[0] for r in cursor.fetchall()]
    conn.close()
    return reqs


def accept_friend_request(my_nick, friend_nick):
    if is_supabase_configured():
        try:
            requests = load_json_store("friend_requests", default=[])
            updated = []
            for row in requests:
                r = dict(row)
                if (r.get("from_user") == friend_nick and r.get("to_user") == my_nick) or (r.get("from_user") == my_nick and r.get("to_user") == friend_nick):
                    r["status"] = "accepted"
                updated.append(r)
            save_json_store("friend_requests", updated)
            friends = load_json_store("friends", default=[])
            if not any((f.get("user1") == my_nick and f.get("user2") == friend_nick) or (f.get("user1") == friend_nick and f.get("user2") == my_nick) for f in friends):
                friends.append({"user1": my_nick, "user2": friend_nick})
                save_json_store("friends", friends)
            cache_invalidate(f"friends:{my_nick}")
            cache_invalidate(f"friends:{friend_nick}")
        except Exception as exc:
            print(f"[Supabase Chat] accept_friend_request: {exc}")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE friend_requests SET status = 'accepted' WHERE (from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?)", (friend_nick, my_nick, my_nick, friend_nick))
    a, b = (my_nick, friend_nick)
    try:
        cursor.execute("INSERT OR IGNORE INTO friends (user1, user2) VALUES (?, ?)", (a, b))
    except Exception:
        try:
            cursor.execute("INSERT OR IGNORE INTO friends (user1, user2) VALUES (?, ?)", (b, a))
        except Exception:
            pass
    conn.commit()
    conn.close()
    cache_invalidate(f"friends:{my_nick}")
    cache_invalidate(f"friends:{friend_nick}")


def reject_friend_request(my_nick, friend_nick):
    """Помечает заявку как отклонённую (rejected)."""
    if is_supabase_configured():
        try:
            requests = load_json_store("friend_requests", default=[])
            updated = []
            for row in requests:
                r = dict(row)
                if (r.get("from_user") == friend_nick and r.get("to_user") == my_nick) or (r.get("from_user") == my_nick and r.get("to_user") == friend_nick):
                    r["status"] = "rejected"
                updated.append(r)
            save_json_store("friend_requests", updated)
        except Exception as exc:
            print(f"[Supabase Chat] reject_friend_request: {exc}")
            cache_invalidate(f"friends:{my_nick}")
            cache_invalidate(f"friends:{friend_nick}")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE friend_requests SET status = 'rejected' WHERE from_user = ? AND to_user = ?", (friend_nick, my_nick))
        cursor.execute("UPDATE friend_requests SET status = 'rejected' WHERE from_user = ? AND to_user = ?", (my_nick, friend_nick))
        conn.commit()
    finally:
        conn.close()


def get_friends_list(my_nick):
    cached = cache_get(f"friends:{my_nick}")
    if cached is not None:
        return cached

    if is_supabase_configured():
        try:
            friends = load_json_store("friends", default=[])
            out = []
            for row in friends:
                if row.get("user1") == my_nick:
                    out.append(row.get("user2"))
                elif row.get("user2") == my_nick:
                    out.append(row.get("user1"))
            result = list(dict.fromkeys(out))
            cache_set(f"friends:{my_nick}", result)
            return result
        except Exception as exc:
            print(f"[Supabase Chat] get_friends_list: {exc}")
            return []

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user2 FROM friends WHERE user1 = ?", (my_nick,))
    f1 = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT user1 FROM friends WHERE user2 = ?", (my_nick,))
    f2 = [r[0] for r in cursor.fetchall()]
    conn.close()
    result = list(set(f1 + f2))
    cache_set(f"friends:{my_nick}", result)
    return result


def save_message(sender, receiver, content, is_image=0):
    cache_key = _chat_cache_key(sender, receiver)
    if is_supabase_configured():
        try:
            messages = load_json_store("messages", default=[])
            next_id = max((m.get("id", 0) for m in messages), default=0) + 1
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if is_image and isinstance(content, (bytes, bytearray)):
                stored_content = base64.b64encode(content).decode("ascii")
            elif isinstance(content, (bytes, bytearray)):
                stored_content = content.decode("utf-8", errors="ignore")
            else:
                stored_content = content

            messages.append({
                "id": next_id,
                "sender": sender,
                "receiver": receiver,
                "content": stored_content,
                "timestamp": ts,
                "is_image": int(is_image),
                "is_read": 0,
            })
            save_json_store("messages", messages)
            cached = cache_get(cache_key)
            result_row = (sender, content, ts, int(is_image), next_id, 0)
            if cached is not None:
                cache_set(cache_key, list(cached) + [result_row])
            return result_row
        except Exception as exc:
            print(f"[Supabase Chat] save_message: {exc}")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if is_image == 0 and isinstance(content, str):
        content = content.encode('utf-8')
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO messages (sender, receiver, content, timestamp, is_image, is_read) VALUES (?, ?, ?, ?, ?, 0)",
                   (sender, receiver, content, ts, is_image))
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    cached = cache_get(cache_key)
    result_row = (sender, content, ts, is_image, msg_id, 0)
    if cached is not None:
        cache_set(cache_key, list(cached) + [result_row])
    return result_row


def get_chat_history(user1, user2):
    cache_key = _chat_cache_key(user1, user2)

    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    if is_supabase_configured():
        try:
            messages = load_json_store("messages", default=[])
            rows = [m for m in messages if ((m.get("sender") == user1 and m.get("receiver") == user2) or
                                            (m.get("sender") == user2 and m.get("receiver") == user1))]
            result = []
            for row in rows:
                content = row.get("content")
                if row.get("is_image") and isinstance(content, str):
                    try:
                        content = base64.b64decode(content)
                    except Exception:
                        pass
                result.append((row.get("sender"), content, row.get("timestamp"), row.get("is_image"), row.get("id"), row.get("is_read", 0)))

            cache_set(cache_key, result)
            return result
        except Exception as exc:
            print(f"[Supabase Error] {exc}")
            return []

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""SELECT sender, content, timestamp, is_image, id, is_read FROM messages
                      WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
                      ORDER BY id ASC""", (user1, user2, user2, user1))
    history = cursor.fetchall()
    conn.close()

    cache_set(cache_key, history)
    return history
