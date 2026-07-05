import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
import io
import time  # <--- Добавили импорт времени
from tools.chat_db import *
# Импортируем добавленные нами функции управления активностью
from tools.auth_db import get_current_user, update_user_activity, get_user_last_seen
from tools.theme import get_theme
from tools.avatar_utils import get_avatar_photo

def calculate_online_status(last_seen_timestamp):
    """Вычисляет цвет индикатора и текстовое описание времени активности"""
    if last_seen_timestamp is None:
        return "gray", "был(а) давно"
        
    now = time.time()
    diff_seconds = int(now - last_seen_timestamp)
    
    # Меньше 60 секунд — пишем "в сети" и ставим зеленый маркер
    if diff_seconds < 5:
        return "#25D366", "в сети"  # Приятный зеленый цвет WhatsApp
        
    diff_minutes = diff_seconds // 60
    if diff_minutes < 2:
        return "gray", "был(а) только что"
    elif diff_minutes < 5:
        return "gray", "был(а) 2 мин. назад"
    elif diff_minutes < 15:
        return "gray", f"был(а) {diff_minutes} мин. назад"
    elif diff_minutes < 60:
        return "gray", "был(а) менее часа назад"
        
    diff_hours = diff_minutes // 60
    if diff_hours < 24:
        if diff_hours == 1:
            return "gray", "был(а) более часа назад"
        return "gray", f"был(а) {diff_hours} ч. назад"
        
    return "gray", "был(а) давно"

