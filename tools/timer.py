import tkinter as tk
from tkinter import messagebox
from tools.theme import get_theme

def create_timer(parent):
    theme = get_theme()
    frame = tk.Frame(parent, bg=theme["bg"])

    # Переменная для хранения ID текущего таймера, чтобы его можно было остановить
    timer_id = None
    is_running = False

    tk.Label(frame, text="Надежный Таймер", font=("Arial", 14), bg=theme["bg"], fg=theme["text"]).pack(pady=10)

    entry_var = tk.StringVar(value="10")
    entry = tk.Entry(frame, textvariable=entry_var, font=("Arial", 20), width=5, justify='center',
                      bg=theme["entry_bg"], fg=theme["text"])
    entry.pack(pady=10)

    label_time = tk.Label(frame, text="00", font=("Arial", 30), bg=theme["bg"], fg=theme["muted_text"])
    label_time.pack(pady=10)

    def start_countdown():
        nonlocal timer_id, is_running
        if is_running: return # Защита от повторного нажатия

        try:
            seconds = int(entry_var.get())
            is_running = True

            # Блокируем кнопку Старт и поле ввода
            btn_start.config(state=tk.DISABLED, bg="#95a5a6")
            entry.config(state=tk.DISABLED)
            label_time.config(fg="red")

            def tick():
                nonlocal seconds, timer_id, is_running
                if seconds >= 0:
                    label_time.config(text=str(seconds))
                    seconds -= 1
                    timer_id = frame.after(1000, tick)
                else:
                    stop_timer()
                    messagebox.showinfo("Время!", "Таймер завершен!")

            tick()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите число")

    def stop_timer():
        nonlocal timer_id, is_running
        is_running = False
        if timer_id:
            frame.after_cancel(timer_id) # Останавливаем выполнение после .after()
            timer_id = None

        # Разблокируем интерфейс
        btn_start.config(state=tk.NORMAL, bg="#e67e22")
        entry.config(state=tk.NORMAL)
        label_time.config(text="00", fg=theme["muted_text"])

    # Кнопки
    btn_frame = tk.Frame(frame, bg=theme["bg"])
    btn_frame.pack(pady=10)

    btn_start = tk.Button(btn_frame, text="СТАРТ", command=start_countdown, bg="#e67e22", fg="white", width=10, relief=tk.FLAT)
    btn_start.pack(side=tk.LEFT, padx=5)

    btn_stop = tk.Button(btn_frame, text="СТОП", command=stop_timer, bg="#c0392b", fg="white", width=10, relief=tk.FLAT)
    btn_stop.pack(side=tk.LEFT, padx=5)

    return frame
