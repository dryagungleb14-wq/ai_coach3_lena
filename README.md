# AI Coach - Тулза для прослушки звонков

Онлайн-тулза для анализа звонков менеджеров по продажам.

## Архитектура

- **Фронтенд**: Next.js (TypeScript) на Vercel
- **Бэкенд**: Python FastAPI на Railway
- **База данных**: Supabase PostgreSQL
- **Расшифровка**: Google Gemini API
- **Оценка**: Google Gemini API

## Установка

### Бэкенд

```bash
cd backend
pip install -r requirements.txt
```

Создайте файл `backend/.env`:
```
DATABASE_URL=sqlite:///./ai_coach.db
GEMINI_API_KEY=your_gemini_api_key_here
```

Для локальной разработки используется SQLite. Для продакшена настройте PostgreSQL.

Запуск:
```bash
uvicorn main:app --reload
```

### Фронтенд

```bash
cd frontend
npm install
```

Создайте файл `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Важно для продакшена (Railway):**
- Используйте HTTPS URL без указания порта: `https://your-app.up.railway.app`
- Railway автоматически проксирует HTTPS на порт 8000, поэтому порт в URL не нужен

Запуск:
```bash
npm run dev
```

## Использование

1. Загрузите аудио файлы через интерфейс
2. Укажите метаданные (менеджер, дата, ID звонка)
3. Запустите анализ - система расшифрует аудио и оценит по чек-листу
4. Просмотрите результаты и экспортируйте в CSV

## API Endpoints

- `GET /health` - проверка здоровья API
- `GET /api/health` - проверка здоровья API (альтернативный)
- `POST /api/upload` - загрузка файлов
- `POST /api/analyze/{call_id}` - анализ звонка
- `POST /api/analyze/{call_id}/retest` - повторная проверка
- `GET /api/calls` - список звонков
- `GET /api/calls/{call_id}` - детали звонка
- `GET /api/export` - экспорт в CSV
- `WS /ws/analyze/{call_id}` - WebSocket для получения прогресса анализа

## Troubleshooting

### Проблема: "Не удалось подключиться к серверу"

**Причины и решения:**

1. **Неправильный URL бэкенда**
   - Проверьте переменную окружения `NEXT_PUBLIC_API_URL`
   - Для локальной разработки: `http://localhost:8000`
   - Для Railway: `https://your-app.up.railway.app` (без порта!)
   - Убедитесь, что используется HTTPS для продакшена

2. **Бэкенд не запущен**
   - Проверьте, что бэкенд запущен и доступен
   - Для локальной разработки: `uvicorn main:app --reload`
   - Для Railway: проверьте логи в панели Railway

3. **CORS ошибки**
   - Бэкенд настроен на разрешение всех источников (`allow_origins=["*"]`)
   - Если проблема сохраняется, проверьте логи бэкенда на наличие CORS ошибок

4. **Проверка подключения**
   - На главной странице отображается статус подключения к бэкенду
   - Используйте кнопку "Проверить снова" для ручной проверки
   - Проверьте консоль браузера для детальных логов ошибок

5. **WebSocket подключение**
   - WebSocket автоматически использует правильный протокол (ws:// для HTTP, wss:// для HTTPS)
   - Проверьте, что Railway поддерживает WebSocket соединения
   - В консоли браузера будут логи попыток подключения WebSocket

### Проверка конфигурации

1. **Локальная разработка:**
   ```bash
   # Бэкенд должен быть доступен на http://localhost:8000
   curl http://localhost:8000/health
   
   # Фронтенд должен использовать http://localhost:8000
   # Проверьте .env.local файл
   ```

2. **Продакшен (Railway):**
   ```bash
   # Замените URL на ваш Railway URL
   curl https://your-app.up.railway.app/health
   
   # В Vercel настройте переменную окружения:
   # NEXT_PUBLIC_API_URL=https://your-app.up.railway.app
   ```

### Логирование

#### Формат логов

Приложение использует JSON-формат логов для совместимости с Railway. Все логи выводятся в stdout в формате JSON с полем `severity` вместо `levelname`.

#### Локальное тестирование

Для проверки формата логов локально:

```bash
cd backend
python -c "import logging; import logging.config; import json; f = open('logging_config.json'); config = json.load(f); f.close(); logging.config.dictConfig(config); logging.info('Test log message')"
```

Вывод должен быть JSON с полями:
- `severity`: уровень лога (INFO, ERROR, WARNING и т.д.)
- `timestamp`: время в формате ISO
- `logger`: имя логгера
- `message`: текст сообщения

#### Переменные окружения

- `LOG_LEVEL`: уровень логирования (по умолчанию: INFO). Возможные значения: DEBUG, INFO, WARNING, ERROR, CRITICAL

#### Railway

Railway автоматически парсит JSON-логи и отображает их в интерфейсе. Уровень лога определяется полем `severity`:
- `INFO`, `DEBUG` → обычные сообщения (не красные)
- `ERROR`, `CRITICAL` → ошибки (красные)
- `WARNING` → предупреждения (желтые)

#### Фронтенд логирование

- В режиме разработки (`NODE_ENV=development`) API URL логируется в консоль браузера
- Все ошибки подключения логируются с детальной информацией (URL, тип ошибки)
- Проверьте консоль браузера (F12) для диагностики проблем

