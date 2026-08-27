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
        
        # Запускаем в отдельном потоке, чтобы GUI (окно) не висло при старте
        import threading
        threading.Thread(target=self._init_databases, daemon=True).start()

    def _init_databases(self):
        init_auth_db()
        init_chat_db()
        init_games_db()
        print("Базы данных инициализированы в фоне.")

    def get_chat_history_for_js(self, friend_name):
        from tools.auth_db import get_current_user
        from tools.chat_db import get_chat_history, mark_as_read
        import base64

        user_data = get_current_user()
        my_nick = user_data[0] if user_data else ""
        if not my_nick or not friend_name:
            return []

        mark_as_read(my_nick, friend_name)
        history = get_chat_history(my_nick, friend_name)
        messages_list = []
        for row in history:
            sender, content_raw, time_str, is_image, msg_id = row[:5]
            is_read = row[5] if len(row) > 5 else 0
            if is_image and isinstance(content_raw, bytes):
                try:
                    b64_data = base64.b64encode(content_raw).decode('utf-8')
                    content_text = f"data:image/png;base64,{b64_data}"
                except Exception:
                    content_text = "[Ошибка изображения]"
            else:
                if isinstance(content_raw, bytes):
                    try:
                        content_text = content_raw.decode('utf-8')
                    except Exception:
                        content_text = content_raw.decode('latin-1', errors='ignore')
                else:
                    content_text = str(content_raw)

            messages_list.append({
                "id": msg_id,
                "sender": sender,
                "text": content_text,
                "time": time_str,
                "is_me": sender == my_nick,
                "is_image": bool(is_image),
                "is_read": bool(is_read),
            })

        print(f"[DEBUG] Отправляю в JS список из {len(messages_list)} сообщений")
        return messages_list

    def get_message_read_status(self, partner):
        """Проверяет, прочитал ли partner последние отправленные ЕМУ сообщения"""
        try:
            from tools.auth_db import get_current_user
            from tools.chat_db import get_chat_history
            user_data = get_current_user()
            my_nick = user_data[0] if user_data else ""
            if not my_nick or not partner:
                return {}
            history = get_chat_history(my_nick, partner)
            my_msgs = [row for row in history if len(row) >= 6 and row[0] == my_nick]
            if not my_msgs:
                return {"last_read": False}
            return {"last_read": bool(my_msgs[-1][5])}
        except Exception as e:
            print(f"[Python Чат] get_message_read_status: {e}")
            return {"last_read": False}

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
        """Читаем список игр через tools.games_db"""
        try:
            games = get_games_from_db()
            return [{
                "id": g["id"],
                "title": g["title"],
                "genre": g["genre"],
                "icon": g["icon"],
                "release_date": g["date"],
                "publisher": g["publisher"],
                "description": g["desc"]
            } for g in games]
        except Exception as exc:
            print(f"[Python Игротека] Ошибка чтения базы игр: {exc}")
            return []

    def get_games_catalog(self, genre_filter="Все", sort_by="По алфавиту А-Я"):
        try:
            games = get_games_from_db(genre_filter=genre_filter, sort_by=sort_by)
            return [{
                "id": g["id"],
                "title": g["title"],
                "genre": g["genre"],
                "icon": g["icon"],
                "release_date": g["date"],
                "publisher": g["publisher"],
                "description": g["desc"],
            } for g in games]
        except Exception as exc:
            print(f"[Python Игротека] Ошибка чтения каталога: {exc}")
            return []

    def _get_game_by_id(self, game_id):
        for game in get_games_from_db():
            if str(game.get("id")) == str(game_id):
                return game
        return None

    def get_game_runtime_state(self):
        return {
            "running_games": dict(getattr(self.app_state, "running_games", {})),
            "active_game_id": getattr(self.app_state, "active_game_id", None),
        }

    def launch_game_by_id(self, game_id):
        """Запуск выбранной игры с отдельным окном-заглушкой без таймера ожидания."""
        try:
            import threading
            import tkinter as tk

            game_id = str(game_id)
            game = self._get_game_by_id(game_id)
            if not game:
                return {"status": "error", "message": "Игра не найдена"}
            
            # --- ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ СОСТОЯНИЯ ---
            if not hasattr(self.app_state, "game_windows"):
                self.app_state.game_windows = {}
            if not hasattr(self.app_state, "running_games"):
                self.app_state.running_games = {}
            if not hasattr(self.app_state, "real_processes"):
                self.app_state.real_processes = {}

            # Сначала закрываем другие запущенные игры (как в Стиме — активна только одна)
            for other_id in list(self.app_state.running_games.keys()):
                if other_id != game_id and self.app_state.running_games.get(other_id):
                    self.stop_game_by_id(other_id)

            # Если ЭТА игра уже запущена, просто выводим её окно на передний план
            existing = self.app_state.game_windows.get(game_id)
            if existing and existing.get("running"):
                root = existing.get("root")
                try:
                    if root:
                        root.after(0, lambda: (root.lift(), root.focus_force()))
                except Exception:
                    pass
                self.app_state.running_games[game_id] = True
                self.app_state.active_game_id = game_id
                return {"status": "success", "game_id": game_id, "running": True}

            # --- ЗАПУСК РЕАЛЬНОЙ ИГРЫ (IT_MAGNAT) ---
            if game_id == "it_magnat":
                import subprocess
                from tools.auth_db import get_current_user

                exe_path = os.path.join(os.path.dirname(__file__), "games", "it_magnat", "game_launcher.exe")
                if not os.path.exists(exe_path):
                    print(f"[launch_game_by_id] Файл не найден: {exe_path}")
                    return {"status": "error", "message": f"Игра не установлена: {exe_path}"}

                user_data = get_current_user()
                nickname = user_data[0] if user_data else "Гость"
                user_uuid = user_data[2] if user_data and len(user_data) > 2 else ""

                try:
                    proc = subprocess.Popen([
                        exe_path,
                        f"--uid={user_uuid}",
                        f"--nickname={nickname}",
                    ])
                    self.app_state.real_processes[game_id] = proc
                    self.app_state.running_games[game_id] = True
                    self.app_state.active_game_id = game_id

                    # Отслеживание закрытия реального процесса
                    def watch_process(p, gid):
                        p.wait()
                        if hasattr(self.app_state, "real_processes"):
                            self.app_state.real_processes.pop(gid, None)
                        if hasattr(self.app_state, "running_games"):
                            self.app_state.running_games[gid] = False
                        if getattr(self.app_state, "active_game_id", None) == gid:
                            self.app_state.active_game_id = None
                        print(f"[watch_process] Игра {gid} закрылась.")

                    threading.Thread(target=watch_process, args=(proc, game_id), daemon=True).start()

                    print(f"[launch_game_by_id] it_magnat запущен, UID={user_uuid}, nick={nickname}")
                    return {"status": "success", "game_id": game_id, "running": True}
                except Exception as exc:
                    print(f"[launch_game_by_id] Ошибка запуска it_magnat: {exc}")
                    return {"status": "error", "message": str(exc)}

            # --- ЗАПУСК ЗАГЛУШКИ ДЛЯ ОСТАЛЬНЫХ ИГР ---
            state = {"running": True, "root": None}
            self.app_state.game_windows[game_id] = state
            self.app_state.running_games[game_id] = True
            self.app_state.active_game_id = game_id

            def run_window():
                root = tk.Tk()
                state["root"] = root
                root.title(f"{game['title']} - запущено")
                root.geometry("460x300")
                root.resizable(False, False)
                root.configure(bg="#111827")

                def close_game():
                    if not state["running"]:
                        return
                    state["running"] = False
                    if hasattr(self.app_state, "running_games"):
                        self.app_state.running_games[game_id] = False
                    if getattr(self.app_state, "active_game_id", None) == game_id:
                        self.app_state.active_game_id = None
                    if hasattr(self.app_state, "game_windows"):
                        self.app_state.game_windows.pop(game_id, None)
                    try:
                        root.destroy()
                    except Exception:
                        pass

                tk.Label(root, text=game["title"], bg="#111827", fg="white",
                         font=("Arial", 17, "bold")).pack(pady=(22, 8))
                tk.Label(root, text=game.get("icon") or "🎮", bg="#111827",
                         fg="#7dd3fc", font=("Arial", 54)).pack(pady=(8, 10))
                tk.Label(root, text="Игра запущена", bg="#111827", fg="#fbbf24",
                         font=("Arial", 12, "bold")).pack(pady=4)
                tk.Label(root, text="Окно можно закрыть здесь или из игротеки",
                         bg="#111827", fg="#9ca3af", font=("Arial", 10)).pack(pady=8)
                tk.Button(root, text="Закрыть игру", bg="#555555", fg="white",
                          font=("Arial", 11, "bold"), relief=tk.FLAT,
                          padx=24, pady=8, command=close_game).pack(pady=14)
                
                root.protocol("WM_DELETE_WINDOW", close_game)
                root.mainloop()

                # На случай, если вышли из mainloop без вызова close_game
                if state["running"]:
                    close_game()

            threading.Thread(target=run_window, daemon=True).start()
            print(f"[Python Лаунчер] Заглушка запущена: {game_id}")
            return {"status": "success", "game_id": game_id, "running": True}

        except Exception as exc:
            print(f"[Python Лаунчер] Ошибка запуска игры: {exc}")
            return {"status": "error", "message": str(exc)}

    def stop_game_by_id(self, game_id):
        try:
            game_id = str(game_id)
            
            # 1. Если это реальный процесс (it_magnat)
            real_procs = getattr(self.app_state, "real_processes", {})
            real_proc = real_procs.pop(game_id, None)
            if real_proc is not None:
                if real_proc.poll() is None:
                    real_proc.terminate()
                if hasattr(self.app_state, "running_games"):
                    self.app_state.running_games[game_id] = False
                if getattr(self.app_state, "active_game_id", None) == game_id:
                    self.app_state.active_game_id = None
                return {"status": "success", "game_id": game_id, "running": False}

            # 2. Если это заглушка (Tkinter)
            if hasattr(self.app_state, "running_games"):
                self.app_state.running_games[game_id] = False
            if getattr(self.app_state, "active_game_id", None) == game_id:
                self.app_state.active_game_id = None
            
            state = getattr(self.app_state, "game_windows", {}).pop(game_id, None)
            if state and isinstance(state, dict):
                state["running"] = False
                root = state.get("root")
                if root:
                    try:
                        root.after(0, root.destroy)
                    except Exception:
                        pass
            return {"status": "success", "game_id": game_id, "running": False}

        except Exception as exc:
            print(f"[Python Лаунчер] Ошибка закрытия игры: {exc}")
            return {"status": "error", "message": str(exc)}
    # --- РАБОТА С ТВОИМ ПРОФИЛЕМ ---
    def get_user_profile_data(self):
        try:
            from tools.auth_db import get_current_user, get_user_avatar, get_user_last_seen
            from tools.supabase_client import is_supabase_configured
            from tools.cache import cache_get, cache_set

            user_data = get_current_user()
            if user_data:
                nick = user_data[0]
                cache_key = f"profile:{nick}"
                cached = cache_get(cache_key)
                if cached is not None:
                    return cached
                phone = user_data[1] if len(user_data) > 1 else "Не указан"
                avatar = get_user_avatar(nick) or "👤"
                profile = {
                    "nickname": nick,
                    "phone": phone,
                    "avatar": avatar,
                    "status": "Разработчик",
                    "last_seen": get_user_last_seen(nick),
                    "sync_status": "Supabase (облако)" if is_supabase_configured() else "Локальная БД",
                    "uuid": user_data[2] if len(user_data) > 2 else "",
                }
                cache_set(cache_key, profile)
                return profile
        except Exception as e:
            print(f"[Python Профиль] Ошибка сбора данных: {e}")

        return {
            "nickname": "Авторизуйтесь",
            "phone": "Нет сессии",
            "avatar": "👤",
            "status": "Гость",
            "sync_status": "—",
        }

    # --- РАБОТА С ТВОИМ ЧАТОМ ---
    def get_launcher_chat_messages(self):
        """Читаем историю сообщений из облачного хранилища"""
        try:
            from tools.auth_db import get_current_user
            from tools.supabase_client import load_json_store
            import datetime
            import base64

            user_data = get_current_user()
            my_nick = user_data[0] if user_data else ""
            rows = load_json_store("messages", default=[])
            rows = sorted(rows, key=lambda r: r.get("id", 0))
            rows = rows[-50:]
            
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
                sender = row.get("sender", "")
                content_raw = row.get("content")
                timestamp = format_chat_date(row.get("timestamp")) if row.get("timestamp") else ""
                is_image = int(row.get("is_image", 0))
                
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
            from tools.auth_db import get_current_user
            import base64
            from tools.chat_db import get_chat_history, mark_as_read

            user_data = get_current_user()
            my_nick = user_data[0] if user_data else ""
            if not my_nick or not partner:
                return []

            # Отмечаем как прочитанные ИМЕННО в момент, когда пользователь реально открыл этот чат
            mark_as_read(my_nick, partner)

            history = get_chat_history(my_nick, partner)
            messages_list = []
            for row in history:
                sender, content_raw, time_str, is_image, msg_id = row[:5]
                is_read = row[5] if len(row) > 5 else 0
                if is_image and isinstance(content_raw, bytes):
                    try:
                        b64_data = base64.b64encode(content_raw).decode('utf-8')
                        content_text = f"data:image/png;base64,{b64_data}"
                    except Exception:
                        content_text = "[Ошибка изображения]"
                else:
                    if isinstance(content_raw, bytes):
                        try:
                            content_text = content_raw.decode('utf-8')
                        except Exception:
                            content_text = content_raw.decode('latin-1', errors='ignore')
                    else:
                        content_text = str(content_raw)

                messages_list.append({
                    "id": msg_id,
                    "sender": sender,
                    "text": content_text,
                    "time": time_str,
                    "is_me": sender == my_nick,
                    "is_image": bool(is_image),
                    "is_read": bool(is_read),
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
        """Получаем список твоих друзей из базы данных, с количеством непрочитанных"""
        try:
            from tools.auth_db import get_current_user, get_user_last_seen
            from tools.chat_db import get_friends_list, get_unread_count
            user_data = get_current_user()
            if not user_data: return []
            my_nick = user_data[0]
            friends_list = get_friends_list(my_nick)
            return [{
                "name": f,
                "last_seen": get_user_last_seen(f),
                "unread": get_unread_count(my_nick, f),
            } for f in friends_list]
        except Exception as e:
            print(f"[Python Друзья] Ошибка получения списка: {e}")
            return []

    def add_launcher_friend_by_phone(self, phone):
        """Добавление друга по номеру телефона через облачный backend"""
        try:
            from tools.auth_db import get_current_user, get_nickname_by_phone
            from tools.chat_db import send_friend_request
            user_data = get_current_user()
            if not user_data: return {"status": "error", "message": "Вы не авторизованы"}
            my_nick = user_data[0]
            friend_nick = get_nickname_by_phone(phone.strip())
            if not friend_nick:
                return {"status": "error", "message": "Пользователь с таким номером не найден"}
            if friend_nick == my_nick:
                return {"status": "error", "message": "Нельзя добавить самого себя"}
            res = send_friend_request(my_nick, friend_nick)
            if res.get("status") == "success":
                return {"status": "success", "message": f"Заявка отправлена пользователю {friend_nick}!"}
            return res
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
        """Регистрация нового пользователя через облачный backend"""
        try:
            from tools.auth_db import register_user, is_user_exists

            if not nickname.strip() or not phone.strip() or not password.strip():
                return {"status": "error", "message": "Заполните все поля!"}
            if is_user_exists(nickname.strip(), phone.strip()):
                return {"status": "error", "message": "Этот никнейм уже занят"}
            success = register_user(nickname.strip(), phone.strip(), password)
            if success:
                return {"status": "success", "message": "Регистрация успешна! Теперь вы можете войти."}
            return {"status": "error", "message": "Ошибка регистрации"}
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
    import ctypes

    def is_webview2_installed():
        # WebView2 Runtime прописывает себя в реестре по этим путям (32-бит и 64-бит машины)
        import winreg
        paths = [
            r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
            r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        ]
        for path in paths:
            try:
                winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                return True
            except FileNotFoundError:
                continue
        return False

    if not is_webview2_installed():
        ctypes.windll.user32.MessageBoxW(
            0,
            "Для запуска лаунчера нужен Microsoft Edge WebView2 Runtime.\n\n"
            "Скачай и установи его отсюда:\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
            "После установки запусти лаунчер снова.",
            "Не найден WebView2 Runtime",
            0x10
        )
        exit(1)

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

    webview.start(gui='edgechromium')