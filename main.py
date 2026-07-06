import tkinter as tk
from types import SimpleNamespace
from tkinter import messagebox
from tools.randomizer import create_randomizer
from tools.todo import create_todo
from tools.timer import create_timer
from tools.auth_db import init_auth_db, check_session_timeout, logout_user
from tools.auth_ui import show_auth_window
from tools.profile import create_profile
from tools.chat import create_chat
from tools.chat_db import init_chat_db
from tools.theme import get_theme, toggle_theme, is_dark
from tools.games import create_games_catalog
from tools.games_db import init_games_db

class MultiToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modular Python Tool")
        self.root.geometry("1200x700")

        # Текущая открытая страница — нужно, чтобы перерисовать её при смене темы
        self.current_page_func = None
        self.app_state = SimpleNamespace(running_games={}, active_game_window=None, active_game_id=None)

        # 1. Инициализируем БД
        init_auth_db()
        init_chat_db()
        init_games_db() # <-- Запускаем создание нашей отдельной базы игр

        # Панели
        self.sidebar = tk.Frame(self.root, width=150)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        self.top_bar = tk.Frame(self.root, height=40)
        self.top_bar.pack(side=tk.TOP, fill=tk.X)

        self.main_area = tk.Frame(self.root)
        self.main_area.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        self.setup_menu()
        self.show_main_menu()
        self.apply_theme()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- ПРОВЕРКА ЛОГИНА ---
        if check_session_timeout():
            self.root.withdraw()
            show_auth_window(self.root, lambda: self.root.deiconify())

    def setup_menu(self):
            # Чистим сайдбар (нужно при перерисовке темы)
            for w in self.sidebar.winfo_children():
                w.destroy()

            theme = get_theme()
            self.sidebar.config(bg=theme["sidebar_bg"])

            nav_buttons = [
                ("🏠 Главная", self.show_main_menu),
                ("🎲 Рандом", lambda: self.switch_page(create_randomizer)),
                ("📝 Заметки", lambda: self.switch_page(create_todo)),
                ("⏰ Таймер", lambda: self.switch_page(create_timer)),
                ("🎮 Игротека", lambda: self.switch_page(create_games_catalog)),
                ("👤 Профиль", lambda: self.switch_page(create_profile)),
                ("💬 Чат", lambda: self.switch_page(create_chat)),
            ]
            for label, cmd in nav_buttons:
                tk.Button(self.sidebar, text=label, command=cmd,
                        bg=theme["sidebar_bg"], fg="white", activebackground=theme["accent"],
                        relief=tk.FLAT, anchor="w").pack(fill=tk.X, padx=5, pady=2)

            # Переключатель темы
            theme_label = "☀️ Светлая тема" if is_dark() else "🌙 Тёмная тема"
            tk.Button(self.sidebar, text=theme_label, command=self.handle_toggle_theme,
                    bg=theme["accent"], fg="white", relief=tk.FLAT).pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))

    def handle_toggle_theme(self):
        toggle_theme()
        self.apply_theme()

    def apply_theme(self):
        theme = get_theme()
        self.root.config(bg=theme["bg"])
        self.top_bar.config(bg=theme["topbar_bg"])
        self.main_area.config(bg=theme["bg"])
        self.setup_menu()
        # Перерисовываем текущую страницу с новыми цветами
        if self.current_page_func is None:
            self.show_main_menu()
        else:
            self.switch_page(self.current_page_func)

    def on_close(self):
        if getattr(self.app_state, "active_game_window", None) is not None:
            try:
                self.app_state.active_game_window.destroy()
            except tk.TclError:
                pass
            self.app_state.active_game_window = None
            self.app_state.active_game_id = None
        try:
            self.root.destroy()
        except tk.TclError:
            try:
                # As a fallback, try quitting the mainloop then destroying
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass

    def handle_logout(self):
            """Разлогинивает пользователя и возвращает на окно авторизации без закрытия приложения"""
            logout_user() # Удаляем session.txt
            
            # Сбрасываем состояние приложения в дефолт
            self.current_page_func = None
            self.clear_screen()
            
            # Прячем главное окно и вызываем авторизацию
            self.root.withdraw()
            show_auth_window(self.root, lambda: [self.root.deiconify(), self.show_main_menu()])

    def clear_screen(self):
        for w in self.main_area.winfo_children(): w.destroy()
        for w in self.top_bar.winfo_children(): w.destroy()

    def switch_page(self, create_func):
            self.current_page_func = create_func
            self.clear_screen()
            theme = get_theme()
            tk.Button(self.top_bar, text="← Назад", command=self.show_main_menu,
                    bg=theme["topbar_bg"], relief=tk.FLAT).pack(side=tk.LEFT, padx=10)
            
            # Передаем колбэк handle_logout в профиль или чат, если они его поддерживают
            if create_func in (create_profile, create_chat):
                page_frame = create_func(self.main_area, on_logout=self.handle_logout)
            elif create_func is create_games_catalog:
                page_frame = create_func(self.main_area, app_state=self.app_state)
            else:
                page_frame = create_func(self.main_area)
                
            page_frame.pack(fill=tk.BOTH, expand=True)



    def show_main_menu(self):
        self.current_page_func = None
        self.clear_screen()
        theme = get_theme()
        tk.Label(self.main_area, text="ГЛАВНОЕ МЕНЮ", font=("Arial", 20),
                 bg=theme["bg"], fg=theme["text"]).pack(pady=50)

if __name__ == "__main__":
    root = tk.Tk()
    app = MultiToolApp(root)
    root.mainloop()
