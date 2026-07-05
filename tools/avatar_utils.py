import os
from PIL import Image, ImageTk, ImageDraw
from tools.auth_db import get_user_avatar


def make_circular_thumbnail(path, size=48):
    img = Image.open(path).convert("RGBA")
    img.thumbnail((size, size))
    square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    square.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    square.putalpha(mask)
    return square


def make_initial_avatar(nickname, color, size=48):
    img = Image.new("RGBA", (size, size), color)
    draw = ImageDraw.Draw(img)
    initial = nickname[0].upper() if nickname else "?"
    # Примерное центрирование буквы
    draw.text((size * 0.35, size * 0.28), initial, fill="white")
    return img


def get_avatar_photo(nickname, accent_color, size=48):
    """Возвращает готовый ImageTk.PhotoImage: либо реальную аватарку, либо кружок с инициалом."""
    avatar_path = get_user_avatar(nickname)
    if avatar_path and os.path.exists(avatar_path):
        img = make_circular_thumbnail(avatar_path, size)
    else:
        img = make_initial_avatar(nickname, accent_color, size)
    return ImageTk.PhotoImage(img)
