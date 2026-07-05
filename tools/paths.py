import os

# Единая папка с данными приложения — в домашней папке пользователя.
# Работает на Windows/Mac/Linux, не привязана к конкретному ПК.
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".modular_chat_app")
AVATARS_DIR = os.path.join(APP_DATA_DIR, "avatars")

DB_NAME = os.path.join(APP_DATA_DIR, "users_data.db")

os.makedirs(APP_DATA_DIR, exist_ok=True)
os.makedirs(AVATARS_DIR, exist_ok=True)
