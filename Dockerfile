# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем папки для статики, медиа и логов
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Собираем статику (SECRET_KEY нужен только для запуска Django на этапе сборки,
# в образ он не попадает; реальный ключ передаётся при запуске контейнера)
RUN SECRET_KEY=build-time-placeholder python manage.py collectstatic --noinput

# Открываем порт
EXPOSE 8000

# Запускаем приложение с Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "strikezoneweb.wsgi:application"]