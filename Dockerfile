FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости (libmagic1 нужен для python-magic)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt (контекст сборки = backend/)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge && \
    rm -rf /root/.cache/pip

# Копируем все файлы из текущего контекста (backend/) в /app
COPY . .

EXPOSE 8000

CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-config logging_config.json"
