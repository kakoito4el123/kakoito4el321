import tkinter as tk
from tkinter import messagebox
import random
import os
from tools.auth_db import is_user_exists, register_user, login_user

# Файл для хранения данных (чисто для удобства тестов)
SAVES_FILE = "login_cache.txt"

def save_credentials(nick, password):
    with open(SAVES_FILE, "w") as f:
        f.write(f"{nick}\n{password}")

def load_credentials():
    if os.path.exists(SAVES_FILE):
        with open(SAVES_FILE, "r") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                return lines[0].strip(), lines[1].strip()
    return "", ""

def show_auth_window(root, on_success):
    auth_win = tk.Toplevel(root)
    auth_win.title("Добро пожаловать")
    auth_win.geometry("350x550")
    auth_win.grab_set()
    auth_win.attributes("-topmost", True)

    generated_code = None
    saved_nick, saved_pw = load_credentials()

    def set_login_mode():
        label_title.config(text="Вход в аккаунт")
        frame_reg_only.pack_forget()
        code_frame.pack_forget()
        btn_action.config(text="Войти", command=handle_login, bg="#2ecc71")
        btn_switch.config(text="Нет аккаунта? Регистрация", command=set_reg_mode)

    def set_reg_mode():
        label_title.config(text="Регистрация")
        frame_reg_only.pack(after=ent_nick, pady=5)
        btn_action.config(text="Получить код", command=start_verification, bg="#3498db")
        btn_switch.config(text="Уже есть аккаунт? Вход", command=set_login_mode)

    def handle_login():
        nick = ent_nick.get()
        pw = ent_pw.get()
        if login_user(nick, pw):
            save_credentials(nick, pw)
            messagebox.showinfo("Успех", "Вы успешно вошли!")
            auth_win.destroy()
            on_success()
        else:
            messagebox.showerror("Ошибка", "Неверный ник или пароль!")

    def start_verification():
        nonlocal generated_code
        nick = ent_nick.get()
        phone = ent_phone.get()
        pw = ent_pw.get()

        if not (nick and phone and pw):
            messagebox.showerror("Ошибка", "Заполните все поля!")
            return

        if is_user_exists(nick, phone):
            messagebox.showerror("Ошибка", "Ник или номер заняты!")
            return

        generated_code = str(random.randint(1000, 9999))
        print(f"\n[СЕРВЕР] ВАШ КОД ДЛЯ РЕГИСТРАЦИИ: {generated_code}")

        code_frame.pack(pady=10)
        btn_action.config(text="Завершить регистрацию", command=finalize_reg, bg="#e67e22")

    def finalize_reg():
        nick = ent_nick.get()
        pw = ent_pw.get()
        if ent_code.get() == generated_code:
            if register_user(nick, ent_phone.get(), pw):
                save_credentials(nick, pw)
                login_user(nick, pw)  # автоматический вход сразу после регистрации
                messagebox.showinfo("Успех", "Аккаунт создан!")
                auth_win.destroy()
                on_success()
        else:
            messagebox.showerror("Ошибка", "Неверный код!")

    label_title = tk.Label(auth_win, text="Вход", font=("Arial", 16, "bold"))
    label_title.pack(pady=10)

    tk.Label(auth_win, text="Никнейм:").pack()
    ent_nick = tk.Entry(auth_win, font=("Arial", 11)); ent_nick.pack(pady=5)
    ent_nick.insert(0, saved_nick)

    frame_reg_only = tk.Frame(auth_win)
    tk.Label(frame_reg_only, text="Телефон:").pack()
    ent_phone = tk.Entry(frame_reg_only, font=("Arial", 11)); ent_phone.pack(pady=5)

    tk.Label(auth_win, text="Пароль:").pack()
    ent_pw = tk.Entry(auth_win, show="*", font=("Arial", 11)); ent_pw.pack(pady=5)
    ent_pw.insert(0, saved_pw)

    code_frame = tk.Frame(auth_win)
    tk.Label(code_frame, text="Введите код из консоли:", fg="red").pack()
    ent_code = tk.Entry(code_frame, width=10, font=("Arial", 12, "bold"), justify='center')
    ent_code.pack(pady=5)

    btn_action = tk.Button(auth_win, text="Войти", bg="#2ecc71", fg="white",
                           font=("Arial", 11, "bold"), command=handle_login, cursor="hand2")
    btn_action.pack(pady=20, ipadx=30, ipady=5)

    btn_switch = tk.Button(auth_win, text="Нет аккаунта? Регистрация",
                           relief=tk.FLAT, fg="#3498db", font=("Arial", 10, "underline"),
                           command=set_reg_mode, cursor="hand2")
    btn_switch.pack()

    def on_closing():
        root.destroy()
    auth_win.protocol("WM_DELETE_WINDOW", on_closing)

    set_login_mode()