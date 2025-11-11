#!/bin/bash

echo "🚀 Запуск AI Coach локально"
echo ""

echo "1. Проверка зависимостей..."
cd backend
if ! python -c "import fastapi" 2>/dev/null; then
    echo "   Установка зависимостей бэкенда..."
    pip install -r requirements.txt
fi
cd ..

cd frontend
if [ ! -d "node_modules" ]; then
    echo "   Установка зависимостей фронтенда..."
    npm install
fi
cd ..

echo ""
echo "2. Проверка конфигурации..."
if [ ! -f "backend/.env" ]; then
    echo "   ⚠️  Создайте backend/.env с DATABASE_URL и GEMINI_API_KEY"
    exit 1
fi

echo ""
echo "3. Запуск серверов..."
echo "   Бэкенд: http://localhost:8000"
echo "   Фронтенд: http://localhost:3000"
echo ""

cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Серверы запущены!"
echo "   Нажмите Ctrl+C для остановки"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait

