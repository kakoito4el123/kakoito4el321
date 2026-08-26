import webview
import os
import subprocess

# Этот класс — мост между HTML и Python.
# Любая функция, написанная внутри этого класса, становится автоматически 
# доступна для вызова из JavaScript внутри index.html!
class LauncherAPI:
    def test_python_signal(self):
        print("\n[PYTHON] Вау! Сигнал от CSS-кнопки успешно долетел до Python!")
        print("[PYTHON] Сейчас запустим системное приложение для теста...")
        
        # Для теста запустим встроенный калькулятор Windows, чтобы доказать,
        # что кнопка из "сайта" может управлять компьютером.
        try:
            if os.name == 'nt': # Если это Windows
                subprocess.Popen(["calc.exe"])
            else:
                print("[PYTHON] Тест прошел успешно! (Запуск calc.exe пропущен, так как вы не на Windows)")
        except Exception as e:
            print(f"[PYTHON] Ошибка запуска приложения: {e}")

if __name__ == '__main__':
    # 1. Создаем экземпляр нашей логики
    api = LauncherAPI()

    # 2. Создаем красивое окно приложения без рамок Tkinter
    window = webview.create_window(
        title="Epic Godot Launcher", 
        url='index.html',        # Указываем наш файл с версткой и CSS
        width=950, 
        height=650,
        resizable=True,
        background_color='#0f0f12' # Цвет фона окна до загрузки HTML
    )

    # 3. Стартуем лаунчер и передаем ему наш класс с функциями (js_api=api)
    webview.start()