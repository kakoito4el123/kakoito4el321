import json
import sqlite3
import time
import uuid

from tools.paths import DB_NAME
from tools.supabase_client import is_supabase_configured, load_json_store, save_json_store


def init_notifications_db():
    if is_supabase_configured():
        notifications = load_json_store("notifications", default=[])
        if not notifications:
            try:
                add_notification("", "system", "Добро пожаловать!", "Это ваш центр уведомлений. Здесь появятся коды, сообщения и события.")
            except Exception as exc:
                print(f"[Notifications] Не удалось создать приветственное событие: {exc}")
        return
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            recipient TEXT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at REAL NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            metadata TEXT
        )"""
    )
    conn.commit()
    conn.close()
    conn = sqlite3.connect(DB_NAME)
    has_notifications = conn.execute("SELECT 1 FROM notifications LIMIT 1").fetchone()
    conn.close()
    if not has_notifications:
        add_notification("", "system", "Добро пожаловать!", "Это ваш центр уведомлений. Здесь появятся коды, сообщения и события.")


def add_notification(recipient, category, title, body, metadata=None):
    notification = {
        "id": str(uuid.uuid4()),
        "recipient": recipient or "",
        "category": category,
        "title": title,
        "body": body,
        "created_at": time.time(),
        "is_read": False,
        "metadata": metadata or {},
    }
    if is_supabase_configured():
        notifications = load_json_store("notifications", default=[])
        notifications.append(notification)
        save_json_store("notifications", notifications[-500:])
        return notification

    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        "INSERT INTO notifications VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            notification["id"],
            notification["recipient"],
            notification["category"],
            notification["title"],
            notification["body"],
            notification["created_at"],
            0,
            json.dumps(notification["metadata"], ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()
    return notification


def get_notifications(recipient="", include_guest=True, limit=100):
    if is_supabase_configured():
        rows = load_json_store("notifications", default=[])
        visible = [
            dict(row)
            for row in rows
            if row.get("recipient", "") == recipient
            or (include_guest and row.get("recipient", "") == "")
        ]
        return sorted(visible, key=lambda row: row.get("created_at", 0), reverse=True)[:limit]

    conn = sqlite3.connect(DB_NAME)
    rows = conn.execute(
        """SELECT id, recipient, category, title, body, created_at, is_read, metadata
           FROM notifications
           WHERE recipient = ? OR (? = 1 AND recipient = '')
           ORDER BY created_at DESC LIMIT ?""",
        (recipient, int(include_guest), limit),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        try:
            metadata = json.loads(row[7] or "{}")
        except json.JSONDecodeError:
            metadata = {}
        result.append({
            "id": row[0], "recipient": row[1], "category": row[2],
            "title": row[3], "body": row[4], "created_at": row[5],
            "is_read": bool(row[6]), "metadata": metadata,
        })
    return result


def mark_notifications_read(recipient, notification_ids=None):
    ids = set(notification_ids or [])
    if is_supabase_configured():
        rows = load_json_store("notifications", default=[])
        for row in rows:
            if row.get("recipient", "") in (recipient, "") and (not ids or row.get("id") in ids):
                row["is_read"] = True
        save_json_store("notifications", rows)
        return

    conn = sqlite3.connect(DB_NAME)
    if ids:
        placeholders = ",".join("?" for _ in ids)
        conn.execute(
            f"UPDATE notifications SET is_read = 1 WHERE recipient IN (?, '') AND id IN ({placeholders})",
            (recipient, *ids),
        )
    else:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE recipient IN (?, '')", (recipient,))
    conn.commit()
    conn.close()


def clear_verification_notifications():
    if is_supabase_configured():
        rows = load_json_store("notifications", default=[])
        rows = [row for row in rows if not row.get("metadata", {}).get("verification_code")]
        save_json_store("notifications", rows)
        return

    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        "DELETE FROM notifications WHERE json_extract(metadata, '$.verification_code') = 1"
    )
    conn.commit()
    conn.close()
