import tkinter as tk
import random
from tools.theme import get_theme

def create_randomizer(parent):
    theme = get_theme()
    frame = tk.Frame(parent, bg=theme["bg"])

    tk.Label(frame, text="Генератор случайных чисел", font=("Arial", 14),
             bg=theme["bg"], fg=theme["text"]).pack(pady=10)

    result_label = tk.Label(frame, text="?", font=("Arial", 40, "bold"),
                             bg=theme["bg"], fg=theme["accent"])
    result_label.pack(pady=20)

    def generate():
        result_label.config(text=str(random.randint(1, 100)))

    tk.Button(frame, text="Сгенерировать", command=generate,
              bg=theme["accent"], fg="white", relief=tk.FLAT, padx=10, pady=5).pack()

    return frame
