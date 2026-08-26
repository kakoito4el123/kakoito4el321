"""Миграция локальной SQLite БД в Supabase (Postgres + Storage)

Как использовать:
  set SUPABASE_URL, SUPABASE_KEY; при необходимости SUPABASE_BUCKET
  python scripts/migrate_to_supabase.py --db path/to/local.db --dry-run

Скрипт переносит таблицы: users, friends, friend_requests, messages, games
и загружает бинарные поля (avatars, message images, game icons) в Supabase Storage.
"""
import os
import sys
import argparse
import sqlite3
from pathlib import Path
import base64
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.paths import DB_NAME
from tools.supabase_client import save_json_store


def upload_bytes_to_storage(storage, path, data_bytes):
    # path: строка внутри бакета
    # supabase-py expects a file-like object or bytes
    try:
        storage.upload(path, data_bytes)
    except Exception:
        # попытка через временный файл
        tmp = Path('tmp_upload.bin')
        tmp.write_bytes(data_bytes)
        storage.upload(path, str(tmp))
        tmp.unlink()


def migrate(db_path, bucket_name=None, dry_run=True):
    print(f"Using DB: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # USERS
    cursor.execute("SELECT nickname, phone, password, avatar, created_at, last_seen FROM users")
    users = cursor.fetchall()
    print(f"Found {len(users)} users")
    if not dry_run and users:
        rows = []
        for nick, phone, pw, avatar, created_at, last_seen in users:
            rows.append({
                'nickname': nick,
                'phone': phone,
                'password': pw,
                'avatar': avatar,
                'created_at': created_at,
                'last_seen': last_seen,
            })
        if rows:
            save_json_store('users', rows)
            print('Stored users JSON in Supabase Storage')

    # FRIENDS
    cursor.execute("SELECT user1, user2 FROM friends")
    friends = cursor.fetchall()
    print(f"Found {len(friends)} friends pairs")
    if not dry_run and friends:
        rows = [{'user1': a, 'user2': b} for a, b in friends]
        save_json_store('friends', rows)

    # FRIEND REQUESTS
    cursor.execute("SELECT from_user, to_user, status FROM friend_requests")
    reqs = cursor.fetchall()
    print(f"Found {len(reqs)} friend requests")
    if not dry_run and reqs:
        rows = [{'from_user': a, 'to_user': b, 'status': s} for a, b, s in reqs]
        save_json_store('friend_requests', rows)

    # GAMES
    try:
        cursor.execute("SELECT id, title, genre, icon, release_date, publisher, description FROM games")
        games = cursor.fetchall()
    except Exception:
        games = []
    print(f"Found {len(games)} games")
    if not dry_run and games:
        rows = []
        for gid, title, genre, icon, release_date, publisher, description in games:
            rows.append({'id': gid, 'title': title, 'genre': genre, 'icon': icon, 'release_date': release_date, 'publisher': publisher, 'description': description})
        save_json_store('games', rows)

    # MESSAGES
    cursor.execute("SELECT sender, receiver, content, timestamp, is_image FROM messages")
    msgs = cursor.fetchall()
    print(f"Found {len(msgs)} messages")
    if not dry_run and msgs:
        rows = []
        for i, (sender, receiver, content, ts, is_image) in enumerate(msgs):
            if is_image and isinstance(content, (bytes, bytearray)):
                stored_content = base64.b64encode(content).decode("ascii")
            elif isinstance(content, (bytes, bytearray)):
                try:
                    stored_content = content.decode('utf-8')
                except Exception:
                    stored_content = content.decode('latin-1', errors='ignore')
            else:
                stored_content = content
            rows.append({'sender': sender, 'receiver': receiver, 'content': stored_content, 'timestamp': ts, 'is_image': int(bool(is_image))})
        save_json_store('messages', rows)
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=False, default=str(DB_NAME))
    parser.add_argument('--bucket', required=False)
    parser.add_argument('--dry-run', action='store_true', help='Показывает, что будет перенесено без записи в Supabase')
    parser.add_argument('--execute', action='store_true', help='Выполнить реальную миграцию в Supabase')
    args = parser.parse_args()
    dry_run = args.dry_run or not args.execute
    print('Dry run mode' if dry_run else 'Executing migration')
    migrate(args.db, args.bucket, dry_run=dry_run)
