# Content Bot Dockerfile
FROM python:3.12-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements_deploy.txt .
RUN pip install --no-cache-dir -r requirements_deploy.txt

# Копирование кода приложения
COPY . .

# Создание директории для состояния
RUN mkdir -p /app/data

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Открытие порта (если понадобится для webhook)
EXPOSE 8080

# Запуск бота
CMD ["python", "bot.py"]
