FROM python:3.11-slim

WORKDIR /app

# Обновляем пакеты и устанавливаем зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем все необходимые файлы
COPY requirements.txt requirements.txt
COPY bot_with_menu.py bot.py
COPY deep_analysis_v2.py deep_analysis_v2.py
COPY real_apis.py real_apis.py
COPY logger.py logger.py

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем бота
CMD ["python", "bot.py"]
