import sqlite3
 
from tools.supabase_client import is_supabase_configured, load_json_store, save_json_store
from tools.cache import cache_get, cache_set
DB_GAMES = "games.db"
 
START_GAMES = [
    {"id": "it_magnat", "title": "IT-Магнат: Симулятор Джуна", "genre": "Стратегия", "icon": "🎮",
     "release_date": "Июль 2026 г.", "publisher": "Solo Dev Inc.",
     "description": "Пройдите путь от написания первой строчки кода до создания собственной IT-империи. Нанимайте джунов, покупайте сервера и автоматизируйте разработку!"},
    {"id": "snake", "title": "Ретро Змейка", "genre": "Аркада", "icon": "🐍",
     "release_date": "Май 2025 г.", "publisher": "Classic Games",
     "description": "Старая добрая змейка в новой обертке. Собирайте пиксели, растите в размерах и не врезайтесь в собственные хвост и стены!"},
    {"id": "cyber_race", "title": "Кибер-Гонки 2077", "genre": "Гонки", "icon": "🏎️",
     "release_date": "Декабрь 2025 г.", "publisher": "Neon Drive Studio",
     "description": "Сумасшедшие неоновые гонки на выживание. Прокачивайте свой болид и обгоняйте соперников на футуристических трассах."},
    {"id": "dungeon_crawler", "title": "Подземелье Страха", "genre": "РПГ", "icon": "⚔️",
     "release_date": "Январь 2026 г.", "publisher": "Pixel Rogue",
     "description": "Пошаговый рогалик. Спускайтесь в темные процедурно-генерируемые подземелья, сражайтесь с монстрами и собирайте легендарный лут."},
    {"id": "space_def", "title": "Защита Галактики", "genre": "Аркада", "icon": "🚀",
     "release_date": "Март 2026 г.", "publisher": "Astro Games",
     "description": "Классический космический скролл-шутер. Защитите Землю от бесконечных волн инопланетных захватчиков и гигантских боссов."},
    {"id": "farm_sim", "title": "Фермерский Уголок", "genre": "Симулятор", "icon": "🚜",
     "release_date": "Июнь 2026 г.", "publisher": "Cozy Games",
     "description": "Расслабирающий симулятор жизни и фермерства. Сажайте грядки, ухаживайте за животными и торгуйте на местном рынке."},
]
 
 
def init_games_db():
    if is_supabase_configured():
        try:
            games = load_json_store("games", default=[])
            if not games:
                save_json_store("games", START_GAMES)
        except Exception as exc:
            print(f"[Supabase Games] init_games_db: {exc}")
        return
 
    conn = sqlite3.connect(DB_GAMES)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            title TEXT,
            genre TEXT,
            icon TEXT,
            release_date TEXT,
            publisher TEXT,
            description TEXT
        )
    ''')
    for game in START_GAMES:
        cursor.execute(
            'INSERT OR IGNORE INTO games VALUES (?, ?, ?, ?, ?, ?, ?)',
            (game["id"], game["title"], game["genre"], game["icon"],
             game["release_date"], game["publisher"], game["description"])
        )
    conn.commit()
    conn.close()
 
 
def get_games_from_db(genre_filter="Все", sort_by="По алфавиту А-Я"):
    cache_key = f"games:{genre_filter}:{sort_by}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    if is_supabase_configured():
        try:
            games = load_json_store("games", default=[])
            rows = [{
                "id": g.get("id"), "title": g.get("title"), "genre": g.get("genre"),
                "icon": g.get("icon"), "date": g.get("release_date"),
                "publisher": g.get("publisher"), "desc": g.get("description"),
            } for g in games]

            if genre_filter != "Все":
                rows = [r for r in rows if r["genre"] == genre_filter]

            if sort_by == "По алфавиту А-Я":
                rows.sort(key=lambda r: (r["title"] or ""))
            elif sort_by == "По алфавиту Я-А":
                rows.sort(key=lambda r: (r["title"] or ""), reverse=True)

            cache_set(cache_key, rows)
            return rows
        except Exception as exc:
            print(f"[Supabase Games] get_games_from_db: {exc}")
            return []

    conn = sqlite3.connect(DB_GAMES)
    cursor = conn.cursor()
    query = "SELECT id, title, genre, icon, release_date, publisher, description FROM games WHERE 1=1"
    params = []
    if genre_filter != "Все":
        query += " AND genre = ?"
        params.append(genre_filter)
    if sort_by == "По алфавиту А-Я":
        query += " ORDER BY title ASC"
    elif sort_by == "По алфавиту Я-А":
        query += " ORDER BY title DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    result = [{
        "id": r[0], "title": r[1], "genre": r[2], "icon": r[3],
        "date": r[4], "publisher": r[5], "desc": r[6]
    } for r in rows]
    cache_set(cache_key, result)
    return result