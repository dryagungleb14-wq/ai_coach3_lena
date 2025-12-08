# План исправления ошибки requires_review

## Проблема
Ошибка `column "requires_review" of relation "calls" does not exist` возникает при загрузке файла. Колонка `requires_review` отсутствует в таблице `calls` в PostgreSQL.

## Задачи

- [x] ✅ Исправить синтаксис DEFAULT в функции migrate_db() для PostgreSQL
- [x] ✅ Создать SQL файл migration_add_requires_review.sql для ручного выполнения миграции

## Версионный лог

### 2025-11-XX (текущая дата)
**Промпт:** Как исправить эту ошибку? Что это?

**Что сделано:**
1. ✅ Исправлена функция `migrate_db()` в `backend/models.py`:
   - Добавлена проверка типа БД перед добавлением колонки `requires_review`
   - Для PostgreSQL используется `DEFAULT FALSE` вместо `DEFAULT 0`
   - Для SQLite сохранен синтаксис `DEFAULT 0`
2. ✅ Создан SQL файл `backend/migration_add_requires_review.sql` для ручного выполнения миграции

**Измененные файлы:**
- `backend/models.py` — исправлена функция `migrate_db()`
- `backend/migration_add_requires_review.sql` — создан новый файл миграции

**Коммит:**
- Коммит `1187f37`: "Исправление ошибки миграции requires_review: добавлена поддержка PostgreSQL DEFAULT FALSE"
- Изменения отправлены в `origin/main`

