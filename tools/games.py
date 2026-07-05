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
    def start_game_action():
        nonlocal animation_id
        if app_state and current_game:
            app_state.running_games[current_game["id"]] = True
        
        btn_launch.grid_remove()
        btn_stop.grid(row=0, column=0, sticky="w")
        
        # На время загрузки блокируем кнопку
        btn_stop.config(state=tk.DISABLED, bg="#333333", fg="#777777")
        
        loading_chars = ["▖", "▘", "▝", "▗"]
        
        def animate(step=0):
            nonlocal animation_id
            if app_state and app_state.running_games.get(current_game["id"], False):
                if step < 25:  # Ровно 5 секунд (25 шагов по 200мс)
                    char = loading_chars[step % len(loading_chars)]
                    lbl_status.config(text=f"⏳ Запуск {char}", fg="#007acc")
                    animation_id = parent.after(200, lambda: animate(step + 1))
                else:
                    # 5 секунд прошло — меняем статус на "Запущено" и открываем кнопку
                    lbl_status.config(text="● Игра запущена", fg="#FFA000")
                    btn_stop.config(state=tk.NORMAL, bg="#555555", fg="white")
        animate()

    def stop_game_action():
        nonlocal animation_id
        if animation_id:
            parent.after_cancel(animation_id)
            
        if app_state and current_game:
            app_state.running_games[current_game["id"]] = False
            
        btn_stop.grid_remove()
        btn_launch.grid(row=0, column=0, sticky="w")
        lbl_status.config(text="● Готова к запуску", fg="#4CAF50")

    # Привязываем функции к кнопкам после их объявления
    btn_launch.config(command=start_game_action)
    btn_stop.config(command=stop_game_action)

    # --- ЦЕЛЬНАЯ ФУНКЦИЯ ВЫБОРА ИГРЫ ---
    def select_game(game, btn, event=None):
        nonlocal current_game, selected_btn
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
        is_running = app_state and app_state.running_games.get(game["id"], False)
        if is_running:
            btn_launch.grid_remove()
            btn_stop.grid(row=0, column=0, sticky="w")
            btn_stop.config(state=tk.NORMAL, bg="#555555", fg="white")
            lbl_status.config(text="● Игра запущена", fg="#FFA000")
            lbl_status.grid(row=0, column=1, padx=20, sticky="w")
        else:
            btn_stop.grid_remove()
            btn_launch.grid(row=0, column=0, sticky="w")
            lbl_status.config(text="● Готова к запуску", fg="#4CAF50")
            lbl_status.grid(row=0, column=1, padx=20, sticky="w")

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
    right_pane.bind("<Button-1>", reset_selection)

    # --- ФУНКЦИЯ ПОИСКА И ОТРИСОВКИ СЕТКИ ---
    def update_catalog_view(*args):
        nonlocal selected_btn
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
            
        for i, game in enumerate(filtered_games):
            row = i // 2
            col = i % 2
            
            btn_frame = tk.Frame(grid_container, width=170, height=110, bg=theme["bg"])
            btn_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            btn_frame.pack_propagate(False)
            
            btn = tk.Button(btn_frame, text=f"{game['icon']}\n\n{game['title']}", 
                            bg=theme["entry_bg"], fg=theme["text"], font=("Arial", 11, "bold"),
                            activebackground=theme["accent"], activeforeground="white",
                            relief=tk.SOLID, bd=1, highlightthickness=0)
            btn.pack(fill=tk.BOTH, expand=True)
            
            btn.config(command=lambda g=game, b=btn: select_game(g, b))
            
            def on_enter(e, b=btn):
                if b != selected_btn:
                    b.config(bg=theme["sidebar_bg"])
            def on_leave(e, b=btn):
                if b != selected_btn:
                    b.config(bg=theme["entry_bg"])
                    
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            
            grid_buttons.append(btn)
            
        show_empty_right_pane()

    search_var.trace_add("write", update_catalog_view)

    update_catalog_view()
    show_empty_right_pane()

    return main_frame