# Используем базовый образ Python
FROM python:3.9-slim-buster


ENV API_TOKEN=${API_TOKEN}
ENV WHITE_LIST=${WHITE_LIST}
ENV ACCESS_TOKEN=${ACCESS_TOKEN}
ENV GROUP_TOKEN=${GROUP_TOKEN}
ENV GROUP_ID=${GROUP_ID}
ENV V=${V}


# Установка необходимых Python-пакетов
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем файлы приложения в контейнер
COPY . /app

# Порт, который будет использоваться внутри контейнера для приложения
EXPOSE 8000
VOLUME /app/logs


# Запуск приложения
CMD ["python", "/app/app.py"]
