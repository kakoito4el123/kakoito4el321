Миграция SQLite → Supabase

1) Подготовка
- Создайте проект в Supabase и Bucket в Storage (например `media`).
- Скопируйте URL проекта и `service_role` ключ (или аннотацию `SERVICE_ROLE`).
- Установите зависимости: `pip install -r requirements.txt`.

2) Экспорт/импорт
- Экспорт производится скриптом `scripts/migrate_to_supabase.py`.
- Перед запуском экспортируйте текущую БД (по умолчанию `users_data.db` в текущей папке).
- Установите переменные окружения:
```
SET SUPABASE_URL=https://your-project.supabase.co
SET SUPABASE_KEY=your_service_role_key
SET SUPABASE_BUCKET=media
```
- Запустите:
```
python scripts/migrate_to_supabase.py --db path/to/users_data.db --bucket media
```
- Для теста используйте флаг `--dry-run`.

3) После миграции
- Таблицы следует проверить в Supabase Studio: `users`, `friends`, `friend_requests`, `messages`, `games`.
- Проверьте, что файлы загружены в Storage и имеют публичные URL (или настройте RLS/CDN).

4) Переключение приложения
- После успешной миграции нужно адаптировать `tools/*` и `main.py` для работы с Supabase (вызовы к Postgres/Storage).
- Безопасность: храните `SUPABASE_KEY` только на серверной стороне.

Если хотите, могу:
- подготовить автоматическое переключение backend на Supabase (patch к `tools/*`),
- или выполнить миграцию на вашем Supabase (нужны SUPABASE_URL и SERVICE_ROLE ключ).
