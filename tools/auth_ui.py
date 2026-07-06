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
    auth_win.geometry("350x450")  # Оптимальный стартовый размер
    auth_win.grab_set()
    auth_win.attributes("-topmost", True)

    generated_code = None
    saved_nick, saved_pw = load_credentials()

    # Вспомогательная функция для безопасного вывода ошибок в потоке
    def show_error(title, message):
        print(f"[ОШИБКА Tkinter] {title}: {message}")
        messagebox.showerror(title, message)

    def set_login_mode():
        nonlocal generated_code
        generated_code = None
        
        # Сбрасываем текст и скрываем ненужные фреймы
        label_title.config(text="Вход в аккаунт")
        frame_reg_only.pack_forget()
        code_frame.pack_forget()
        ent_code.delete(0, tk.END)
        
        # Четко возвращаем кнопку действия в состояние Входа
        btn_action.config(text="Войти", command=handle_login, bg="#2ecc71")
        btn_switch.config(text="Нет аккаунта? Регистрация", command=set_reg_mode)

    def set_reg_mode():
        label_title.config(text="Регистрация")
        code_frame.pack_forget()
        ent_code.delete(0, tk.END)
        
        # Показываем поле телефона сразу после поля никнейма
        frame_reg_only.pack(after=ent_nick, pady=5)
        
        # Четко настраиваем кнопку на первый этап регистрации
        btn_action.config(text="Получить код", command=start_verification, bg="#3498db")
        btn_switch.config(text="Уже есть аккаунт? Вход", command=set_login_mode)

    def handle_login():
        nick = ent_nick.get().strip()
        pw = ent_pw.get().strip()
        
        if not nick or not pw:
            show_error("Ошибка", "Заполните никнейм и пароль!")
            return
            
        if login_user(nick, pw):
            save_credentials(nick, pw)
            messagebox.showinfo("Успех", "Вы успешно вошли!")
            auth_win.destroy()
            on_success()
        else:
            show_error("Ошибка", "Неверный ник или пароль!")

    def start_verification():
        nonlocal generated_code
        nick = ent_nick.get().strip()
        phone = ent_phone.get().strip()
        pw = ent_pw.get().strip()

        if not (nick and phone and pw):
            show_error("Ошибка", "Заполните все поля для регистрации!")
            return

        if is_user_exists(nick, phone):
            show_error("Ошибка", "Никнейм или номер телефона уже заняты!")
            return

        # Генерация кода подтверждения
        generated_code = str(random.randint(1000, 9999))
        print(f"\n[СЕРВЕР] ВАШ КОД ДЛЯ РЕГИСТРАЦИИ: {generated_code}")

        # Показываем поле ввода кода
        code_frame.pack(pady=10, before=btn_action)
        
        # Меняем кнопку на финальный шаг регистрации
        btn_action.config(text="Завершить регистрацию", command=finalize_reg, bg="#e67e22")

    def finalize_reg():
        nick = ent_nick.get().strip()
        phone = ent_phone.get().strip()
        pw = ent_pw.get().strip()
        user_code = ent_code.get().strip()

        if user_code == generated_code:
            if register_user(nick, phone, pw):
                save_credentials(nick, pw)
                login_user(nick, pw)  # Автоматический вход
                messagebox.showinfo("Успех", "Аккаунт успешно создан!")
                auth_win.destroy()
                on_success()
            else:
                show_error("Ошибка", "Не удалось сохранить пользователя в БД.")
        else:
            show_error("Ошибка", "Неверный код подтверждения!")

    # --- Сборка элементов интерфейса ---
    label_title = tk.Label(auth_win, text="Вход", font=("Arial", 16, "bold"))
    label_title.pack(pady=10)

    tk.Label(auth_win, text="Никнейм:").pack()
    ent_nick = tk.Entry(auth_win, font=("Arial", 11))
    ent_nick.pack(pady=5)
    ent_nick.insert(0, saved_nick)

    # Контейнер для регистрации (телефон)
    frame_reg_only = tk.Frame(auth_win)
    tk.Label(frame_reg_only, text="Телефон:").pack()
    ent_phone = tk.Entry(frame_reg_only, font=("Arial", 11))
    ent_phone.pack(pady=5)

    tk.Label(auth_win, text="Пароль:").pack()
    ent_pw = tk.Entry(auth_win, show="*", font=("Arial", 11))
    ent_pw.pack(pady=5)
    ent_pw.insert(0, saved_pw)

    # Контейнер для ввода кода подтверждения
    code_frame = tk.Frame(auth_win)
    tk.Label(code_frame, text="Введите код из консоли:", fg="#e74c3c", font=("Arial", 10, "bold")).pack()
    ent_code = tk.Entry(code_frame, width=10, font=("Arial", 14, "bold"), justify='center')
    ent_code.pack(pady=5)

    # Главная кнопка действия
    btn_action = tk.Button(
        auth_win, text="Войти", bg="#2ecc71", fg="white",
        font=("Arial", 11, "bold"), command=handle_login, cursor="hand2", relief="flat"
    )
    btn_action.pack(pady=20, ipadx=30, ipady=5)

    # Кнопка переключения режимов (ссылка)
    btn_switch = tk.Button(
        auth_win, text="Нет аккаунта? Регистрация",
        relief=tk.FLAT, fg="#3498db", font=("Arial", 10, "underline"),
        command=set_reg_mode, cursor="hand2"
    )
    btn_switch.pack(pady=5)

    # Инициализация стартового состояния
    set_login_mode()
    
    return auth_win