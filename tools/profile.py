import tkinter as tk
from tkinter import messagebox, filedialog
import os
import shutil
from tools.auth_db import get_current_user, logout_user, set_user_avatar, get_user_avatar
from tools.theme import get_theme
from tools.paths import AVATARS_DIR
from tools.avatar_utils import get_avatar_photo


def create_profile(parent):
    theme = get_theme()
    frame = tk.Frame(parent, bg=theme["bg"])
    user = get_current_user()
    nick = user[0] if user else None

    tk.Label(frame, text="👤 Мой Профиль", font=("Arial", 18, "bold"), bg=theme["bg"], fg=theme["text"]).pack(pady=20)

    avatar_label = tk.Label(frame, bg=theme["bg"])
    avatar_label.pack(pady=10)

    def load_avatar_preview():
        if not nick:
            return
        img_tk = get_avatar_photo(nick, theme["accent"], size=120)
        avatar_label.image = img_tk  # держим ссылку, иначе tkinter соберёт мусор
        avatar_label.config(image=img_tk)

    def change_avatar():
        if not nick:
            return
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")])
        if not path:
            return
        ext = os.path.splitext(path)[1]
        dest = os.path.join(AVATARS_DIR, f"{nick}{ext}")
        shutil.copy(path, dest)
        set_user_avatar(nick, dest)
        load_avatar_preview()
        messagebox.showinfo("Готово", "Аватарка обновлена!")

    tk.Button(frame, text="Сменить аватарку", command=change_avatar,
              bg=theme["accent"], fg="white", relief=tk.FLAT, padx=10, pady=5).pack(pady=5)

    if user:
        nickname, phone = user
        info_text = f"Ваш ник: {nickname}\n\nВаш номер: {phone}\n\nСтатус: Online"
    else:
        info_text = "Пользователь не найден"

    tk.Label(frame, text=info_text, font=("Arial", 12), bg=theme["entry_bg"], fg=theme["text"],
             padx=20, pady=20, relief=tk.GROOVE).pack(pady=10)

    # ФУНКЦИЯ ДЛЯ КНОПКИ ВЫХОДА
    def handle_logout():
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти из аккаунта?"):
            logout_user()
            parent.winfo_toplevel().destroy()

    tk.Button(frame, text="Выйти из аккаунта", command=handle_logout,
              bg=theme["danger"], fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, padx=10, pady=5).pack(pady=30)

    load_avatar_preview()
    return frame
