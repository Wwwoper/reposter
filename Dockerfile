FROM python:3.9-slim-buster

# Установка переменных окружения для Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Рабочая директория
WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание необходимых директорий
RUN mkdir -p logs temp_photos

# Переменные окружения (будут переопределены из .env)
ENV API_TOKEN=${API_TOKEN}
ENV WHITE_LIST=${WHITE_LIST}
ENV ACCESS_TOKEN=${ACCESS_TOKEN}
ENV GROUP_TOKEN=${GROUP_TOKEN}
ENV GROUP_ID=${GROUP_ID}
ENV V=${V}

# ВАЖНО: Правильная передача сигналов
STOPSIGNAL SIGTERM

# ВАЖНО: Использовать exec форму и unbuffered режим
CMD ["python", "-u", "app.py"]