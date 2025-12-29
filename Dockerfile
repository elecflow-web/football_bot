FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов (БЕЗ суффикса _fixed!)
COPY requirements.txt requirements.txt
COPY bot.py bot.py
COPY real_apis.py real_apis.py
COPY logger.py logger.py
COPY model.py model.py
COPY historical_matches.csv historical_matches.csv
COPY runtime.txt runtime.txt

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Запуск бота
CMD ["python", "bot.py"]
