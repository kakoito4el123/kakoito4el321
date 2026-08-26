import tkinter as tk
import time
from tools.theme import get_theme
from tools.games_db import get_games_from_db

LAUNCH_SECONDS = 5.0     # сколько "грузится" игра
UI_REFRESH_MS = 250      # как часто перерисовываем статус (и в каталоге, и в окне игры)


def create_games_catalog(parent, app_state=None):
    theme = get_theme()

    genre_colors = {
        "Стратегия": ("#2f5d8c", "#7db8ff"),
        "Аркада": ("#7a2f6a", "#ff8ee6"),
        "Гонки": ("#7a3a1f", "#ffb36b"),
        "РПГ": ("#4f2d7a", "#b48cff"),
        "Симулятор": ("#2f6a4f", "#71e0a5"),
    }
    display_icons = {
        "it_magnat": "💻", "snake": "🐍", "cyber_race": "🏁",
        "dungeon_crawler": "🗡️", "space_def": "🚀", "farm_sim": "🌾",
    }

    # ==========================================================================
    # ЕДИНЫЙ ИСТОЧНИК ПРАВДЫ (живёт в app_state — переживает переключение вкладок)
    # ==========================================================================
    if app_state is None:
        class _Dummy: pass
        game_state = _Dummy()
    else:
        game_state = app_state

    if not hasattr(game_state, "running_games"):
        game_state.running_games = {}       # {game_id: True/False} — запущена ли игра
    if not hasattr(game_state, "launch_started_at"):
        game_state.launch_started_at = {}   # {game_id: timestamp} — когда нажали "Запустить"
    if not hasattr(game_state, "game_windows"):
        game_state.game_windows = {}        # {game_id: Toplevel} — открытое окно игры

    def is_running(gid):
        return bool(game_state.running_games.get(gid, False))

    def is_loading(gid):
        """Прошло ли меньше 5 секунд с запуска — считаем каждый раз заново, никаких счётчиков шагов."""
        if not is_running(gid):
            return False
        started = game_state.launch_started_at.get(gid)
        if started is None:
            return False
        return (time.time() - started) < LAUNCH_SECONDS

    def start_game(gid):
        # Одновременно "запущена" только одна игра — если была другая, сначала закрываем её.
        for other_gid in list(game_state.running_games.keys()):
            if other_gid != gid and is_running(other_gid):
                stop_game(other_gid)

        game_state.running_games[gid] = True
        game_state.launch_started_at[gid] = time.time()
        ensure_popup(gid)

    def stop_game(gid):
        game_state.running_games[gid] = False
        game_state.launch_started_at.pop(gid, None)
        wnd = game_state.game_windows.pop(gid, None)
        if wnd is not None:
            try:
                if wnd.winfo_exists():
                    wnd.destroy()
            except tk.TclError:
                pass

    def get_game_by_id(gid):
        for g in get_games_from_db():
            if g["id"] == gid:
                return g
        return None

    # ==========================================================================
    # ОКНО ЗАПУЩЕННОЙ ИГРЫ (полностью самодостаточное — само себя обновляет,
    # не зависит от того, жива ли ещё страница каталога)
    # ==========================================================================
    def ensure_popup(gid):
        existing = game_state.game_windows.get(gid)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except tk.TclError:
                pass

        game = get_game_by_id(gid)
        if game is None:
            return

        root = parent.winfo_toplevel()
        wnd = tk.Toplevel(root)
        game_state.game_windows[gid] = wnd
        wnd.title(f"{game['title']} — запущено")
        wnd.geometry("440x270")
        wnd.resizable(False, False)
        wnd.configure(bg="#111827")

        tk.Label(wnd, text=game["title"], bg="#111827", fg="white",
                 font=("Arial", 16, "bold")).pack(pady=(18, 8))
        tk.Label(wnd, text=display_icons.get(gid, game["icon"]), bg="#111827",
                 fg="#7dd3fc", font=("Arial", 48)).pack(pady=(6, 12))

        status_label = tk.Label(wnd, bg="#111827", fg="#60a5fa", font=("Arial", 12, "bold"))
        status_label.pack(pady=6)
        hint_label = tk.Label(wnd, bg="#111827", fg="#9ca3af", font=("Arial", 10))
        hint_label.pack(pady=8)

        close_btn = tk.Button(wnd, text="", bg="#ef4444", fg="white",
                               font=("Arial", 11, "bold"), command=lambda: stop_game(gid))
        close_btn.pack(pady=16)

        wnd.protocol("WM_DELETE_WINDOW", lambda: stop_game(gid))

        def refresh_popup():
            try:
                if not wnd.winfo_exists():
                    return
            except tk.TclError:
                return

            if not is_running(gid):
                return

            if is_loading(gid):
                status_label.config(text="⏳ Запуск...", fg="#60a5fa")
                hint_label.config(text="Открываем окно игры…")
                close_btn.config(text="Подождите...", state=tk.DISABLED, bg="#555555")
            else:
                status_label.config(text="Игра запущена", fg="#fbbf24")
                hint_label.config(text="Окно остаётся открытым при смене вкладок")
                close_btn.config(text="Закрыть игру", state=tk.NORMAL, bg="#ef4444")

            wnd.after(UI_REFRESH_MS, refresh_popup)

        refresh_popup()

    # ==========================================================================
    # СТРАНИЦА КАТАЛОГА
    # ==========================================================================
    current_game = {"value": None}
    grid_buttons = []
    selected_btn = {"value": None}

    main_frame = tk.Frame(parent, bg=theme["bg"])

    left_pane = tk.Frame(main_frame, bg=theme["bg"], width=380)
    left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=10)
    left_pane.pack_propagate(False)

    filter_frame = tk.Frame(left_pane, bg=theme["entry_bg"], bd=1, relief=tk.SOLID, padx=10, pady=10)
    filter_frame.pack(fill=tk.X, pady=(0, 10))
    tk.Label(filter_frame, text="🔍 Поиск игр:", bg=theme["entry_bg"], fg=theme["text"],
             font=("Arial", 10, "bold")).pack(anchor="w")

    search_var = tk.StringVar()
    tk.Entry(filter_frame, textvariable=search_var, bg=theme["bg"], fg=theme["text"],
              insertbackground=theme["text"], relief=tk.FLAT).pack(fill=tk.X, pady=(2, 8))

    sort_frame = tk.Frame(filter_frame, bg=theme["entry_bg"])
    sort_frame.pack(fill=tk.X)

    genres = ["Все", "Стратегия", "Аркада", "Гонки", "РПГ", "Симулятор"]
    genre_var = tk.StringVar(value="Все")
    genre_menu = tk.OptionMenu(sort_frame, genre_var, *genres, command=lambda _: update_catalog_view())
    genre_menu.config(bg=theme["bg"], fg=theme["text"], relief=tk.FLAT, highlightthickness=0, font=("Arial", 9))
    genre_menu.pack(side=tk.LEFT, padx=(0, 15))

    sort_options = ["По алфавиту А-Я", "По алфавиту Я-А"]
    sort_var = tk.StringVar(value="По алфавиту А-Я")
    sort_menu = tk.OptionMenu(sort_frame, sort_var, *sort_options, command=lambda _: update_catalog_view())
    sort_menu.config(bg=theme["bg"], fg=theme["text"], relief=tk.FLAT, highlightthickness=0, font=("Arial", 9))
    sort_menu.pack(side=tk.LEFT)

    grid_container = tk.Frame(left_pane, bg=theme["bg"])
    grid_container.pack(fill=tk.BOTH, expand=True, pady=10)

    right_pane = tk.Frame(main_frame, bg=theme["entry_bg"], padx=15, pady=15, bd=1, relief=tk.SOLID, width=420)
    right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 10), pady=10)
    right_pane.pack_propagate(False)

    lbl_game_title = tk.Label(right_pane, text="", font=("Arial", 16, "bold"), bg=theme["entry_bg"], fg=theme["accent"])
    lbl_meta = tk.Label(right_pane, text="", justify=tk.LEFT, font=("Arial", 10), bg=theme["entry_bg"], fg=theme["muted_text"])

    launch_frame = tk.Frame(right_pane, bg=theme["entry_bg"])
    launch_frame.columnconfigure(0, minsize=150)
    launch_frame.columnconfigure(1, weight=1)

    btn_launch = tk.Button(launch_frame, text="▶   ЗАПУСТИТЬ", bg="#4CAF50", fg="white",
                            font=("Arial", 12, "bold"), relief=tk.FLAT, padx=20, pady=8,
                            command=lambda: current_game["value"] and start_game(current_game["value"]["id"]))
    btn_stop = tk.Button(launch_frame, text="✖   ЗАКРЫТЬ", bg="#555555", fg="white",
                         font=("Arial", 12, "bold"), relief=tk.FLAT, padx=25, pady=8,
                         command=lambda: current_game["value"] and stop_game(current_game["value"]["id"]))
    lbl_status = tk.Label(launch_frame, bg=theme["entry_bg"], font=("Arial", 10, "italic"))

    separator = tk.Frame(right_pane, height=2, bg=theme["bg"])
    lbl_about_header = tk.Label(right_pane, text="О ПРИЛОЖЕНИИ", font=("Arial", 11, "bold"), bg=theme["entry_bg"], fg=theme["text"])
    lbl_desc = tk.Label(right_pane, text="", wrap=380, justify=tk.LEFT, font=("Arial", 10), bg=theme["entry_bg"], fg=theme["text"])
    lbl_empty_state = tk.Label(right_pane, text="🎮 Выберите игру из списка,\nчтобы увидеть описание и запустить",
                                font=("Arial", 12, "italic"), bg=theme["entry_bg"], fg=theme["muted_text"], justify=tk.CENTER)

    def show_empty_right_pane():
        lbl_game_title.pack_forget()
        lbl_meta.pack_forget()
        launch_frame.pack_forget()
        separator.pack_forget()
        lbl_about_header.pack_forget()
        lbl_desc.pack_forget()
        lbl_empty_state.pack(expand=True)

    def render_right_panel():
        """Перерисовывает кнопку/статус ИСКЛЮЧИТЕЛЬНО на основе game_state — никаких ручных 'патчей' по месту."""
        try:
            if not main_frame.winfo_exists():
                return
        except tk.TclError:
            return

        game = current_game["value"]
        if game is not None:
            gid = game["id"]
            if is_running(gid):
                btn_launch.grid_remove()
                btn_stop.grid(row=0, column=0, sticky="w")
                if is_loading(gid):
                    btn_stop.config(state=tk.DISABLED, bg="#333333", fg="#777777")
                    lbl_status.config(text="⏳ Идёт запуск...", fg="#007acc")
                else:
                    btn_stop.config(state=tk.NORMAL, bg="#555555", fg="white")
                    lbl_status.config(text="● Игра запущена", fg="#FFA000")
            else:
                btn_stop.grid_remove()
                btn_launch.grid(row=0, column=0, sticky="w")
                lbl_status.config(text="● Готова к запуску", fg="#4CAF50")
            lbl_status.grid(row=0, column=1, padx=20, sticky="w")

        main_frame.after(UI_REFRESH_MS, render_right_panel)

    def select_game(game, btn):
        current_game["value"] = game

        if selected_btn["value"] is not None:
            try: selected_btn["value"].config(bg=theme["entry_bg"])
            except tk.TclError: pass
        selected_btn["value"] = btn
        btn.config(bg=theme["sidebar_bg"])

        lbl_empty_state.pack_forget()
        lbl_game_title.pack(anchor="w", pady=(0, 5))
        lbl_meta.pack(anchor="w", pady=(0, 15))
        launch_frame.pack(fill=tk.X, pady=(0, 15))
        separator.pack(fill=tk.X, pady=10)
        lbl_about_header.pack(anchor="w", pady=(5, 5))
        lbl_desc.pack(anchor="w")

        lbl_game_title.config(text=game["title"])
        lbl_meta.config(text=(f"📂 Жанр: {game['genre']}\n📅 Дата выпуска: {game['date']}\n"
                               f"🏢 Издатель: {game['publisher']}\n⭐ Рейтинг: 10 / 10"))
        lbl_desc.config(text=game["desc"])

    def reset_selection(event):
        if event.widget in (main_frame, left_pane, grid_container, right_pane):
            if selected_btn["value"] is not None:
                try: selected_btn["value"].config(bg=theme["entry_bg"])
                except tk.TclError: pass
            selected_btn["value"] = None
            current_game["value"] = None
            show_empty_right_pane()

    main_frame.bind("<Button-1>", reset_selection)
    left_pane.bind("<Button-1>", reset_selection)
    grid_container.bind("<Button-1>", reset_selection)
    right_pane.bind("<Button-1>", reset_selection)

    def update_catalog_view(*args):
        for b in grid_buttons:
            b.grid_forget()
        grid_buttons.clear()
        selected_btn["value"] = None

        all_games = get_games_from_db(genre_filter=genre_var.get(), sort_by=sort_var.get())
        query = search_var.get().lower().strip()
        filtered = [g for g in all_games if not query or g["title"].lower().startswith(query)]

        def bind_click_recursive(widget, callback):
            widget.bind("<Button-1>", callback)
            for child in widget.winfo_children():
                bind_click_recursive(child, callback)

        for i, game in enumerate(filtered):
            row, col = divmod(i, 2)
            btn_frame = tk.Frame(grid_container, width=170, height=128, bg=theme["bg"])
            btn_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            btn_frame.pack_propagate(False)

            card_bg, icon_bg = genre_colors.get(game["genre"], (theme["entry_bg"], theme["accent"]))
            display_icon = display_icons.get(game["id"], game["icon"])

            card = tk.Frame(btn_frame, bg=card_bg, cursor="hand2")
            card.pack(fill=tk.BOTH, expand=True)
            card.config(highlightthickness=1, highlightbackground=theme["bg"], highlightcolor=theme["bg"])

            icon_area = tk.Frame(card, bg=icon_bg, height=78)
            icon_area.pack(fill=tk.X)
            icon_area.pack_propagate(False)
            tk.Label(icon_area, text=display_icon, bg=icon_bg, fg="white", font=("Arial", 48), pady=8).pack(expand=True)

            title_area = tk.Frame(card, bg=card_bg, padx=6, pady=8)
            title_area.pack(fill=tk.BOTH, expand=True)
            tk.Label(title_area, text=game["title"], bg=card_bg, fg="white", font=("Arial", 9, "bold"),
                     wraplength=140, justify=tk.CENTER).pack(expand=True)
            tk.Label(title_area, text=game["genre"], bg=card_bg, fg="#f3f3f3", font=("Arial", 8)).pack(pady=(2, 0))

            def on_enter(e, b=card, base_bg=card_bg):
                if b is not selected_btn["value"]:
                    b.config(bg=theme["sidebar_bg"])

            def on_leave(e, b=card, base_bg=card_bg):
                if b is not selected_btn["value"]:
                    b.config(bg=base_bg)

            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            bind_click_recursive(btn_frame, lambda e, g=game, b=card: select_game(g, b))
            grid_buttons.append(btn_frame)

        show_empty_right_pane()

    search_var.trace_add("write", update_catalog_view)
    update_catalog_view()
    show_empty_right_pane()

    for gid, running in list(game_state.running_games.items()):
        if running:
            game = get_game_by_id(gid)
            if game:
                for idx, g in enumerate(get_games_from_db(genre_filter=genre_var.get(), sort_by=sort_var.get())):
                    if g["id"] == gid and idx < len(grid_buttons):
                        select_game(g, grid_buttons[idx])
                        break
            break

    render_right_panel()
    return main_frame