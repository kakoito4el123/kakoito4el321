import tkinter as tk
from tkinter import messagebox
import sqlite3
from tools.theme import get_theme

def create_todo(parent):
    theme = get_theme()
    frame = tk.Frame(parent, bg=theme["bg"])

    # --- ЛОГИКА БД ---
    def init_db():
        conn = sqlite3.connect("todo.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, task TEXT)")
        conn.commit()
        conn.close()

    def load_tasks():
        listbox.delete(0, tk.END)
        conn = sqlite3.connect("todo.db")
        cursor = conn.cursor()
        cursor.execute("SELECT task FROM tasks")
        for row in cursor.fetchall():
            listbox.insert(tk.END, row[0])
        conn.close()

    def add():
        task = task_entry.get()
        if task:
            conn = sqlite3.connect("todo.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (task) VALUES (?)", (task,))
            conn.commit()
            conn.close()
            task_entry.delete(0, tk.END)
            load_tasks()

    def delete():
        try:
            # Получаем текст выбранного элемента
            selected_index = listbox.curselection()[0]
            selected_text = listbox.get(selected_index)

            conn = sqlite3.connect("todo.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE task = ?", (selected_text,))
            conn.commit()
            conn.close()
            load_tasks()
        except IndexError:
            messagebox.showwarning("Внимание", "Выберите заметку для удаления")

    # --- ИНТЕРФЕЙС ---
    tk.Label(frame, text="Список дел (с сохранением)", font=("Arial", 14), bg=theme["bg"], fg=theme["text"]).pack(pady=10)

    entry_frame = tk.Frame(frame, bg=theme["bg"])
    entry_frame.pack(pady=5)

    task_entry = tk.Entry(entry_frame, width=30, font=("Arial", 12), bg=theme["entry_bg"], fg=theme["text"])
    task_entry.pack(side=tk.LEFT, padx=5)

    tk.Button(entry_frame, text="Добавить", command=add, bg=theme["accent"], fg="white", relief=tk.FLAT).pack(side=tk.LEFT)

    listbox = tk.Listbox(frame, width=45, height=10, font=("Arial", 10), bg=theme["entry_bg"], fg=theme["text"])
    listbox.pack(pady=10, padx=20)

    tk.Button(frame, text="Удалить выбранное", command=delete, fg="white", bg=theme["danger"], relief=tk.FLAT).pack()

    init_db()
    load_tasks()

    return frame
