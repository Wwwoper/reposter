FROM python:3.9-slim-buster


ENV API_TOKEN=${API_TOKEN}
ENV WHITE_LIST=${WHITE_LIST}
ENV ACCESS_TOKEN=${ACCESS_TOKEN}
ENV GROUP_TOKEN=${GROUP_TOKEN}
ENV GROUP_ID=${GROUP_ID}
ENV V=${V}


COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000
VOLUME /app/logs

CMD ["python", "/app/app.py"]
