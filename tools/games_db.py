import sqlite3

DB_GAMES = "games.db"

def init_games_db():
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
    
    start_games = [
        ("it_magnat", "IT-Магнат: Симулятор Джуна", "Стратегия", "🎮", "Июль 2026 г.", "Solo Dev Inc.", "Пройдите путь от написания первой строчки кода до создания собственной IT-империи. Нанимайте джунов, покупайте сервера и автоматизируйте разработку!"),
        ("snake", "Ретро Змейка", "Аркада", "🐍", "Май 2025 г.", "Classic Games", "Старая добрая змейка в новой обертке. Собирайте пиксели, растите в размерах и не врезайтесь в собственные хвост и стены!"),
        ("cyber_race", "Кибер-Гонки 2077", "Гонки", "🏎️", "Декабрь 2025 г.", "Neon Drive Studio", "Сумасшедшие неоновые гонки на выживание. Прокачивайте свой болид и обгоняйте соперников на футуристических трассах."),
        ("dungeon_crawler", "Подземелье Страха", "РПГ", "⚔️", "Январь 2026 г.", "Pixel Rogue", "Пошаговый рогалик. Спускайтесь в темные процедурно-генерируемые подземелья, сражайтесь с монстрами и собирайте легендарный лут."),
        ("space_def", "Защита Галактики", "Аркада", "🚀", "Март 2026 г.", "Astro Games", "Классический космический скролл-шутер. Защитите Землю от бесконечных волн инопланетных захватчиков и гигантских боссов."),
        ("farm_sim", "Фермерский Уголок", "Симулятор", "🚜", "Июнь 2026 г.", "Cozy Games", "Расслабирающий симулятор жизни и фермерства. Сажайте грядки, ухаживайте за животными и торгуйте на местном рынке.")
    ]
    
    for game in start_games:
        cursor.execute('INSERT OR IGNORE INTO games VALUES (?, ?, ?, ?, ?, ?, ?)', game)
    conn.commit()
    conn.close()

def get_games_from_db(genre_filter="Все", sort_by="По алфавиту А-Я"):
    """Простой и надежный забор данных из БД без ломающейся SQL-фильтрации строк"""
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
    
    return [{
        "id": r[0], "title": r[1], "genre": r[2], "icon": r[3],
        "date": r[4], "publisher": r[5], "desc": r[6]
    } for r in rows]