import webview
import os
import random
import sqlite3
from types import SimpleNamespace
# Твои родные импорты модулей и БД
from tools.auth_db import init_auth_db, check_session_timeout, logout_user
from tools.chat_db import init_chat_db
from tools.games_db import init_games_db, get_games_from_db

class LauncherAPI:
    def __init__(self):
            self.app_state = SimpleNamespace(running_games={}, active_game_window=None, active_game_id=None)
            self.active_contact_id = None
            # Запускаем строго твои родные инициализации баз данных, где лежат все аккаунты и чаты
            init_auth_db()
            init_chat_db()
            init_games_db()

    def open_native_auth(self):
        """Безопасно запускает окно auth_ui в отдельном потоке, выводя уведомления через pywebview"""
        import threading
        import tkinter as tk
        from tools.auth_ui import show_auth_window

        def run_tk_thread():
            # Создаем изолированную среду Tkinter для потока
            root = tk.Tk()
            root.withdraw()  # Прячем невидимое главное окно

            # Обычный трюк, чтобы скрыть лишнее пустое окно на панели задач для root
            root.overrideredirect(True)
            root.geometry("0x0+0+0")

            # Временный костыль: подменяем стандартный messagebox.showinfo внутри потока,
            # чтобы он не ломал поток (перенаправляем вывод в консоль)
            from tkinter import messagebox
            original_showinfo = messagebox.showinfo
            messagebox.showinfo = lambda title, message: print(f"[{title}] {message}")

            login_status = {"success": False}

            def on_success():
                login_status["success"] = True
                auth_win.destroy()
                root.quit()

            # Инициализируем твое окно
            auth_win = show_auth_window(root, on_success)
            
            def on_close_win():
                auth_win.destroy()
                root.quit()
            auth_win.protocol("WM_DELETE_WINDOW", on_close_win)

            root.mainloop()
            
            # Возвращаем messagebox на место после закрытия цикла
            messagebox.showinfo = original_showinfo

            # Если вход был успешным, делаем нативное уведомление и релоад
            if login_status["success"]:
                if webview.windows:
                    # Показываем красивое окно уведомления силами браузера лаунчера, а затем обновляем страницу
                    webview.windows[0].evaluate_js("alert('Вы успешно вошли!'); location.reload();")

        # Запускаем поток авторизации
        auth_thread = threading.Thread(target=run_tk_thread)
        auth_thread.start()

    def logout_user(self):
        """Выход из аккаунта"""
        from tools.auth_db import logout_user
        logout_user()
        return True
    
    def get_games_list(self):
            """Читаем список игр из твоей реальной базы через твой модуль"""
            try:
                # Вызываем твою оригинальную функцию из tools.games_db
                games = get_games_from_db() 
                
                # Превращаем кортежи из базы в красивый массив объектов для JS
                return [{
                    "id": g[0],
                    "title": g[1],
                    "genre": g[2],
                    "icon": g[3],
                    "release_date": g[4],
                    "publisher": g[5],
                    "description": g[6]
                } for g in games]
            except Exception as e:
                print(f"[Python Игротека] Ошибка чтения базы игр: {e}")
                return []

    def launch_game_by_id(self, game_id):
        """Запуск выбранной игры (логика из твоего файла tools/games.py)"""
        # Здесь мы в будущем вызовем твой родной скрипт запуска,
        # а пока выводим лог в консоль для проверки связи
        print(f"[Python Лаунчер] Запрос на запуск игры с ID: {game_id}")
        
        # Если у тебя в tools/games.py есть функция запуска, мы вызовем её здесь.
        return {"status": "success", "game_id": game_id}

    # --- РАБОТА С ТВОИМ ПРОФИЛЕМ ---
    def get_user_profile_data(self):
        """Читаем сессию из session.txt и берем данные из твоей БД"""
        try:
            from tools.auth_db import get_current_user
            from tools.paths import DB_NAME
            
            user_data = get_current_user() # Читает твой session.txt
            if user_data:
                nick = user_data[0]
                phone = user_data[1] if len(user_data) > 1 else "Не указан"
                
                # Подключаемся к твоей реальной общей базе данных
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                # Проверяем, есть ли поле аватарки в твоей таблице users
                try:
                    cursor.execute("SELECT avatar FROM users WHERE nickname = ?", (nick,))
                    row = cursor.fetchone()
                    avatar = row[0] if row and row[0] else "👤"
                except:
                    avatar = "👤" # Если поля нет, ставим дефолт
                conn.close()
                
                return {
                    "nickname": nick,
                    "phone": phone,
                    "avatar": avatar,
                    "status": "Разработчик"
                }
        except Exception as e:
            print(f"[Python Профиль] Ошибка сбора данных: {e}")
            
        return {
            "nickname": "Авторизуйтесь",
            "phone": "Нет сессии",
            "avatar": "👤",
            "status": "Гость"
        }

    # --- РАБОТА С ТВОИМ ЧАТОМ ---
    def get_launcher_chat_messages(self):
        """Читаем историю сообщений из твоей таблицы messages с декодированием текста и конвертацией BLOB картинок"""
        try:
            from tools.paths import DB_NAME
            from tools.auth_db import get_current_user
            import datetime
            import base64  # Добавляем для кодирования картинок
            
            user_data = get_current_user()
            my_nick = user_data[0] if user_data else ""
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            # Достаем сообщения, включая флаг картинки is_image
            cursor.execute("SELECT sender, content, timestamp, is_image FROM messages ORDER BY id DESC LIMIT 50")
            rows = cursor.fetchall()
            conn.close()
            
            rows.reverse()
            
            def format_chat_date(ts_str):
                try:
                    dt = datetime.datetime.strptime(ts_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                    today = datetime.date.today()
                    yesterday = today - datetime.timedelta(days=1)
                    if dt.date() == today:
                        return f"Сегодня, {dt.strftime('%H:%M')}"
                    elif dt.date() == yesterday:
                        return f"Вчера, {dt.strftime('%H:%M')}"
                    else:
                        return dt.strftime("%d.%m.%Y %H:%M")
                except:
                    return ts_str

            messages_list = []
            for row in rows:
                sender = row[0]
                content_raw = row[1]
                timestamp = format_chat_date(row[2]) if row[2] else ""
                is_image = row[3] if len(row) > 3 else 0
                
                content_text = ""
                
                # ЕСЛИ ЭТО КАРТИНКА (Байты изображения из базы)
                if is_image and isinstance(content_raw, bytes):
                    try:
                        # Кодируем бинарные байты картинки в строку Base64
                        b64_data = base64.b64encode(content_raw).decode('utf-8')
                        # Формируем Data URL, который поймет любой браузер в <img>
                        content_text = f"data:image/png;base64,{b64_data}"
                    except Exception as img_err:
                        print(f"[Python Чат] Ошибка конвертации картинки: {img_err}")
                        content_text = "[Ошибка отображения изображения]"
                else:
                    # ЕСЛИ ЭТО ОБЫЧНЫЙ ТЕКСТ ИЛИ СМАЙЛИК
                    if isinstance(content_raw, bytes):
                        try:
                            content_text = content_raw.decode('utf-8')
                        except:
                            try:
                                content_text = content_raw.decode('latin-1', errors='ignore')
                            except:
                                content_text = "[Нечитаемое сообщение]"
                    else:
                        content_text = str(content_raw)
                
                messages_list.append({
                    "sender": sender,
                    "text": content_text,
                    "time": timestamp,
                    "is_me": sender == my_nick,
                    "is_image": bool(is_image)
                })
            return messages_list
        except Exception as e:
            print(f"[Python Чат] Ошибка загрузки messages: {e}")
            return []

    def get_private_chat_messages(self, partner):
        """Возвращает историю между текущим пользователем и partner (nickname)."""
        try:
            from tools.paths import DB_NAME
            from tools.auth_db import get_current_user
            import datetime
            import base64
            from tools.chat_db import get_chat_history

            user_data = get_current_user()
            my_nick = user_data[0] if user_data else ""
            if not my_nick or not partner:
                return []

            history = get_chat_history(my_nick, partner)
            messages_list = []
            for sender, content_raw, time_str, is_image, msg_id in history:
                # reuse formatting from get_launcher_chat_messages
                if is_image and isinstance(content_raw, bytes):
                    try:
                        b64_data = base64.b64encode(content_raw).decode('utf-8')
                        content_text = f"data:image/png;base64,{b64_data}"
                    except:
                        content_text = "[Ошибка изображения]"
                else:
                    if isinstance(content_raw, bytes):
                        try:
                            content_text = content_raw.decode('utf-8')
                        except:
                            content_text = content_raw.decode('latin-1', errors='ignore')
                    else:
                        content_text = str(content_raw)

                messages_list.append({
                    "sender": sender,
                    "text": content_text,
                    "time": time_str,
                    "is_me": sender == my_nick,
                    "is_image": bool(is_image)
                })
            return messages_list
        except Exception as e:
            print(f"[Python Чат] Ошибка get_private_chat_messages: {e}")
            return []

    def send_launcher_message(self, receiver, text):
        """Сохраняет сообщение от текущей сессии к receiver."""
        try:
            from tools.auth_db import get_current_user
            from tools.chat_db import save_message
            user = get_current_user()
            if not user:
                return {"status": "error", "message": "Не авторизован"}
            my = user[0]
            if not receiver:
                return {"status": "error", "message": "Неверные параметры"}

            # Поддерживаем отправку изображений: если третьим аргументом передан флаг is_image==1,
            # JS посылает data URL или base64-строку.
            is_image = 0
            # текст может быть объектом если pywebview передаёт третий параметр; попытка получить
            try:
                # При вызове из JS может быть передан третий параметр
                # pywebview maps extra args positionally; если text - объект, нормализуем
                pass
            except:
                pass

            # Если text выглядит как Data URL — считаем это картинкой
            if isinstance(text, str) and text.startswith('data:'):
                import base64
                header, b64 = text.split(',', 1)
                try:
                    data = base64.b64decode(b64)
                    save_message(my, receiver, data, is_image=1)
                    return {"status": "success"}
                except Exception as e:
                    print(f"[Python Чат] Ошибка при сохранении картинки: {e}")
                    return {"status": "error", "message": "Ошибка сохранения изображения"}

            # Обычный текст
            if not text:
                return {"status": "error", "message": "Пустое сообщение"}
            save_message(my, receiver, text, is_image=0)
            return {"status": "success"}
        except Exception as e:
            print(f"[Python Чат] Ошибка send_launcher_message: {e}")
            return {"status": "error", "message": str(e)}

    def send_launcher_friend_request(self, target):
        try:
            from tools.auth_db import get_current_user
            from tools.chat_db import send_friend_request
            user = get_current_user()
            if not user:
                return {"status": "error", "message": "Не авторизованы"}
            my = user[0]
            return send_friend_request(my, target)
        except Exception as e:
            print(f"[Python Друзья] Ошибка send_launcher_friend_request: {e}")
            return {"status": "error", "message": str(e)}

    def accept_launcher_friend_request(self, from_user):
        try:
            from tools.chat_db import accept_friend_request
            from tools.auth_db import get_current_user
            accept_friend_request(get_current_user()[0], from_user)
            return {"status": "success"}
        except Exception as e:
            print(f"[Python Друзья] Ошибка accept_launcher_friend_request: {e}")
            return {"status": "error", "message": str(e)}

    def get_launcher_friend_requests(self):
        try:
            from tools.chat_db import get_incoming_requests
            from tools.auth_db import get_current_user
            user = get_current_user()
            if not user: return []
            my = user[0]
            return get_incoming_requests(my)
        except Exception as e:
            print(f"[Python Друзья] Ошибка get_launcher_friend_requests: {e}")
            return []

    def decline_launcher_friend_request(self, from_user):
        try:
            from tools.chat_db import reject_friend_request
            from tools.auth_db import get_current_user
            user = get_current_user()
            if not user:
                return {"status": "error", "message": "Не авторизованы"}
            my = user[0]
            reject_friend_request(my, from_user)
            return {"status": "success"}
        except Exception as e:
            print(f"[Python Друзья] Ошибка decline_launcher_friend_request: {e}")
            return {"status": "error", "message": str(e)}

    def delete_launcher_friend(self, friend_name):
        try:
            from tools.chat_db import delete_friend
            from tools.auth_db import get_current_user
            user = get_current_user()
            if not user:
                return {"status": "error", "message": "Не авторизованы"}
            my = user[0]
            delete_friend(my, friend_name)
            return {"status": "success"}
        except Exception as e:
            print(f"[Python Друзья] Ошибка delete_launcher_friend: {e}")
            return {"status": "error", "message": str(e)}

    def get_todo_tasks(self):
        conn = sqlite3.connect("todo.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, task FROM tasks")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": row[0], "task": row[1]} for row in rows]

    def add_todo_task(self, task_text):
        if not task_text.strip(): return {"status": "error"}
        conn = sqlite3.connect("todo.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (task) VALUES (?)", (task_text,))
        conn.commit()
        conn.close()
        return {"status": "success"}

    def delete_todo_task(self, task_id):
        conn = sqlite3.connect("todo.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    
    # --- СИСТЕМА ДРУЗЕЙ (ИЗ ТВОЕЙ ТАБЛИЦЫ friends И friend_requests) ---
    def get_launcher_friends(self):
        """Получаем список твоих друзей из базы данных"""
        try:
            from tools.paths import DB_NAME
            from tools.auth_db import get_current_user
            user_data = get_current_user()
            if not user_data: return []
            my_nick = user_data[0]
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            # Ищем всех друзей, где ты либо user1, либо user2
            cursor.execute("SELECT user2 FROM friends WHERE user1 = ?", (my_nick,))
            f1 = [r[0] for r in cursor.fetchall()]
            cursor.execute("SELECT user1 FROM friends WHERE user2 = ?", (my_nick,))
            f2 = [r[0] for r in cursor.fetchall()]

            friends_list = list(set(f1 + f2))
            # Возвращаем объекты со временем последней активности (last_seen)
            out = []
            for f in friends_list:
                cursor.execute("SELECT last_seen FROM users WHERE nickname = ?", (f,))
                row = cursor.fetchone()
                last_seen = row[0] if row and row[0] else None
                out.append({"name": f, "last_seen": last_seen})
            conn.close()
            return out
        except Exception as e:
            print(f"[Python Друзья] Ошибка получения списка: {e}")
            return []

    def add_launcher_friend_by_phone(self, phone):
        """Добавление друга по номеру телефона (логика твоей БД)"""
        try:
            from tools.paths import DB_NAME
            from tools.auth_db import get_current_user
            user_data = get_current_user()
            if not user_data: return {"status": "error", "message": "Вы не авторизованы"}
            my_nick = user_data[0]
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            # Ищем никнейм юзера по его телефону в таблице users
            cursor.execute("SELECT nickname FROM users WHERE phone = ?", (phone.strip(),))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return {"status": "error", "message": "Пользователь с таким номером не найден"}
                
            friend_nick = row[0]
            if friend_nick == my_nick:
                conn.close()
                return {"status": "error", "message": "Нельзя добавить самого себя"}
                
            # Добавляем в таблицу заявок friend_requests
            cursor.execute("INSERT INTO friend_requests (from_user, to_user, status) VALUES (?, ?, 'pending')", (my_nick, friend_nick))
            conn.commit()
            conn.close()
            return {"status": "success", "message": f"Заявка отправлена пользователю {friend_nick}!"}
        except Exception as e:
            print(f"[Python Друзья] Ошибка отправки заявки: {e}")
            return {"status": "error", "message": "Ошибка базы данных"}

    # --- ФУНКЦИЯ ВЫХОДА ИЗ АККАУНТА ---
    def logout_launcher_user(self):
        """Удаляем сессию через твой родной модуль без закрытия приложения"""
        try:
            from tools.auth_db import logout_user
            logout_user() # Удаляет session.txt
            return {"status": "success"}
        except Exception as e:
            print(f"[Python Логаут] Ошибка: {e}")
            return {"status": "error"}

    def ping_user_activity(self):
        try:
            from tools.auth_db import get_current_user, update_user_activity
            u = get_current_user()
            if not u: return {"status": "error"}
            update_user_activity(u[0])
            return {"status": "success"}
        except Exception as e:
            print(f"[Python Пинг] Ошибка: {e}")
            return {"status": "error"}

    def login_launcher_user(self, nickname, password):
        """Вход пользователя через твой родной auth_db"""
        try:
            from tools.auth_db import login_user
            success = login_user(nickname, password)
            if success:
                return {"status": "success", "message": "Успешный вход!"}
            return {"status": "error", "message": "Неверный никнейм или пароль"}
        except Exception as e:
            print(f"[Python Auth] Ошибка входа: {e}")
            return {"status": "error", "message": "Ошибка базы данных"}

    def register_launcher_user(self, nickname, phone, password):
        """Регистрация нового пользователя в твоей БД users"""
        try:
            from tools.paths import DB_NAME
            import hashlib
            import datetime
            
            if not nickname.strip() or not phone.strip() or not password.strip():
                return {"status": "error", "message": "Заполните все поля!"}
                
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # Проверяем, занят ли ник
            cursor.execute("SELECT nickname FROM users WHERE nickname = ?", (nickname.strip(),))
            if cursor.fetchone():
                conn.close()
                return {"status": "error", "message": "Этот никнейм уже занят"}
                
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                "INSERT INTO users (nickname, phone, password, avatar, created_at) VALUES (?, ?, ?, ?, ?)",
                (nickname.strip(), phone.strip(), hashed_pw, "👤", now)
            )
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Регистрация успешна! Теперь вы можете войти."}
        except Exception as e:
            print(f"[Python Auth] Ошибка регистрации: {e}")
            return {"status": "error", "message": f"Ошибка БД: {e}"}
            
    def get_active_chat_partner_info(self):
        """Возвращает информацию для шапки чата"""
        return {
            "name": "ОБЩИЙ ЧАТ (Global Room)",
            "status": "В сети",
            "online": True
        }

    # --- ОСТАЛЬНЫЕ ФУНКЦИИ ---
    def get_games(self):
        try: return get_games_from_db()
        except: return []

    def generate_random_number(self):
        return random.randint(1, 100)

    def close_app(self):
        if webview.windows: webview.windows[0].destroy()

    def select_contact(self, contact_id):
        self.active_contact_id = int(contact_id)
        return True

    def get_active_chat_id(self):
        return self.active_contact_id

if __name__ == "__main__":
    api = LauncherAPI()

    window = webview.create_window(
        title="Modular Modern Launcher",
        url='index.html',
        width=1200,
        height=700,
        resizable=True,
        background_color='#0b0b0e',
        js_api=api
    )

    webview.start()