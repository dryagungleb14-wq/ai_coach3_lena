# Инструкция по деплою

## Деплой бэкенда на Railway

1. Зайдите на https://railway.app и войдите через GitHub
2. Нажмите "New Project" → "Deploy from GitHub repo"
3. Выберите ваш репозиторий
4. **Важно**: Укажите Root Directory как `backend`
5. Railway автоматически определит Python проект и использует Nixpacks для сборки

### Настройка переменных окружения в Railway:

В настройках проекта (Settings → Variables) добавьте:
- `DATABASE_URL` - URL базы данных PostgreSQL (Railway может создать автоматически)
- `GEMINI_API_KEY` - ваш API ключ от Google Gemini
- `PORT` - Railway установит автоматически, не нужно добавлять вручную

### Настройка базы данных:

1. В Railway добавьте PostgreSQL сервис (Add Service → Database → PostgreSQL)
2. Скопируйте `DATABASE_URL` из настроек PostgreSQL
3. Добавьте его в переменные окружения бэкенда

### Проверка деплоя:

После деплоя Railway покажет URL вашего API (например: `https://your-app.up.railway.app`)

Проверьте: `https://your-app.up.railway.app/` должно вернуть `{"message":"AI Coach API"}`

## Деплой фронтенда на Vercel

1. Зайдите на https://vercel.com и войдите через GitHub
2. Нажмите "Add New Project"
3. Выберите ваш репозиторий
4. Настройте проект:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js (определится автоматически)
   - **Build Command**: `npm run build` (по умолчанию)
   - **Output Directory**: `.next` (по умолчанию)

### Настройка переменных окружения в Vercel:

В настройках проекта (Settings → Environment Variables) добавьте:
- `NEXT_PUBLIC_API_URL` - URL вашего бэкенда на Railway (например: `https://your-app.up.railway.app`)

**Важно**: После добавления переменной перезапустите деплой (Redeploy)

### Проверка деплоя:

После деплоя Vercel покажет URL вашего фронтенда (например: `https://your-app.vercel.app`)

Откройте URL и проверьте, что фронтенд работает и подключается к бэкенду.

## Важные моменты:

1. **CORS**: Бэкенд настроен на разрешение всех источников (`allow_origins=["*"]`), что подходит для деплоя
2. **База данных**: Используйте PostgreSQL на Railway, не SQLite
3. **Файлы**: Загруженные аудио файлы будут храниться в `backend/uploads/` на Railway (временное хранилище)
4. **Порты**: Railway автоматически устанавливает PORT, бэкенд использует его

## Troubleshooting:

- Если фронтенд не подключается к бэкенду, проверьте `NEXT_PUBLIC_API_URL` в Vercel и перезапустите деплой
- Если бэкенд не запускается, проверьте логи в Railway (View Logs)
- Если приложение крашится при старте, проверьте логи в Railway и убедитесь что все переменные окружения установлены
- Если возникают ошибки с базой данных, проверьте что `DATABASE_URL` правильно настроен

## Быстрая проверка после деплоя:

1. Проверьте бэкенд: `curl https://your-railway-app.up.railway.app/`
2. Проверьте API: `curl https://your-railway-app.up.railway.app/api/calls`
3. Откройте фронтенд в браузере и попробуйте загрузить файл

