LIGHT = {
    "name": "light",
    "bg": "white",
    "sidebar_bg": "#2c3e50",
    "topbar_bg": "#ecf0f1",
    "text": "#1c1c1c",
    "muted_text": "#65676B",
    "accent": "#075E54",
    "accent_light": "#25D366",
    "chat_bg": "#E5DDD5",
    "chat_sidebar_bg": "#ffffff",
    "bubble_me": "#DCF8C6",
    "bubble_other": "#FFFFFF",
    "entry_bg": "white",
    "danger": "#e74c3c",
}

DARK = {
    "name": "dark",
    "bg": "#1e1e1e",
    "sidebar_bg": "#111318",
    "topbar_bg": "#26272b",
    "text": "#e8e8e8",
    "muted_text": "#a0a0a0",
    "accent": "#128C7E",
    "accent_light": "#25D366",
    "chat_bg": "#0b141a",
    "chat_sidebar_bg": "#1f2c34",
    "bubble_me": "#005c4b",
    "bubble_other": "#202c33",
    "entry_bg": "#2a3942",
    "danger": "#c0392b",
}

# Текущая тема хранится тут же, чтобы все модули могли к ней обращаться
_current = LIGHT


def get_theme():
    return _current


def is_dark():
    return _current["name"] == "dark"


def toggle_theme():
    global _current
    _current = DARK if _current["name"] == "light" else LIGHT
    return _current
