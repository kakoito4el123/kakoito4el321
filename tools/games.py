import tkinter as tk
from tools.theme import get_theme
from tools.games_db import get_games_from_db

def create_games_catalog(parent, app_state=None):
    theme = get_theme()
    
    current_game = None
    grid_buttons = []  
    selected_btn = None  
    
    # Флаг, разрешено ли закрыть игру (для фикса кнопки ЗАКРЫТЬ)
    can_close = False  

    genre_colors = {
        "Стратегия": ("#2f5d8c", "#7db8ff"),
        "Аркада": ("#7a2f6a", "#ff8ee6"),
        "Гонки": ("#7a3a1f", "#ffb36b"),
        "РПГ": ("#4f2d7a", "#b48cff"),
        "Симулятор": ("#2f6a4f", "#71e0a5")
    }

    display_icons = {
        "it_magnat": "💻",
        "snake": "🐍",
        "cyber_race": "🏁",
        "dungeon_crawler": "🗡️",
        "space_def": "🚀",
        "farm_sim": "🌾"
    }

    # Глобальный уничтожитель окна: независимый от экземпляра каталога
    def _global_close_window(wnd):
        try:
            if getattr(wnd, "_destroying", False):
                return
            wnd._destroying = True
        except Exception:
            pass
        try:
            if wnd is not None and getattr(wnd, "winfo_exists", lambda: False)():
                wnd.destroy()
        except Exception:
            pass

        try:
            app = getattr(wnd, "_app_state", None)
            gid = getattr(wnd, "_game_id", None)
            if app is not None:
                app.active_game_window = None
                app.active_game_id = None
                if gid is not None:
                    app.running_games[gid] = False
        except Exception:
            pass

    if app_state is not None and hasattr(app_state, "running_games"):
        game_state = app_state
    else:
        class DummyAppState:
            def __init__(self):
                self.running_games = {}
        game_state = DummyAppState()
    # Ensure launch_complete dict exists on app_state to track when loading finished
    if not hasattr(game_state, "launch_complete"):
        try:
            game_state.launch_complete = {}
        except Exception:
            pass

    # Главный контейнер
    main_frame = tk.Frame(parent, bg=theme["bg"])
    
    # --- ЛЕВЫЙ БЛОК ---
    left_pane = tk.Frame(main_frame, bg=theme["bg"], width=380)
    left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=10)
    left_pane.pack_propagate(False)

    filter_frame = tk.Frame(left_pane, bg=theme["entry_bg"], bd=1, relief=tk.SOLID, padx=10, pady=10)
    filter_frame.pack(fill=tk.X, pady=(0, 10))
    
    tk.Label(filter_frame, text="🔍 Поиск игр:", bg=theme["entry_bg"], fg=theme["text"], font=("Arial", 10, "bold")).pack(anchor="w")
    
    search_var = tk.StringVar()
    search_entry = tk.Entry(filter_frame, textvariable=search_var, bg=theme["bg"], fg=theme["text"], insertbackground=theme["text"], relief=tk.FLAT)
    search_entry.pack(fill=tk.X, pady=(2, 8))
    
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

    # --- ПРАВЫЙ БЛОК ---
    right_pane = tk.Frame(main_frame, bg=theme["entry_bg"], padx=15, pady=15, bd=1, relief=tk.SOLID, width=420)
    right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 10), pady=10)
    right_pane.pack_propagate(False)

    animation_id = None
    game_window = None
    runtime_title_label = None
    runtime_status_label = None
    runtime_hint_label = None
    runtime_close_btn = None
    last_filtered_games = []

    # Инициализация всех виджетов правой панели (чтобы Python знал их до вызова функций)
    lbl_game_title = tk.Label(right_pane, text="", font=("Arial", 16, "bold"), bg=theme["entry_bg"], fg=theme["accent"])
    lbl_meta = tk.Label(right_pane, text="", justify=tk.LEFT, font=("Arial", 10), bg=theme["entry_bg"], fg=theme["muted_text"])

    launch_frame = tk.Frame(right_pane, bg=theme["entry_bg"])
    launch_frame.columnconfigure(0, minsize=150)
    launch_frame.columnconfigure(1, weight=1)

    btn_launch = tk.Button(launch_frame, text="▶   ЗАПУСТИТЬ", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), relief=tk.FLAT, padx=20, pady=8)
    btn_stop = tk.Button(launch_frame, text="✖   ЗАКРЫТЬ", bg="#555555", fg="white", font=("Arial", 12, "bold"), relief=tk.FLAT, padx=25, pady=8)
    lbl_status = tk.Label(launch_frame, bg=theme["entry_bg"], font=("Arial", 10, "italic"))

    separator = tk.Frame(right_pane, height=2, bg=theme["bg"])
    lbl_about_header = tk.Label(right_pane, text="О ПРИЛОЖЕНИИ", font=("Arial", 11, "bold"), bg=theme["entry_bg"], fg=theme["text"])
    lbl_desc = tk.Label(right_pane, text="", wrap=380, justify=tk.LEFT, font=("Arial", 10), bg=theme["entry_bg"], fg=theme["text"])

    lbl_empty_state = tk.Label(right_pane, text="🎮 Выберите игру из списка,\nчтобы увидеть описание и запустить", 
                               font=("Arial", 12, "italic"), bg=theme["entry_bg"], fg=theme["muted_text"], justify=tk.CENTER)

    def safe_grid_remove(widget):
        if widget is None:
            return
        try:
            if widget.winfo_exists() and widget.winfo_ismapped():
                widget.grid_remove()
        except tk.TclError:
            pass

    def safe_widget_config(widget, **kwargs):
        if widget is None:
            return
        try:
            if widget.winfo_exists():
                widget.config(**kwargs)
        except tk.TclError:
            pass

    # --- ВЫДЕЛЕННАЯ ФУНКЦИЯ ОЧИСТКИ (БОЛЬШЕ НИКОГО НЕ РЕЖЕТ) ---
    def show_empty_right_pane():
        lbl_game_title.pack_forget()
        lbl_meta.pack_forget()
        launch_frame.pack_forget()
        separator.pack_forget()
        lbl_about_header.pack_forget()
        lbl_desc.pack_forget()
        lbl_empty_state.pack(expand=True)

    # --- ФУНКЦИИ ЗАПУСКА И ЗАКРЫТИЯ ---
    def close_runtime_window(force_game_id=None, window_ref=None):
        # Always operate on the actual runtime window reference passed or on app_state.active_game_window.
        nonlocal game_window, animation_id, runtime_title_label, runtime_status_label, runtime_hint_label, runtime_close_btn
        if animation_id:
            try:
                parent.after_cancel(animation_id)
            except Exception:
                pass
            animation_id = None

        # Determine which window to close and use global closer
        target = window_ref or getattr(game_state, "active_game_window", None) or game_window
        if target is not None:
            try:
                _global_close_window(target)
            except Exception:
                try:
                    if target.winfo_exists():
                        target.destroy()
                except Exception:
                    pass

        # If the destroyed window was the local reference, clear it
        if game_window is not None and (window_ref is None or window_ref is game_window):
            game_window = None
            runtime_title_label = None
            runtime_status_label = None
            runtime_hint_label = None
            runtime_close_btn = None

        # Clearing handled by global closer; ensure UI updates after a short delay
        def delayed_ui_clear():
            try:
                update_launch_ui(is_running=False)
            except Exception:
                pass

        parent.after(120, delayed_ui_clear)
        # Also reset launch_complete flag for the closed game
        try:
            gid = force_game_id or getattr(game_state, "active_game_id", None) or (current_game["id"] if current_game else None)
            if gid is not None:
                game_state.launch_complete[gid] = False
        except Exception:
            pass

    def open_runtime_window():
        nonlocal game_window, runtime_title_label, runtime_status_label, runtime_hint_label, runtime_close_btn
        if not current_game:
            return

        # If there's already an active runtime window in app state, respect it.
        existing = getattr(game_state, "active_game_window", None)
        existing_id = getattr(game_state, "active_game_id", None)
        if existing is not None and getattr(existing, "winfo_exists", lambda: False)():
            # If it's the same game, just focus it
            if existing_id == current_game["id"]:
                try:
                    existing.lift()
                    existing.focus_force()
                except tk.TclError:
                    pass
                return
            # If it's a different game, close it deterministically first
            close_runtime_window(force_game_id=existing_id, window_ref=existing)

        root = parent.winfo_toplevel()
        game_window = tk.Toplevel(root)
        game_state.active_game_window = game_window
        game_state.active_game_id = current_game["id"]
        game_window.title(f"{current_game['title']} — запущено")
        game_window.geometry("440x270")
        game_window.resizable(False, False)
        game_window.configure(bg="#111827")
        game_window.attributes("-topmost", True)

        runtime_title_label = tk.Label(game_window, text=current_game["title"], bg="#111827", fg="white",
                                       font=("Arial", 16, "bold"))
        runtime_title_label.pack(pady=(18, 8))

        runtime_icon_label = tk.Label(game_window, text=display_icons.get(current_game["id"], current_game["icon"]),
                                      bg="#111827", fg="#7dd3fc", font=("Arial", 48))
        runtime_icon_label.pack(pady=(6, 12))

        runtime_status_label = tk.Label(game_window, text="Подготовка к запуску...", bg="#111827", fg="#60a5fa",
                                         font=("Arial", 12, "bold"))
        runtime_status_label.pack(pady=6)

        runtime_hint_label = tk.Label(game_window, text="Открываем окно игры…", bg="#111827",
                                      fg="#9ca3af", font=("Arial", 10))
        runtime_hint_label.pack(pady=8)

        # Bind the close button to this exact window and game id so it cannot get stale
        this_id = current_game["id"]
        # Attach app_state and id to the window so global closer can work
        try:
            game_window._app_state = game_state
            game_window._game_id = this_id
            game_window._destroying = False
        except Exception:
            pass

        def close_this_window_local(w=this_id, wnd=game_window):
            # Prefer global closer to ensure deterministic behavior across instances
            _global_close_window(wnd)

        # Set close button state depending on whether launch is complete for this game
        start_state = tk.NORMAL if game_state.launch_complete.get(this_id, False) else tk.DISABLED
        runtime_close_btn = tk.Button(game_window, text=("Закрыть игру" if start_state==tk.NORMAL else "Подождите..."), bg="#ef4444", fg="white",
                          font=("Arial", 11, "bold"), command=lambda: _global_close_window(game_window), state=start_state)
        runtime_close_btn.pack(pady=16)

        # Ensure window manager close also uses the same deterministic closer
        game_window.protocol("WM_DELETE_WINDOW", lambda: _global_close_window(game_window))

    def update_launch_ui(is_running, is_loading=False):
        if is_running:
            safe_grid_remove(btn_launch)
            if btn_stop.winfo_exists():
                btn_stop.grid(row=0, column=0, sticky="w")
            # If the game is still loading (not completed), keep stop disabled
            gid = None
            try:
                gid = current_game["id"] if current_game else getattr(game_state, "active_game_id", None)
            except Exception:
                gid = getattr(game_state, "active_game_id", None)
            launching = False
            if gid is not None:
                launching = not game_state.launch_complete.get(gid, False)
            safe_widget_config(btn_stop, state=tk.DISABLED if launching else tk.NORMAL,
                               bg="#333333" if launching else "#555555",
                               fg="#777777" if launching else "white")
            safe_widget_config(lbl_status, text="⏳ Идёт запуск..." if is_loading else "● Игра запущена",
                               fg="#007acc" if is_loading else "#FFA000")
            if lbl_status.winfo_exists():
                lbl_status.grid(row=0, column=1, padx=20, sticky="w")
        else:
            safe_grid_remove(btn_stop)
            if btn_launch.winfo_exists():
                btn_launch.grid(row=0, column=0, sticky="w")
            safe_widget_config(lbl_status, text="● Готова к запуску", fg="#4CAF50")
            if lbl_status.winfo_exists():
                lbl_status.grid(row=0, column=1, padx=20, sticky="w")
        # Update runtime_close_btn state to reflect launch_complete as well
        try:
            gid2 = current_game["id"] if current_game else getattr(game_state, "active_game_id", None)
            if gid2 is not None and runtime_close_btn is not None and getattr(runtime_close_btn, "winfo_exists", lambda: False)():
                if game_state.launch_complete.get(gid2, False):
                    runtime_close_btn.config(state=tk.NORMAL, text="Закрыть игру")
                else:
                    runtime_close_btn.config(state=tk.DISABLED, text="Подождите...")
        except Exception:
            pass

    def start_game_action():
        nonlocal animation_id
        if not current_game:
            return

        game_id = current_game["id"]
        # If the game is marked running, ensure its window exists; if so, focus it. If not, clear the flag.
        if game_state.running_games.get(game_id, False):
            existing = getattr(game_state, "active_game_window", None)
            # block relaunch if window is currently destroying
            if existing is not None:
                if getattr(existing, "_destroying", False):
                    return
                if getattr(existing, "winfo_exists", lambda: False)():
                    try:
                        existing.lift()
                        existing.focus_force()
                    except tk.TclError:
                        pass
                    update_launch_ui(is_running=True, is_loading=False)
                    return
            # stale flag — clear it so a fresh launch can occur
            game_state.running_games[game_id] = False

        if hasattr(game_state, "active_game_id") and game_state.active_game_id and game_state.active_game_id != game_id:
            close_runtime_window(force_game_id=game_state.active_game_id, window_ref=game_state.active_game_window)

        game_state.running_games[game_id] = True
        update_launch_ui(is_running=True, is_loading=True)
        # Ensure we schedule animation on the application root so it survives page/frame redraws
        app_root = parent.winfo_toplevel()
        open_runtime_window()
        # If runtime_close_btn exists, allow user to close during launch
        try:
            if runtime_close_btn is not None and runtime_close_btn.winfo_exists():
                runtime_close_btn.config(state=tk.NORMAL, text="Закрыть игру")
        except Exception:
            pass

        if animation_id:
            try:
                parent.after_cancel(animation_id)
            except Exception:
                pass
            animation_id = None

        def animate(step=0):
            nonlocal animation_id
            # Stop if the game window no longer exists or the game is not marked running
            if game_window is None or not (game_window is not None and getattr(game_window, "winfo_exists", lambda: False)()):
                animation_id = None
                return
            if not (current_game and game_state.running_games.get(current_game["id"], False)):
                animation_id = None
                return
            # Proceed to update UI where widgets still exist
            try:
                chars = ['▖', '▘', '▝', '▗']
            except Exception:
                chars = ['-', '\\', '|', '/']
            if step < 25:
                try:
                    safe_widget_config(lbl_status, text=f"⏳ Запуск {chars[step % 4]}", fg="#007acc")
                    if runtime_status_label is not None and getattr(runtime_status_label, "winfo_exists", lambda: False)():
                        runtime_status_label.config(text=f"Запуск {chars[step % 4]}", fg="#60a3fa")
                    if runtime_hint_label is not None and getattr(runtime_hint_label, "winfo_exists", lambda: False)():
                        runtime_hint_label.config(text="Открываем окно игры…", fg="#9ca3af")
                    # Allow closing during launch: keep close button enabled
                        if runtime_close_btn is not None and getattr(runtime_close_btn, "winfo_exists", lambda: False)():
                            # keep close disabled until launch completes
                            runtime_close_btn.config(text="Подождите...", state=tk.DISABLED)
                        animation_id = app_root.after(200, lambda: animate(step + 1))
                except tk.TclError:
                    animation_id = None
            else:
                try:
                        # Mark launch complete for this game id so both UI sides know
                        try:
                            gid_local = current_game["id"] if current_game else None
                            if gid_local is not None:
                                game_state.launch_complete[gid_local] = True
                        except Exception:
                            pass
                        safe_widget_config(lbl_status, text="● Игра запущена", fg="#FFA000")
                        safe_widget_config(btn_stop, state=tk.NORMAL, bg="#555555", fg="white")
                        if runtime_status_label is not None and getattr(runtime_status_label, "winfo_exists", lambda: False)():
                            runtime_status_label.config(text="Игра запущена", fg="#fbbf24")
                        if runtime_hint_label is not None and getattr(runtime_hint_label, "winfo_exists", lambda: False)():
                            runtime_hint_label.config(text="Окно остаётся открытым при смене вкладок", fg="#9ca3af")
                        if runtime_close_btn is not None and getattr(runtime_close_btn, "winfo_exists", lambda: False)():
                            runtime_close_btn.config(text="Закрыть игру", state=tk.NORMAL)
                except tk.TclError:
                    pass
                animation_id = None

        animate()

    def stop_game_action():
        nonlocal animation_id
        if animation_id:
            parent.after_cancel(animation_id)
            animation_id = None

        # Use app-level window reference if available; ensures we close the actual runtime window
        wnd = getattr(game_state, "active_game_window", None)
        gid = current_game["id"] if current_game else getattr(game_state, "active_game_id", None)
        if wnd is not None:
            _global_close_window(wnd)
        else:
            close_runtime_window(force_game_id=gid, window_ref=wnd)

    # Привязываем функции к кнопкам после их объявления
    btn_launch.config(command=start_game_action)
    btn_stop.config(command=stop_game_action)

    # --- ЦЕЛЬНАЯ ФУНКЦИЯ ВЫБОРА ИГРЫ ---
    def select_game(game, btn, event=None):
        nonlocal current_game, selected_btn, animation_id
        if animation_id:
            parent.after_cancel(animation_id)
            animation_id = None

        current_game = game
        
        if selected_btn and selected_btn in grid_buttons:
            try: selected_btn.config(bg=theme["entry_bg"])
            except: pass
            
        selected_btn = btn
        btn.config(bg=theme["sidebar_bg"])

        lbl_empty_state.pack_forget()
        lbl_game_title.pack(anchor="w", pady=(0, 5))
        lbl_meta.pack(anchor="w", pady=(0, 15))
        launch_frame.pack(fill=tk.X, pady=(0, 15))
        separator.pack(fill=tk.X, pady=10)
        lbl_about_header.pack(anchor="w", pady=(5, 5))
        lbl_desc.pack(anchor="w")
        
        lbl_game_title.config(text=game["title"])
        meta_text = f"📂 Жанр: {game['genre']}\n📅 Дата выпуска: {game['date']}\n🏢 Издатель: {game['publisher']}\n⭐ Рейтинг: 10 / 10"
        lbl_meta.config(text=meta_text)
        lbl_desc.config(text=game["desc"])
        
        # Обновляем состояние интерфейса в зависимости от того, запущена игра или нет
        is_running = game_state.running_games.get(game["id"], False)
        update_launch_ui(is_running=is_running, is_loading=False)

    # --- ФУНКЦИЯ СБРОСА ВЫБОРА ПРИ КЛИКЕ МИМО ---
    def reset_selection(event):
        nonlocal current_game, selected_btn
        if event.widget in [main_frame, left_pane, grid_container, right_pane]:
            if selected_btn:
                try: selected_btn.config(bg=theme["entry_bg"])
                except: pass
            selected_btn = None
            current_game = None
            show_empty_right_pane()

    main_frame.bind("<Button-1>", reset_selection)
    left_pane.bind("<Button-1>", reset_selection)
    grid_container.bind("<Button-1>", reset_selection)

    # --- ФУНКЦИЯ ПОИСКА И ОТРИСОВКИ СЕТКИ ---
    def update_catalog_view(*args):
        nonlocal selected_btn, last_filtered_games
        for btn in grid_buttons:
            btn.grid_forget()
        grid_buttons.clear()
        selected_btn = None
        
        all_games = get_games_from_db(genre_filter=genre_var.get(), sort_by=sort_var.get())
        search_query = search_var.get().lower().strip()
        
        filtered_games = []
        for g in all_games:
            # Поиск строго по первым буквам
            if not search_query or g["title"].lower().startswith(search_query):
                filtered_games.append(g)
        # remember filtered list for possible auto-selection after redraw
        last_filtered_games = filtered_games
            
        def bind_click_recursive(widget, callback):
            widget.bind("<Button-1>", callback)
            for child in widget.winfo_children():
                bind_click_recursive(child, callback)

        for i, game in enumerate(filtered_games):
            row = i // 2
            col = i % 2

            btn_frame = tk.Frame(grid_container, width=170, height=128, bg=theme["bg"])
            btn_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            btn_frame.pack_propagate(False)

            card_bg, icon_bg = genre_colors.get(game["genre"], (theme["entry_bg"], theme["accent"]))
            display_icon = display_icons.get(game["id"], game["icon"])

            card = tk.Frame(btn_frame, bg=card_bg, bd=0, padx=0, pady=0)
            card.pack(fill=tk.BOTH, expand=True)
            card.config(highlightthickness=1, highlightbackground=theme["bg"], highlightcolor=theme["bg"])

            icon_area = tk.Frame(card, bg=icon_bg, height=78)
            icon_area.pack(fill=tk.X)
            icon_area.pack_propagate(False)

            icon_label = tk.Label(icon_area, text=display_icon, bg=icon_bg, fg="white",
                                  font=("Arial", 48), pady=8)
            icon_label.pack(expand=True)

            # Hover for icon: scale and change background slightly
            def icon_hover_in(ev, lbl=icon_label, base_bg=icon_bg):
                try:
                    lbl.config(font=("Arial", 56), bg=theme["sidebar_bg"])
                except Exception:
                    pass

            def icon_hover_out(ev, lbl=icon_label, base_bg=icon_bg):
                try:
                    lbl.config(font=("Arial", 48), bg=base_bg)
                except Exception:
                    pass

            icon_label.bind("<Enter>", icon_hover_in)
            icon_label.bind("<Leave>", icon_hover_out)

            title_area = tk.Frame(card, bg=card_bg, padx=6, pady=8)
            title_area.pack(fill=tk.BOTH, expand=True)

            title_label = tk.Label(title_area, text=game["title"], bg=card_bg, fg="white",
                                   font=("Arial", 9, "bold"), wraplength=140, justify=tk.CENTER)
            title_label.pack(expand=True)

            genre_label = tk.Label(title_area, text=game["genre"], bg=card_bg, fg="#f3f3f3",
                                   font=("Arial", 8))
            genre_label.pack(pady=(2, 0))

            card.config(cursor="hand2")

            def on_enter(e, b=card, base_bg=card_bg, base_icon=icon_bg):
                try:
                    if b != selected_btn:
                        b.config(bg=theme["sidebar_bg"])
                        if b.winfo_children():
                            b.winfo_children()[0].config(bg=theme["accent"])
                            if b.winfo_children()[0].winfo_children():
                                b.winfo_children()[0].winfo_children()[0].config(bg=theme["accent"])
                except Exception:
                    pass
            def on_leave(e, b=card, base_bg=card_bg, base_icon=icon_bg):
                try:
                    if b != selected_btn:
                        b.config(bg=base_bg)
                        if b.winfo_children():
                            b.winfo_children()[0].config(bg=base_icon)
                            if b.winfo_children()[0].winfo_children():
                                b.winfo_children()[0].winfo_children()[0].config(bg=base_icon)
                except Exception:
                    pass

            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            bind_click_recursive(btn_frame, lambda e, g=game, b=card: select_game(g, b))

            grid_buttons.append(btn_frame)
            
        show_empty_right_pane()

    search_var.trace_add("write", update_catalog_view)

    update_catalog_view()
    show_empty_right_pane()

    # Если ранее была выбрана или запущена игра, восстановим её выбор при открытии страницы
    try:
        active_gid = getattr(game_state, "active_game_id", None)
        if active_gid:
            for idx, g in enumerate(last_filtered_games):
                if g["id"] == active_gid and idx < len(grid_buttons):
                    select_game(g, grid_buttons[idx])
                    break
    except Exception:
        pass

    return main_frame