def create_chat(parent, on_logout=None):
    theme = get_theme()
    user_info = get_current_user()
    if not user_info: return tk.Label(parent, text="Ошибка авторизации")
    my_nick = user_info[0]

    current_chat_with = None
    last_msg_count = 0
    reply_data = None
    avatar_refs = []  # чтобы PhotoImage не удалялись сборщиком мусора
    
    # Хранилище ссылок на виджеты статусов друзей, чтобы обновлять их динамически
    # Структура: { 'friend_nick': { 'dot': canvas_widget, 'status_label': label_widget, 'row': frame_widget } }
    status_widgets = {}

    main_frame = tk.Frame(parent, bg=theme["chat_bg"])

    # --- САЙДБАР ---
    sidebar = tk.Frame(main_frame, width=220, bg=theme["chat_sidebar_bg"], bd=0)
    sidebar.pack(side=tk.LEFT, fill=tk.Y)
    sidebar.pack_propagate(False)

    tk.Label(sidebar, text=" Чаты", font=("Segoe UI", 14, "bold"), bg=theme["chat_sidebar_bg"], fg=theme["accent"]).pack(pady=15, anchor="w")

    bottom_bar = tk.Frame(sidebar, bg=theme["chat_sidebar_bg"])
    bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

    btn_reqs = tk.Button(bottom_bar, text="Заявки", relief=tk.FLAT)

    tk.Button(bottom_bar, text="+ Добавить друга", bg="#25D366", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
              command=lambda: [send_friend_request(my_nick, simpledialog.askstring("Поиск", "Номер:")), refresh_friends()]).pack(fill=tk.X, padx=10, pady=10)

    list_canvas = tk.Canvas(sidebar, bg=theme["chat_sidebar_bg"], highlightthickness=0)
    list_scroll = tk.Scrollbar(sidebar, orient="vertical", command=list_canvas.yview)
    friends_list_frame = tk.Frame(list_canvas, bg=theme["chat_sidebar_bg"])
    friends_list_frame.bind("<Configure>", lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
    list_canvas.create_window((0, 0), window=friends_list_frame, anchor="nw", width=200)
    list_canvas.configure(yscrollcommand=list_scroll.set)
    list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def show_requests():
        reqs = get_incoming_requests(my_nick)
        win = tk.Toplevel(main_frame)
        win.title("Заявки")
        win.geometry("300x400")
        for f in reqs:
            frm = tk.Frame(win, pady=5); frm.pack(fill=tk.X, padx=10)
            tk.Label(frm, text=f).pack(side=tk.LEFT)
            tk.Button(frm, text="Принять", bg="#25D366", fg="white",
                      command=lambda x=f: [accept_friend_request(my_nick, x), win.destroy(), refresh_friends()]).pack(side=tk.RIGHT)

    def select_friend(nick):
        nonlocal current_chat_with, last_msg_count
        current_chat_with = nick
        friend_label.config(text=f"💬 {nick}")
        mark_as_read(my_nick, nick)
        last_msg_count = 0
        update_chat_window()
        refresh_friends()

    def refresh_friends():
        for w in friends_list_frame.winfo_children():
            w.destroy()
        avatar_refs.clear()
        status_widgets.clear() # Очищаем старые ссылки при перерисовке списка

        for f in get_friends_list(my_nick):
            unread = get_unread_count(my_nick, f)
            is_selected = (f == current_chat_with)
            row_bg = theme["accent"] if is_selected else theme["chat_sidebar_bg"]
            row_fg = "white" if is_selected else theme["text"]

            row = tk.Frame(friends_list_frame, bg=row_bg, cursor="hand2")
            row.pack(fill=tk.X, pady=1)

            avatar_img = get_avatar_photo(f, theme["accent"], size=36)
            avatar_refs.append(avatar_img)
            lbl_avatar = tk.Label(row, image=avatar_img, bg=row_bg)
            lbl_avatar.pack(side=tk.LEFT, padx=8, pady=6)

            # Контейнер для имени и статуса "был в сети"
            info_block = tk.Frame(row, bg=row_bg)
            info_block.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Верхняя строка контейнера: Имя и цветной кружок
            name_row = tk.Frame(info_block, bg=row_bg)
            name_row.pack(side=tk.TOP, fill=tk.X, anchor="w", pady=(2, 0))

            name_text = f if unread == 0 else f"{f}  ({unread if unread <= 99 else '99+'})"
            lbl_name = tk.Label(name_row, text=name_text, bg=row_bg, fg=row_fg, font=("Segoe UI", 10, "bold" if unread > 0 else "normal"))
            lbl_name.pack(side=tk.LEFT, anchor="w")

            # Маленький индикатор-кружок (Canvas)
            dot_canvas = tk.Canvas(name_row, width=10, height=10, bg=row_bg, highlightthickness=0)
            dot_canvas.pack(side=tk.LEFT, padx=5, pady=4)
            
            # Рассчитываем начальный статус
            dot_color, text_status = calculate_online_status(get_user_last_seen(f))
            dot_id = dot_canvas.create_oval(2, 2, 9, 9, fill=dot_color, outline="")

            # Нижняя строка контейнера: Время активности (был тогда-то)
            # Если контакт выбран (активен), ставим приглушенный белый текст, иначе стандартный серый
            status_fg = "#E0E0E0" if is_selected else theme["muted_text"]
            lbl_status = tk.Label(info_block, text=text_status, bg=row_bg, fg=status_fg, font=("Segoe UI", 8))
            lbl_status.pack(side=tk.TOP, anchor="w")

            # Сохраняем ссылки для динамического обновления
            status_widgets[f] = {
                "canvas": dot_canvas,
                "dot_id": dot_id,
                "status_label": lbl_status,
                "row_bg": row_bg
            }

            for widget in (row, lbl_avatar, info_block, name_row, lbl_name, dot_canvas, lbl_status):
                widget.bind("<Button-1>", lambda e, n=f: select_friend(n))

        reqs = get_incoming_requests(my_nick)
        if reqs:
            btn_reqs.config(text=f"Заявки ({len(reqs)})", bg="#25D366", fg="white", command=show_requests)
            btn_reqs.pack(fill=tk.X, padx=10, pady=(10, 0))
        else: btn_reqs.pack_forget()

    # --- ЧАТ-ЗОНА ---
    chat_container = tk.Frame(main_frame, bg=theme["chat_bg"])
    chat_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    header = tk.Frame(chat_container, bg=theme["accent"], height=55)
    header.pack(side=tk.TOP, fill=tk.X)
    friend_label = tk.Label(header, text="Выберите контакт", font=("Segoe UI", 11, "bold"), bg=theme["accent"], fg="white")
    friend_label.pack(side=tk.LEFT, padx=15, pady=12)

    input_container = tk.Frame(chat_container, bg=theme["chat_sidebar_bg"], pady=5)
    input_container.pack(side=tk.BOTTOM, fill=tk.X)

    reply_bar = tk.Frame(chat_container, bg="#E1F3FB", bd=1, relief=tk.GROOVE)
    reply_label = tk.Label(reply_bar, text="", font=("Segoe UI", 9, "italic"), bg="#E1F3FB", fg="#075E54", anchor="w")
    reply_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)

    def close_reply():
        nonlocal reply_data; reply_data = None; reply_bar.pack_forget()
    tk.Button(reply_bar, text="✕", bd=0, bg="#E1F3FB", command=close_reply).pack(side=tk.RIGHT, padx=5)

    def set_reply(text, sender):
        nonlocal reply_data
        reply_data = f"{sender}: {text[:30]}"
        reply_label.config(text=f"➥ {reply_data}")
        reply_bar.pack(side=tk.BOTTOM, fill=tk.X, before=input_container)

    def show_msg_menu(event, msg_id, is_me, text):
        menu = tk.Menu(main_frame, tearoff=0)
        if is_me:
            menu.add_command(label="Редактировать", command=lambda: edit_msg_prompt(msg_id, text))
            menu.add_command(label="Удалить", command=lambda: [delete_message(msg_id), update_chat_window()])
        menu.add_command(label="Ответить", command=lambda: set_reply(text, "Собеседник"))
        menu.post(event.x_root, event.y_root)

    def edit_msg_prompt(msg_id, old_text):
        new_text = simpledialog.askstring("Редактирование", "Новый текст:", initialvalue=old_text)
        if new_text:
            edit_message(msg_id, new_text)
            update_chat_window()

    sticker_frame = tk.Frame(input_container, bg=theme["chat_sidebar_bg"])
    sticker_frame.pack(side=tk.TOP, fill=tk.X)

    def open_full_photo(img_bytes):
        top = tk.Toplevel(); img = Image.open(io.BytesIO(img_bytes)); img.thumbnail((800, 800))
        img_tk = ImageTk.PhotoImage(img); l = tk.Label(top, image=img_tk); l.image = img_tk; l.pack()

    def send_photo():
        if not current_chat_with: return
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")])
        if path:
            with open(path, "rb") as f: img_data = f.read()
            save_message(my_nick, current_chat_with, img_data, is_image=1); update_chat_window()

    tk.Button(sticker_frame, text="🖼️", relief=tk.FLAT, bg=theme["chat_sidebar_bg"], command=send_photo).pack(side=tk.LEFT, padx=10)
    for s in ["😊", "😂", "👍", "❤️"]:
        tk.Button(sticker_frame, text=s, relief=tk.FLAT, bg=theme["chat_sidebar_bg"],
                  command=lambda c=s: [save_message(my_nick, current_chat_with, c), update_chat_window()] if current_chat_with else None).pack(side=tk.LEFT, padx=2)

    entry_frame = tk.Frame(input_container, bg=theme["chat_sidebar_bg"])
    entry_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
    entry = tk.Entry(entry_frame, font=("Segoe UI", 12), bg=theme["entry_bg"], fg=theme["text"], relief=tk.FLAT, bd=8)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def send_msg(e=None):
        nonlocal reply_data
        text = entry.get().strip()
        if text and current_chat_with:
            final = f"➥ {reply_data}\n{text}" if reply_data else text
            save_message(my_nick, current_chat_with, final); entry.delete(0, tk.END); close_reply(); update_chat_window()

    entry.bind("<Return>", send_msg)
    tk.Button(entry_frame, text="🕊️", font=("Arial", 16), fg=theme["accent"], bg=theme["chat_sidebar_bg"], bd=0, command=send_msg).pack(side=tk.RIGHT, padx=10)

    txt_output = tk.Text(chat_container, bg=theme["chat_bg"], state=tk.DISABLED, font=("Segoe UI", 10), relief=tk.FLAT, padx=15)
    txt_output.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def update_chat_window():
        nonlocal last_msg_count
        if not current_chat_with: return
        history = get_chat_history(my_nick, current_chat_with)
        if len(history) != last_msg_count:
            txt_output.config(state=tk.NORMAL); txt_output.delete('1.0', tk.END); txt_output._img_refs = []
            for sender, content, time, is_image, msg_id in history:
                is_me = (sender == my_nick); bubble_bg = theme["bubble_me"] if is_me else theme["bubble_other"]
                txt_output.insert(tk.END, f"{time}\n", "my_header" if is_me else "friend_header")
                if is_image:
                    try:
                        img_raw = Image.open(io.BytesIO(content)); img_raw.thumbnail((220, 220))
                        img_tk = ImageTk.PhotoImage(img_raw); txt_output._img_refs.append(img_tk)
                        lbl_img = tk.Label(txt_output, image=img_tk, bg=theme["chat_bg"], cursor="hand2")
                        lbl_img.bind("<Button-1>", lambda e, b=content: open_full_photo(b))
                        lbl_img.bind("<Button-3>", lambda e, mid=msg_id, m=is_me: show_msg_menu(e, mid, m, "[Фото]"))
                        lbl_img.bind("<MouseWheel>", lambda e: txt_output.yview_scroll(int(-1*(e.delta/120)), "units"))
                        txt_output.window_create(tk.END, window=lbl_img)
                    except: txt_output.insert(tk.END, " [Ошибка фото] ")
                else:
                    msg = content.decode('utf-8') if isinstance(content, bytes) else content
                    bubble = tk.Label(txt_output, text=msg, bg=bubble_bg, fg="black" if theme["name"] == "light" else "white",
                                       font=("Segoe UI", 10), padx=10, pady=5, wraplength=250, justify=tk.LEFT)
                    bubble.bind("<Button-3>", lambda e, mid=msg_id, m=is_me, t=msg: show_msg_menu(e, mid, m, t))
                    bubble.bind("<MouseWheel>", lambda e: txt_output.yview_scroll(int(-1*(e.delta/120)), "units"))
                    txt_output.window_create(tk.END, window=bubble)

                line_start = txt_output.index("insert linestart")
                txt_output.tag_add("right" if is_me else "left", line_start, "insert")
                txt_output.insert(tk.END, "\n\n")

            txt_output.tag_configure("right", justify='right')
            txt_output.tag_configure("left", justify='left')
            txt_output.tag_configure("my_header", justify='right', foreground=theme["muted_text"], font=("Segoe UI", 7))
            txt_output.tag_configure("friend_header", justify='left', foreground=theme["muted_text"], font=("Segoe UI", 7))
            txt_output.config(state=tk.DISABLED); txt_output.see(tk.END); last_msg_count = len(history)

    def sync_loop():
        # 1. Говорим базе, что МЫ активны прямо сейчас
        update_user_activity(my_nick)
        
        # 2. Обновляем историю сообщений
        update_chat_window()
        
        # 3. Динамически перерисовываем статусы друзей без пересоздания виджетов списка
        for friend_name, widgets in status_widgets.items():
            ts = get_user_last_seen(friend_name)
            dot_color, text_status = calculate_online_status(ts)
            
            # Меняем цвет точки на Canvas
            widgets["canvas"].itemconfig(widgets["dot_id"], fill=dot_color)
            # Меняем текст
            widgets["status_label"].config(text=text_status)
            
        # Проверяем заявки в друзья (раз в 2 секунды)
        reqs = get_incoming_requests(my_nick)
        if reqs:
            btn_reqs.config(text=f"Заявки ({len(reqs)})", bg="#25D366", fg="white", command=show_requests)
            btn_reqs.pack(fill=tk.X, padx=10, pady=(10, 0))
        else: btn_reqs.pack_forget()

        main_frame.after(2000, sync_loop)
        
    # Запускаем первичное наполнение списка и стартуем фоновый цикл
    refresh_friends()
    sync_loop()
    return main_frame