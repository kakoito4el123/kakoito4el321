import os
import sys
import urllib.request
import json
import tempfile
import subprocess
import threading
from pathlib import Path

_update_progress = {
    "status": "idle",
    "downloaded": 0,
    "total": 0,
    "percent": 0,
    "message": "",
}

# ТЕКУЩАЯ ВЕРСИЯ ВАШЕГО ПРИЛОЖЕНИЯ
def get_current_version():
    version_file = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "1.0.2"

# Ссылка на GitHub API вашего репозитория
GITHUB_REPO = "kakoito4el123/kakoito4el321"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def check_for_updates():
    """
    Проверяет наличие свежего релиза на GitHub.
    Возвращает dict с инфой об обновлении или None, если обновлений нет.
    """
    try:
        # Делаем запрос к GitHub API
        req = urllib.request.Request(
            API_URL, 
            headers={'User-Agent': 'Python-App-Updater'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                return None
            
            data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data.get('tag_name', '').lstrip('v')
            release_notes = data.get('body', 'Описание изменений отсутствует.')
            
            # Ищем ZIP-архив в прикрепленных файлах (Assets)
            download_url = None
            file_size_mb = 0
            for asset in data.get('assets', []):
                if asset['name'].startswith('launcher-') and asset['name'].endswith('.zip'):
                    download_url = asset['browser_download_url']
                    file_size_mb = round(asset['size'] / (1024 * 1024), 2)
                    break

            current_version = get_current_version()
            if latest_version and _version_key(latest_version) > _version_key(current_version) and download_url:
                return {
                    "has_update": True,
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "release_notes": release_notes,
                    "download_url": download_url,
                    "file_size_mb": file_size_mb
                }
    except Exception as e:
        print(f"[Updater Error] Не удалось проверить обновления: {e}")
    
    return {"has_update": False}


def _version_key(version):
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return (0,)


def install_latest_update(update_info):
    """Скачивает ZIP релиза и запускает безопасную замену файлов после выхода приложения."""
    if not update_info or not update_info.get("download_url"):
        return {"status": "error", "message": "Доступный релиз не найден"}

    install_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path.cwd()
    archive_path = Path(tempfile.gettempdir()) / f"launcher-{update_info['latest_version']}.zip"
    script_path = Path(tempfile.gettempdir()) / f"launcher-update-{os.getpid()}.ps1"
    _update_progress.update(status="downloading", downloaded=0, total=0, percent=0, message="Подготовка загрузки")
    request = urllib.request.Request(update_info["download_url"], headers={"User-Agent": "Python-App-Updater"})
    with urllib.request.urlopen(request, timeout=30) as response, open(archive_path, "wb") as archive:
        total = int(response.headers.get("Content-Length") or update_info.get("file_size_mb", 0) * 1024 * 1024)
        downloaded = 0
        _update_progress["total"] = total
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            archive.write(chunk)
            downloaded += len(chunk)
            _update_progress.update(
                downloaded=downloaded,
                percent=round(downloaded * 100 / total) if total else 0,
                message=f"Загружено {downloaded / 1024 / 1024:.1f} МБ"
            )

    script = f"""
$ErrorActionPreference = 'Stop'
$processId = {os.getpid()}
while (Get-Process -Id $processId -ErrorAction SilentlyContinue) {{ Start-Sleep -Milliseconds 300 }}
$target = '{str(install_dir).replace("'", "''")}'
$archive = '{str(archive_path).replace("'", "''")}'
$temp = Join-Path $env:TEMP 'launcher-update-{os.getpid()}'
if (Test-Path $temp) {{ Remove-Item $temp -Recurse -Force }}
Expand-Archive -Path $archive -DestinationPath $temp -Force
$payload = Join-Path $temp 'main'
if (Test-Path (Join-Path $temp 'main.exe')) {{ $payload = $temp }}
Copy-Item (Join-Path $payload '*') $target -Recurse -Force
Get-ChildItem -Path $target -Recurse -File | Unblock-File -ErrorAction SilentlyContinue
Start-Process (Join-Path $target 'main.exe')
Remove-Item $archive -Force
Remove-Item $temp -Recurse -Force
Remove-Item $MyInvocation.MyCommand.Path -Force
"""
    script_path.write_text(script, encoding="utf-8")
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    _update_progress.update(status="ready", percent=100, message="Загрузка завершена. Перезапуск...")
    return {"status": "success", "message": "Обновление загружено. Лаунчер перезапустится автоматически."}


def get_update_progress():
    return dict(_update_progress)